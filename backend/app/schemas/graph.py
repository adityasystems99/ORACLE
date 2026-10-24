"""Pydantic schemas for the Temporal Knowledge Graph, Graph RAG, and blast radius models."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class NodeType(str, Enum):
    """Types of entities tracked within the temporal knowledge graph."""
    COMPANY = "Company"
    PRODUCT = "Product"
    TECHNOLOGY = "Technology"
    API = "API"
    SOFTWARE_VERSION = "SoftwareVersion"
    RELEASE = "Release"
    SECURITY_ADVISORY = "SecurityAdvisory"
    EVENT = "Event"
    PROJECT = "Project"
    DEPENDENCY = "Dependency"
    EVIDENCE_DOCUMENT = "EvidenceDocument"

    # Compatibility aliases for legacy seed nodes and tests
    PACKAGE = "package"
    SERVICE = "service"
    ORGANIZATION = "organization"
    SPECIFICATION = "specification"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_clean = value.lower().replace("_", "").replace("-", "")
            for member in cls:
                if member.value.lower().replace("_", "").replace("-", "") == val_clean or member.name.lower().replace("_", "").replace("-", "") == val_clean:
                    return member
        return None


class EdgeType(str, Enum):
    """Directional semantic relationships between entities."""
    PRODUCES = "PRODUCES"
    USES = "USES"
    DEPENDS_ON = "DEPENDS_ON"
    AFFECTS = "AFFECTS"
    SUPERSEDES = "SUPERSEDES"
    ANNOUNCES = "ANNOUNCES"
    DOCUMENTED_BY = "DOCUMENTED_BY"
    VERSION_OF = "VERSION_OF"

    # Compatibility aliases for legacy edge types
    INTEGRATES_WITH = "INTEGRATES_WITH"
    DEPRECATED_BY = "DEPRECATED_BY"
    AFFECTED_BY = "AFFECTED_BY"
    MAINTAINED_BY = "MAINTAINED_BY"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_clean = value.upper().replace("-", "_")
            for member in cls:
                if member.value.upper().replace("-", "_") == val_clean or member.name == val_clean:
                    return member
        return None


class RelationshipModality(str, Enum):
    """Distinguishes verified empirical facts from inferred or what-if hypotheses."""
    OBSERVED = "observed"          # Explicitly stated in verified source evidence / manifest
    INFERRED = "inferred"          # Derived through deterministic graph traversal / dependency propagation
    HYPOTHETICAL = "hypothetical"  # Predictive what-if simulation or speculative impact


class TemporalGraphNode(BaseModel):
    """Entity node in the temporal graph with lifecycle timestamps and evidence citations."""
    id: str = Field(..., description="Canonical entity key (lowercase e.g. 'fastapi')")
    name: str = Field(..., description="Display name of the technology/package")
    node_type: NodeType = Field(..., description="Category of entity")
    ecosystem: str = Field(default="python", description="Ecosystem (e.g. python, node, cloud)")
    version: Optional[str] = Field(default=None, description="Current or specific version string")
    latest_version: Optional[str] = None
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list, description="IDs of supporting evidence documents")
    properties: Dict[str, Any] = Field(default_factory=dict)


class TemporalGraphEdge(BaseModel):
    """Temporal edge linking two nodes with valid time window, evidence provenance, and modality."""
    id: Optional[str] = Field(default=None, description="Unique edge identifier")
    source: str = Field(..., description="Origin node id")
    target: str = Field(..., description="Destination node id")
    edge_type: EdgeType = Field(..., description="Semantic relation")
    modality: RelationshipModality = Field(default=RelationshipModality.OBSERVED, description="Observed vs Inferred vs Hypothetical")
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: Optional[datetime] = Field(default=None, description="End of validity interval. None indicates currently active.")
    valid_to: Optional[datetime] = Field(default=None, description="Alias for valid_until for compatibility.")
    version_constraint: Optional[str] = Field(default=None, description="e.g. '>=2.0.0, <3.0.0'")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_ids: List[str] = Field(default_factory=list, description="Evidence document or passage IDs proving this relationship")
    source_evidence_id: Optional[str] = Field(default=None, description="Primary supporting evidence document ID")
    source_url: Optional[str] = Field(default=None, description="Direct URL of the primary source")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Publisher, retrieval details, and ingest metadata")
    properties: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def sync_temporal_and_evidence_fields(self) -> "TemporalGraphEdge":
        # Keep valid_until and valid_to in sync
        if self.valid_to is not None and self.valid_until is None:
            self.valid_until = self.valid_to
        elif self.valid_until is not None and self.valid_to is None:
            self.valid_to = self.valid_until

        # Sync primary evidence ID
        if self.source_evidence_id and self.source_evidence_id not in self.evidence_ids:
            self.evidence_ids.append(self.source_evidence_id)
        elif self.evidence_ids and not self.source_evidence_id:
            self.source_evidence_id = self.evidence_ids[0]

        # Auto-generate ID if missing
        if not self.id:
            ts = int(self.valid_from.timestamp()) if self.valid_from else 0
            self.id = f"{self.source}->{self.edge_type.value}->{self.target}_{ts}"

        return self


class PathStep(BaseModel):
    """A single traversed relationship hop in an explainable graph path."""
    from_node: str
    from_name: str
    from_type: NodeType
    to_node: str
    to_name: str
    to_type: NodeType
    edge_id: Optional[str] = None
    relationship: EdgeType
    modality: RelationshipModality
    valid_from: datetime
    valid_until: Optional[datetime] = None
    version_constraint: Optional[str] = None
    confidence: float = 1.0
    evidence_ids: List[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    step_explanation: str


class ExplainablePath(BaseModel):
    """An explainable, evidence-backed provenance path between two entities in the graph."""
    path_id: str
    source_id: str
    target_id: str
    steps: List[PathStep]
    overall_explanation: str
    evidence_citations: List[str] = Field(default_factory=list)
    total_hops: int
    is_temporally_valid: bool = True
    path_modality: RelationshipModality = RelationshipModality.OBSERVED


class TraversalResult(BaseModel):
    """Result of a bounded temporal graph traversal."""
    root_entity: str
    as_of: datetime
    max_depth: int
    max_nodes: int
    total_nodes_visited: int
    total_edges_traversed: int
    cycles_detected: int = 0
    nodes: List[TemporalGraphNode]
    edges: List[TemporalGraphEdge]
    explainable_paths: List[ExplainablePath] = Field(default_factory=list)


class BlastRadiusNode(BaseModel):
    """A single technology/package within an impact blast radius."""
    node_id: str
    name: str
    node_type: NodeType
    ecosystem: str
    depth: int = Field(..., description="Hops away from the root change entity")
    relationship_path: List[str] = Field(default_factory=list, description="Sequence of relationship types from root")
    impact_likelihood: float = Field(..., ge=0.0, le=1.0)
    modality: RelationshipModality = Field(default=RelationshipModality.INFERRED)
    vulnerability_reasons: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class BlastRadiusReport(BaseModel):
    """Graph blast radius propagation result."""
    root_entity: str = Field(..., description="Originating node id triggering the analysis")
    event_id: Optional[str] = None
    max_traversal_depth: int
    total_nodes_scanned: int
    direct_dependents_count: int
    transitive_dependents_count: int
    affected_nodes: List[BlastRadiusNode] = Field(default_factory=list)
    analysis_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphSnapshot(BaseModel):
    """Full exportable snapshot of the knowledge graph for visualization & backup."""
    nodes: List[TemporalGraphNode]
    edges: List[TemporalGraphEdge]
    node_count: int
    edge_count: int
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TemporalGraphRAGQuery(BaseModel):
    """Query payload for combined Temporal Graph RAG investigation."""
    query: str = Field(..., description="Natural language question, incident topic, or package name")
    event_id: Optional[str] = Field(default=None, description="Optional associated IntelligenceEvent ID")
    root_entity: Optional[str] = Field(default=None, description="Optional entity ID to seed graph traversal")
    as_of: Optional[datetime] = Field(default=None, description="Temporal snapshot point. Outdated relationships after this are filtered.")
    max_depth: int = Field(default=3, ge=1, le=6, description="Maximum graph hops to traverse")
    max_nodes: int = Field(default=50, ge=5, le=200, description="Maximum graph nodes to include in neighborhood")
    top_k_evidence: int = Field(default=5, ge=1, le=20, description="Number of semantic evidence passages to retrieve")
    active_only: bool = Field(default=True, description="When true, filters out relationships superseded before as_of")
    rerank: bool = Field(default=True, description="Apply hybrid lexical/semantic reranking to retrieved evidence")


class TemporalGraphRAGResponse(BaseModel):
    """Comprehensive Temporal Graph RAG investigation response."""
    query: str
    as_of: datetime
    anchored_entities: List[str]
    evidence_passages: List[Any] = Field(default_factory=list, description="Passages from Live RAG vector search")
    explainable_paths: List[ExplainablePath] = Field(default_factory=list, description="Verifiable paths linking event/entities to affected targets")
    affected_nodes: List[BlastRadiusNode] = Field(default_factory=list, description="Discovered affected entities in the blast radius")
    graph_subgraph: GraphSnapshot = Field(..., description="Neighborhood subgraph encompassing evidence and dependents")
    synthesis: str = Field(..., description="Structured synthesis explaining impact and temporal status")
    verified_evidence_count: int
    observed_relations_count: int
    inferred_relations_count: int
    hypothetical_relations_count: int
    unverified_dependencies_invented: bool = Field(default=False, description="Strict safety indicator: guarantees zero invented dependencies")
