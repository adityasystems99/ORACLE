"""Impact Analysis Engine synthesizing graph blast radius, vector evidence, and LLM reasoning."""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from ..config import get_settings
from ..graph.store import KnowledgeGraphStore
from ..llm.base import BaseLLMAdapter
from ..llm.factory import get_llm_adapter
from ..retrieval.vector_store import VectorStore
from ..schemas.event import IntelligenceEvent, SeverityLevel
from ..schemas.graph import BlastRadiusNode
from ..schemas.report import ImpactReport, MitigationAction
from ..storage.disk_store import DiskStore

logger = logging.getLogger(__name__)


class LLMSynthesisSchema(BaseModel):
    """Structured response schema expected from LLM."""
    executive_summary: str = Field(..., description="High-level summary of the ecosystem impact")
    technical_root_cause: str = Field(..., description="Detailed explanation of the breaking change, vulnerability, or failure")
    breaking_changes: List[str] = Field(default_factory=list, description="List of concrete breaking API/spec changes")
    mitigation_playbook: List[MitigationAction] = Field(default_factory=list, description="Prioritized mitigation actions")
    confidence_score: float = Field(default=0.90, ge=0.0, le=1.0)


class ImpactAnalyzer:
    """Combines graph blast radius, vector evidence retrieval, and LLM synthesis."""

    def __init__(
        self,
        graph_store: KnowledgeGraphStore,
        vector_store: VectorStore,
        disk_store: DiskStore,
        llm_adapter: Optional[BaseLLMAdapter] = None,
    ):
        self.settings = get_settings()
        self.graph_store = graph_store
        self.vector_store = vector_store
        self.disk_store = disk_store
        self.llm_adapter = llm_adapter or get_llm_adapter()

    async def generate_impact_report(
        self,
        event: IntelligenceEvent,
        max_graph_depth: int = 3,
    ) -> ImpactReport:
        """Conduct comprehensive impact assessment for an intelligence event."""
        logger.info(f"Analyzing impact for event: {event.id} ({event.title})")

        # 1. Compute blast radius from temporal knowledge graph
        blast_report = self.graph_store.calculate_blast_radius(
            root_entity_id=event.primary_technology,
            max_depth=max_graph_depth,
            event_id=event.id,
        )

        # 2. Vector retrieval: Query vector store for related past events or context
        retrieved_context = self.vector_store.query_similar(
            collection_name="events",
            query_text=f"{event.primary_technology} {event.title} {event.summary}",
            n_results=3,
        )
        context_snippets = [r.get("document", "") for r in retrieved_context if r.get("id") != event.id]

        # 3. Construct evidence-grounded prompt for LLM
        prompt = self._build_synthesis_prompt(event, blast_report.affected_nodes, context_snippets)
        system_prompt = (
            "You are ORACLE, a Principal Software Architect and Technology Intelligence Copilot.\n"
            "Analyze the provided technological change event and graph blast radius.\n"
            "Ground your conclusions strictly on the provided evidence and dependency paths.\n"
            "Do NOT speculate or invent breaking changes not justified by the event text.\n"
            "Provide concrete, actionable code or terminal commands for every mitigation step."
        )

        # 4. Invoke provider-agnostic LLM
        synthesis_result, provenance = await self.llm_adapter.generate_structured(
            prompt=prompt,
            response_model=LLMSynthesisSchema,
            system_prompt=system_prompt,
            temperature=self.settings.LLM_TEMPERATURE,
        )

        # 5. Assemble final evidence-backed ImpactReport
        report_id = f"rpt_{event.id.replace('evt_', '')}_{event.primary_technology}"
        report = ImpactReport(
            id=report_id,
            event_id=event.id,
            event_title=event.title,
            severity=event.severity,
            primary_technology=event.primary_technology,
            ecosystem=event.metadata.get("ecosystem", "generic"),
            executive_summary=synthesis_result.executive_summary,
            technical_root_cause=synthesis_result.technical_root_cause,
            breaking_changes=synthesis_result.breaking_changes,
            impacted_components=blast_report.affected_nodes,
            evidence_trail=event.evidence,
            mitigation_playbook=synthesis_result.mitigation_playbook,
            confidence_score=min(event.confidence, synthesis_result.confidence_score),
            llm_provenance=provenance,
            is_live_data=event.is_live_data,
        )

        # 6. Persist report and index in vector store for future retrieval
        self.disk_store.upsert_item("reports", report)
        self.vector_store.upsert_documents(
            collection_name="reports",
            ids=[report.id],
            documents=[f"{report.event_title}\n{report.executive_summary}\n{report.technical_root_cause}"],
            metadatas=[{
                "event_id": report.event_id,
                "technology": report.primary_technology,
                "severity": report.severity.value,
            }],
        )

        logger.info(f"Successfully generated and persisted impact report: {report.id}")
        return report

    def _build_synthesis_prompt(
        self,
        event: IntelligenceEvent,
        affected_nodes: List[BlastRadiusNode],
        context_snippets: List[str],
    ) -> str:
        nodes_desc = "\n".join(
            [f"- {n.name} (Type: {n.node_type.value}, Depth: {n.depth}, Path: {' -> '.join(n.relationship_path)})" for n in affected_nodes]
        ) or "No direct dependents found in knowledge graph."

        evidence_desc = "\n".join(
            [f"- Source ({e.source_url}): \"{e.snippet}\"" for e in event.evidence]
        )

        context_desc = "\n".join([f"- Related Signal: {s[:160]}..." for s in context_snippets]) if context_snippets else "None."

        return (
            f"### INTELLIGENCE EVENT DETAILS\n"
            f"Title: {event.title}\n"
            f"Category: {event.category.value}\n"
            f"Calculated Severity: {event.severity.value}\n"
            f"Primary Technology: {event.primary_technology}\n"
            f"CVE ID: {event.cve_id or 'N/A'}\n"
            f"Event Summary: {event.summary}\n\n"
            f"### GROUND-TRUTH EVIDENCE CITATIONS\n{evidence_desc}\n\n"
            f"### GRAPH BLAST RADIUS (AFFECTED DEPENDENTS)\n{nodes_desc}\n\n"
            f"### HISTORICAL CONTEXT\n{context_desc}\n\n"
            f"Provide an evidence-backed impact analysis with an executive summary, technical root cause, "
            f"breaking changes list, and a prioritized mitigation playbook."
        )
