"""Pydantic schemas for the Temporal Knowledge Graph and blast radius models."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of entities tracked within the knowledge graph."""
    TECHNOLOGY = "technology"          # Language, runtime, framework (e.g. Python, Node.js)
    PACKAGE = "package"                # Library / module (e.g. pydantic, httpx, react)
    SERVICE = "service"                # Cloud service / platform (e.g. AWS S3, Cloudflare)
    ORGANIZATION = "organization"      # Maintainer / company (e.g. PSF, Meta, Vercel)
    SPECIFICATION = "specification"    # Standard / RFC (e.g. OpenAPI 3.1, OAuth 2.1)


class EdgeType(str, Enum):
    """Directional semantic relationships between entities."""
    DEPENDS_ON = "depends_on"          # A depends on B
    INTEGRATES_WITH = "integrates_with"# A works alongside B
    DEPRECATED_BY = "deprecated_by"    # A is replaced/deprecated by B
    AFFECTED_BY = "affected_by"        # A is impacted by B (vulnerability or incident)
    MAINTAINED_BY = "maintained_by"    # A is maintained by organization B


class TemporalGraphNode(BaseModel):
    """Entity node in the temporal graph with lifecycle timestamps."""
    id: str = Field(..., description="Canonical entity key (lowercase e.g. 'fastapi')")
    name: str = Field(..., description="Display name of the technology/package")
    node_type: NodeType = Field(..., description="Category of entity")
    ecosystem: str = Field(default="python", description="Ecosystem (e.g. python, node, cloud)")
    latest_version: Optional[str] = None
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class TemporalGraphEdge(BaseModel):
    """Temporal edge linking two nodes with valid time window and constraints."""
    source: str = Field(..., description="Origin node id")
    target: str = Field(..., description="Destination node id")
    edge_type: EdgeType = Field(..., description="Semantic relation")
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_to: Optional[datetime] = None  # None indicates currently active
    version_constraint: Optional[str] = Field(default=None, description="e.g. '>=2.0.0, <3.0.0'")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_evidence_id: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class BlastRadiusNode(BaseModel):
    """A single technology/package within an impact blast radius."""
    node_id: str
    name: str
    node_type: NodeType
    ecosystem: str
    depth: int = Field(..., description="Hops away from the root change entity")
    relationship_path: List[str] = Field(default_factory=list, description="Sequence of relationship types from root")
    impact_likelihood: float = Field(..., ge=0.0, le=1.0)
    vulnerability_reasons: List[str] = Field(default_factory=list)


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
