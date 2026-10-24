"""Evidence-grounded impact analysis and unified investigation pipeline for ORACLE."""

from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .ranking import FindingRankingEngine
from ..graph.store import KnowledgeGraphStore
from ..graph.temporal import parse_timestamp
from ..retrieval.rag_pipeline import LiveRAGPipeline
from ..schemas.event import SeverityLevel
from ..schemas.graph import EdgeType, NodeType, RelationshipModality
from ..schemas.investigation import (
    EvidenceItem,
    FindingPriority,
    ImpactCategory,
    ImpactStatus,
    InvestigationFinding,
    InvestigationReport,
    InvestigationRequest,
)
from ..schemas.rag import EvidencePassage, EvidenceSearchQuery

logger = logging.getLogger("oracle.impact.investigation")


class InvestigationService:
    """Unified investigation pipeline combining Live RAG evidence, historical version auditing,

    temporal graph reasoning, deterministic ranking, and transparent uncertainty reporting.
    """

    def __init__(
        self,
        graph_store: KnowledgeGraphStore,
        rag_pipeline: LiveRAGPipeline,
        ranking_engine: Optional[FindingRankingEngine] = None,
    ):
        self.graph_store = graph_store
        self.rag_pipeline = rag_pipeline
        self.ranking_engine = ranking_engine or FindingRankingEngine()

    def _extract_entities_from_text(self, text: str) -> List[str]:
        """Extract candidate technology / package / API keys mentioned in text, ordered by appearance position."""
        tokens = set(re.findall(r"[A-Za-z0-9_\-\.]+", text.lower()))
        matched_with_pos: List[Tuple[int, str]] = []

        for node_id in self.graph_store.graph.nodes:
            key = str(node_id).lower()
            name = str(self.graph_store.graph.nodes[node_id].get("name", "")).lower()
            pos = -1
            if key in tokens:
                pos = text.lower().find(key)
            elif name and name in text.lower():
                pos = text.lower().find(name)

            if pos != -1:
                matched_with_pos.append((pos, key))

        # Sort by first appearance in the input text so grammatical subjects take precedence
        matched_with_pos.sort(key=lambda x: x[0])
        return list(dict.fromkeys([k for _, k in matched_with_pos]))

    def _categorize_impact(self, text: str, edge_type: str) -> ImpactCategory:
        """Deterministically determine impact category based on technical tokens and relationship."""
        t_lower = text.lower()
        if "deprecat" in t_lower or "sunset" in t_lower or "end-of-life" in t_lower or "eol" in t_lower:
            return ImpactCategory.API_DEPRECATION
        if "cve-" in t_lower or "vulnerability" in t_lower or "advisory" in t_lower or edge_type == EdgeType.AFFECTS.value:
            return ImpactCategory.SECURITY_VULNERABILITY
        if "breaking" in t_lower or "backward-incompatible" in t_lower or "removed" in t_lower:
            return ImpactCategory.BREAKING_CHANGE
        if "conflict" in t_lower or "incompatible version" in t_lower:
            return ImpactCategory.DEPENDENCY_CONFLICT
        if "outage" in t_lower or "incident" in t_lower or "degraded" in t_lower:
            return ImpactCategory.SERVICE_OUTAGE
        return ImpactCategory.BREAKING_CHANGE

    async def investigate(self, request: InvestigationRequest) -> InvestigationReport:
        """Execute full evidence-grounded impact investigation workflow."""
        start_time = datetime.now(timezone.utc)
        as_of_dt = parse_timestamp(request.as_of) or start_time
        logger.info(f"Starting unified impact investigation for: '{request.query}' (as_of: {as_of_dt.isoformat()})")

        # 1. Retrieve Current Evidence from Live RAG
        search_res = self.rag_pipeline.search_evidence(
            EvidenceSearchQuery(
                query=request.query,
                top_k=request.max_candidates,
                rerank=True,
            )
        )
        passages: List[EvidencePassage] = search_res.passages

        # Convert passages to EvidenceItems
        evidence_items: List[EvidenceItem] = []
        for p in passages:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=p.chunk_id,
                    source_url=p.source_url,
                    publisher=p.publisher,
                    title=getattr(p, "title", None) or (p.metadata.get("title") if isinstance(p.metadata, dict) else None) or f"Evidence {p.chunk_id}",
                    snippet=p.content[:300],
                    publication_timestamp=p.publication_timestamp,
                    retrieval_timestamp=p.retrieval_timestamp,
                    document_version=p.document_version,
                    is_superseded=False,
                    content_hash=p.content_hash,
                )
            )

        # 2. Retrieve Historical Document Versions & Detect Superseded Claims
        superseded_claims: List[str] = []
        conflicts: List[str] = []
        unknowns: List[str] = []

        if request.include_historical:
            all_stored_docs = self.rag_pipeline.get_all_documents()
            for doc in all_stored_docs:
                if doc.previous_versions:
                    for prev in doc.previous_versions:
                        superseded_claims.append(
                            f"Document '{doc.title}' v{prev.version} was updated to v{doc.document_version} on {prev.archived_at.strftime('%Y-%m-%d')} (Fingerprint {prev.content_hash[:8]}). Prior content: \"{prev.content_preview[:120]}...\""
                        )

        # 3. Identify Related Entities in the Knowledge Graph
        anchored_entities: List[str] = []
        if request.target_technology:
            target_clean = request.target_technology.lower().strip()
            if target_clean in self.graph_store.graph:
                anchored_entities.append(target_clean)

        if not anchored_entities:
            query_entities = self._extract_entities_from_text(request.query)
            for ent in query_entities:
                if ent not in anchored_entities:
                    anchored_entities.append(ent)

        # Only inspect passages for candidate entities if no anchor was established from target_technology or query,
        # and only from passages with high relevance score (>= 0.35) to prevent topic drift into unrelated entities
        if not anchored_entities:
            for p in passages:
                if getattr(p, "score", 0.0) >= 0.35:
                    p_title = getattr(p, "title", "") or ""
                    doc_entities = self._extract_entities_from_text(f"{p_title} {p.content}")
                    for ent in doc_entities:
                        if ent not in anchored_entities and len(anchored_entities) < 3:
                            anchored_entities.append(ent)

        # Strict grounding: If no entity matched the query or evidence, do NOT fall back to arbitrary nodes
        if not anchored_entities:
            unknowns.append(
                "No known or verified technology entities from this query were matched in the knowledge graph. "
                "Unsupported dependency claims are rejected; 0 speculative connections were invented."
            )

        # 4. Traverse Supported Relationships to Discover Affected Components
        findings: List[InvestigationFinding] = []
        rules_applied_set: Set[str] = set()

        # The primary root under investigation is target_technology if provided, or the first query entity
        primary_anchor = anchored_entities[0] if anchored_entities else None
        secondary_anchors = anchored_entities[1:] if len(anchored_entities) > 1 else []

        # Check if query asked about secondary entities that have NO path to primary_anchor
        for sec in secondary_anchors:
            paths = self.graph_store.find_explainable_paths(
                source_id=primary_anchor,
                target_id=sec,
                max_depth=request.max_graph_depth,
                max_paths=1,
                as_of=as_of_dt,
            )
            reverse_paths = self.graph_store.find_explainable_paths(
                source_id=sec,
                target_id=primary_anchor,
                max_depth=request.max_graph_depth,
                max_paths=1,
                as_of=as_of_dt,
            )
            if not paths and not reverse_paths:
                unknowns.append(
                    f"Verified graph topology confirms NO dependency path between '{primary_anchor}' and '{sec}'. "
                    f"Unsupported dependency claim is rejected; no shared blast radius exists."
                )

        # Only traverse the primary root entity for downstream blast radius propagation
        traversal_roots = [primary_anchor] if primary_anchor else []

        for anchor in traversal_roots:
            # Traversal for downstream and upstream connections
            traversal = self.graph_store.traverse(
                root_id=anchor,
                max_depth=request.max_graph_depth,
                max_nodes=request.max_candidates * 2,
                as_of=as_of_dt,
                active_only=True,
            )

            # Check each visited node that is not the anchor itself
            for node in traversal.nodes:
                if node.id == anchor:
                    continue

                # Find explainable path from anchor to this node
                paths = self.graph_store.find_explainable_paths(
                    source_id=anchor,
                    target_id=node.id,
                    max_depth=request.max_graph_depth,
                    max_paths=1,
                    as_of=as_of_dt,
                    active_only=True,
                )
                if not paths:
                    continue

                path = paths[0]
                depth = len(path.steps)
                first_step = path.steps[0]

                # Determine impact category
                impact_cat = self._categorize_impact(request.query + " " + path.overall_explanation, first_step.relationship.value)

                # Determine empirical certainty:
                # Direct OBSERVED relationship from verified manifest/API -> CONFIRMED exposure
                # Multi-hop transitive dependency -> POTENTIAL exposure
                if depth == 1 and first_step.modality == RelationshipModality.OBSERVED:
                    status = ImpactStatus.CONFIRMED
                    severity = SeverityLevel.HIGH if impact_cat in (ImpactCategory.API_DEPRECATION, ImpactCategory.BREAKING_CHANGE) else SeverityLevel.MEDIUM
                else:
                    status = ImpactStatus.POTENTIAL
                    severity = SeverityLevel.MEDIUM if depth == 2 else SeverityLevel.LOW

                # Base summary
                summary = (
                    f"Component '{node.name}' ({node.node_type.value}) is connected to '{anchor}' "
                    f"via {path.overall_explanation}. Category: {impact_cat.value.replace('_', ' ').title()}."
                )

                # Known facts grounded in evidence
                known_facts = [
                    f"Entity '{node.name}' is recorded in the knowledge graph with type '{node.node_type.value}' in ecosystem '{node.ecosystem}'.",
                    f"Relationship '{first_step.relationship.value}' connects '{first_step.from_name}' to '{first_step.to_name}'"
                    + (f" with version constraint '{first_step.version_constraint}'." if first_step.version_constraint else "."),
                    f"Temporal interval verified active as of {as_of_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}.",
                ]

                # Inferences and assumptions
                inferences = [
                    f"Assumed that '{node.name}' actively invokes the affected API/interface at runtime based on recorded graph dependency.",
                    "Transitive impact propagation assumes non-isolated build environment.",
                ]

                # Confidence limitations & unknowns
                limitations = [
                    "A graph dependency connection does not prove execution or causal outage in production.",
                    "Internal AST (Abstract Syntax Tree) call graph has not been indexed; specific deprecated methods used cannot be verified without private repository access.",
                ]

                # Suggested next steps
                next_steps = [
                    f"Inspect codebase for '{node.name}' to check for direct calls to deprecated symbols.",
                    f"Run integration test suite with upgraded dependency constraint to verify compatibility.",
                    "Review official changelog and migration guide linked in evidence sources.",
                ]

                # Evidence sources matching this finding
                finding_evidence = [e for e in evidence_items if anchor in e.snippet.lower() or node.id in e.snippet.lower()]
                if not finding_evidence and evidence_items:
                    finding_evidence = evidence_items[:2]

                # Assemble finding
                finding_id = f"fnd_{anchor}_{node.id}_{impact_cat.value}"
                finding = InvestigationFinding(
                    id=finding_id,
                    summary=summary,
                    affected_entity=node.id,
                    affected_entity_name=node.name,
                    affected_entity_type=node.node_type.value,
                    impact_category=impact_cat,
                    impact_status=status,
                    severity=severity,
                    priority=FindingPriority.P2_MEDIUM,
                    severity_and_priority_explanation="",
                    evidence_and_sources=finding_evidence,
                    supporting_graph_path=[s.step_explanation for s in path.steps],
                    graph_path_explanation=path.overall_explanation,
                    known_facts=known_facts,
                    inferences_and_assumptions=inferences,
                    confidence_limitations=limitations,
                    suggested_next_steps=next_steps,
                    last_verified_timestamp=start_time,
                    internal_verification_note="UNVERIFIABLE_WITHOUT_PRIVATE_CODE: Internal repository usage of deprecated API cannot be verified without codebase AST or dependency lockfile.",
                    score=0.0,
                )

                # Score & rank finding
                score, priority, rules = self.ranking_engine.score_finding(finding, depth=depth)
                finding.score = score
                finding.priority = priority
                finding.severity_and_priority_explanation = f"Score: {score:.1f}/100 -> {priority.value}. Factors: {'; '.join(rules)}."
                for r in rules:
                    rules_applied_set.add(r)

                findings.append(finding)

        # 5. Filter & Rank Findings
        if request.min_severity:
            sev_order = [SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL]
            min_idx = sev_order.index(request.min_severity)
            findings = [f for f in findings if sev_order.index(f.severity) >= min_idx]

        ranked_findings = self.ranking_engine.rank_findings(findings)[: request.max_candidates]

        # 6. Check for Contradictions & Unknowns
        if not evidence_items:
            unknowns.append("No primary evidence documents match query in current vector index; findings are based solely on graph topology.")
        unknowns.append("Internal private repositories were not scanned; internal call graph coverage is 0%.")

        confirmed_count = sum(1 for f in ranked_findings if f.impact_status == ImpactStatus.CONFIRMED)
        potential_count = sum(1 for f in ranked_findings if f.impact_status == ImpactStatus.POTENTIAL)

        # 7. Executive Summary
        exec_summary = (
            f"Evidence-grounded impact investigation identified {len(ranked_findings)} potentially affected components "
            f"across {len(anchored_entities)} anchored entities ('{', '.join(anchored_entities)}'). "
            f"Confirmed: {confirmed_count}, Potential: {potential_count}. "
            f"Reliability Rule Enforced: Graph connections indicate dependency exposure, not proven causation. "
            f"Internal private code impact cannot be verified without repository AST analysis."
        )

        report_id = f"inv_rpt_{int(start_time.timestamp())}_{anchored_entities[0] if anchored_entities else 'tech'}"
        return InvestigationReport(
            id=report_id,
            query_or_event=request.query,
            investigation_timestamp=start_time,
            target_technology=request.target_technology,
            executive_summary=exec_summary,
            total_findings=len(ranked_findings),
            confirmed_impacts_count=confirmed_count,
            potential_impacts_count=potential_count,
            findings=ranked_findings,
            superseded_claims=superseded_claims,
            conflicts_and_contradictions=conflicts,
            unknowns_and_open_questions=unknowns,
            evidence_citations=evidence_items,
            internal_impact_verification_status="UNVERIFIED: Internal private repository code cannot be analyzed without AST access.",
            ranking_rules_applied=sorted(list(rules_applied_set)),
            llm_assisted=False,
            llm_provenance=None,
        )
