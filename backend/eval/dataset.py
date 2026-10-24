"""Reproducible, manually labeled test dataset for ORACLE end-to-end evaluation.

Covers 6 essential evaluation scenarios:
1. New Announcements (breaking changes, CVEs, major releases)
2. Revised Announcements (version increments, modified deprecation timelines)
3. Duplicate Documents (content deduplication and hash checkpoints)
4. Outdated Information (superseded versions and expired validity intervals)
5. Conflicting Sources (divergent claims between primary and secondary feeds)
6. Unsupported Dependency Scenarios (assertions of relationships with no graph or document evidence)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class EvaluationSample:
    id: str
    scenario: str  # "new_announcement" | "revised_announcement" | "duplicate_document" | "outdated_information" | "conflicting_sources" | "unsupported_dependency"
    title: str
    content: str
    source_url: str
    publisher: str
    ecosystem: str
    published_at: str
    version: str
    
    # Ground Truths for Evaluation
    expected_event_category: Optional[str] = None  # breaking_change, security_vulnerability, deprecation, outage, major_release
    expected_severity: Optional[str] = None  # critical, high, medium, low
    expected_primary_tech: Optional[str] = None
    expected_entities: List[str] = field(default_factory=list)
    expected_affected_dependents: List[str] = field(default_factory=list)
    unsupported_dependents: List[str] = field(default_factory=list)  # MUST NOT be reported as affected
    ground_truth_query: str = ""
    expected_relevant_keywords: List[str] = field(default_factory=list)
    is_superseded: bool = False
    superseded_by_sample_id: Optional[str] = None
    expected_conflict: bool = False
    temporal_as_of: Optional[str] = None


EVALUATION_DATASET: List[EvaluationSample] = [
    # =========================================================================
    # SCENARIO 1: NEW ANNOUNCEMENTS (Breaking Changes, CVEs, Outages)
    # =========================================================================
    EvaluationSample(
        id="sample-new-fastapi-lifespan",
        scenario="new_announcement",
        title="FastAPI 0.111.0: Deprecate on_event in favor of Lifespan handlers",
        content=(
            "FastAPI 0.111.0 officially deprecates `@app.on_event('startup')` and `@app.on_event('shutdown')`. "
            "Applications should now use async context manager `lifespan` handlers. "
            "Passing `on_event` will trigger a deprecation warning and be removed in a future release."
        ),
        source_url="https://github.com/tiangolo/fastapi/releases/tag/0.111.0",
        publisher="FastAPI GitHub",
        ecosystem="python",
        published_at="2024-05-15T10:00:00Z",
        version="0.111.0",
        expected_event_category="deprecation",
        expected_severity="medium",
        expected_primary_tech="fastapi",
        expected_entities=["fastapi", "starlette", "pydantic"],
        expected_affected_dependents=["internal_crm_service", "analytics_pipeline"],
        unsupported_dependents=["react", "django", "kubernetes"],
        ground_truth_query="What happened to on_event startup handlers in FastAPI 0.111.0?",
        expected_relevant_keywords=["lifespan", "deprecate", "on_event", "startup"],
    ),
    EvaluationSample(
        id="sample-new-pydantic-v2",
        scenario="new_announcement",
        title="Pydantic V2 Migration Guide: Breaking changes to validator and root_validator",
        content=(
            "Pydantic V2 is a complete rewrite in Rust. Breaking change: `@validator` is replaced by `@field_validator`. "
            "`@root_validator` is replaced by `@model_validator`. `dict()` is replaced by `model_dump()`, "
            "and `json()` is replaced by `model_dump_json()`. Schema generation methods have changed."
        ),
        source_url="https://docs.pydantic.dev/2.0/migration/",
        publisher="Pydantic Official",
        ecosystem="python",
        published_at="2023-06-30T12:00:00Z",
        version="2.0.0",
        expected_event_category="breaking_change",
        expected_severity="high",
        expected_primary_tech="pydantic",
        expected_entities=["pydantic", "fastapi"],
        expected_affected_dependents=["fastapi", "internal_crm_service"],
        unsupported_dependents=["express", "vue", "redis"],
        ground_truth_query="What are the breaking changes in Pydantic V2 regarding validators?",
        expected_relevant_keywords=["field_validator", "model_validator", "model_dump", "validator"],
    ),
    EvaluationSample(
        id="sample-new-cve-fastapi",
        scenario="new_announcement",
        title="CVE-2024-24762: ReDoS Vulnerability in FastAPI Content-Type Header Parsing",
        content=(
            "CVE-2024-24762 affects FastAPI versions prior to 0.109.1. An attacker can send a crafted Content-Type header "
            "causing regular expression catastrophic backtracking (ReDoS) leading to severe denial of service."
        ),
        source_url="https://nvd.nist.gov/vuln/detail/CVE-2024-24762",
        publisher="NIST NVD",
        ecosystem="python",
        published_at="2024-02-05T08:00:00Z",
        version="0.109.0",
        expected_event_category="security_vulnerability",
        expected_severity="high",
        expected_primary_tech="fastapi",
        expected_entities=["fastapi"],
        expected_affected_dependents=["internal_crm_service", "analytics_pipeline"],
        unsupported_dependents=["nextjs", "aws"],
        ground_truth_query="Explain CVE-2024-24762 in FastAPI Content-Type parsing",
        expected_relevant_keywords=["redos", "content-type", "denial of service", "0.109.1"],
    ),
    EvaluationSample(
        id="sample-new-nextjs-15-async",
        scenario="new_announcement",
        title="Next.js 15 RC: Async Request APIs Breaking Change for cookies and headers",
        content=(
            "In Next.js 15, asynchronous request-specific data like `cookies()`, `headers()`, and page `params` "
            "are transitioning from synchronous access to asynchronous Promises. Users must await them or use React `use()`."
        ),
        source_url="https://nextjs.org/blog/next-15",
        publisher="Vercel Next.js",
        ecosystem="node",
        published_at="2024-05-23T14:00:00Z",
        version="15.0.0-rc.0",
        expected_event_category="breaking_change",
        expected_severity="high",
        expected_primary_tech="nextjs",
        expected_entities=["nextjs", "react", "nodejs"],
        expected_affected_dependents=["customer_portal_web"],
        unsupported_dependents=["fastapi", "pydantic", "postgresql"],
        ground_truth_query="How do cookies and headers work in Next.js 15?",
        expected_relevant_keywords=["async", "await", "cookies", "headers", "promises"],
    ),
    EvaluationSample(
        id="sample-new-cloudflare-outage",
        scenario="new_announcement",
        title="Cloudflare Status: Major Outage affecting DNS and Pages Routing",
        content=(
            "Cloudflare is experiencing a major outage affecting edge DNS resolution and Pages routing across North America. "
            "Edge workers returning 522 connection timed out. Engineering team is actively rerouting traffic."
        ),
        source_url="https://www.cloudflarestatus.com/incidents/dns-outage-2024",
        publisher="Cloudflare Status",
        ecosystem="cloud",
        published_at="2024-06-10T16:00:00Z",
        version="incident-2024-06-10",
        expected_event_category="outage",
        expected_severity="critical",
        expected_primary_tech="cloudflare",
        expected_entities=["cloudflare"],
        expected_affected_dependents=["customer_portal_web", "internal_crm_service"],
        unsupported_dependents=["python", "starlette"],
        ground_truth_query="Is there an ongoing outage affecting Cloudflare edge services?",
        expected_relevant_keywords=["outage", "dns", "522", "pages"],
    ),

    # =========================================================================
    # SCENARIO 2: REVISED ANNOUNCEMENTS (Version Updates & Timelines)
    # =========================================================================
    EvaluationSample(
        id="sample-revised-pydantic-v2-migration",
        scenario="revised_announcement",
        title="Pydantic V2 Migration Guide (Revised): Extended support for V1 models in v2.7",
        content=(
            "Update: Pydantic 2.7 introduces a compatibility layer restoring temporary support for legacy `pydantic.v1` "
            "modules, allowing hybrid codebases to defer complete migration until Pydantic 3.0."
        ),
        source_url="https://docs.pydantic.dev/2.7/migration_updated/",
        publisher="Pydantic Official",
        ecosystem="python",
        published_at="2024-04-12T11:00:00Z",
        version="2.7.0",
        expected_event_category="deprecation",
        expected_severity="medium",
        expected_primary_tech="pydantic",
        expected_entities=["pydantic"],
        expected_affected_dependents=["fastapi"],
        unsupported_dependents=["angular", "ruby"],
        ground_truth_query="Can Pydantic V1 models be run alongside Pydantic 2.7?",
        expected_relevant_keywords=["pydantic.v1", "compatibility", "hybrid", "defer"],
    ),
    EvaluationSample(
        id="sample-revised-cve-fastapi-patch",
        scenario="revised_announcement",
        title="CVE-2024-24762 Fix Released in FastAPI 0.109.2",
        content=(
            "FastAPI 0.109.2 has been released addressing CVE-2024-24762. The Content-Type parser now enforces strict length limits "
            "and linear matching to prevent denial of service."
        ),
        source_url="https://github.com/tiangolo/fastapi/releases/tag/0.109.2",
        publisher="FastAPI GitHub",
        ecosystem="python",
        published_at="2024-02-10T12:00:00Z",
        version="0.109.2",
        expected_event_category="security_vulnerability",
        expected_severity="high",
        expected_primary_tech="fastapi",
        expected_entities=["fastapi"],
        expected_affected_dependents=["internal_crm_service"],
        unsupported_dependents=["rust", "go"],
        ground_truth_query="Which version of FastAPI patches CVE-2024-24762?",
        expected_relevant_keywords=["0.109.2", "fixed", "patch", "linear matching"],
    ),

    # =========================================================================
    # SCENARIO 3: DUPLICATE DOCUMENTS (Exact or Near-Identical Content)
    # =========================================================================
    EvaluationSample(
        id="sample-duplicate-pydantic-v2-mirror",
        scenario="duplicate_document",
        title="Pydantic V2 Migration Guide: Breaking changes to validator and root_validator (Mirror)",
        content=(
            "Pydantic V2 is a complete rewrite in Rust. Breaking change: `@validator` is replaced by `@field_validator`. "
            "`@root_validator` is replaced by `@model_validator`. `dict()` is replaced by `model_dump()`, "
            "and `json()` is replaced by `model_dump_json()`. Schema generation methods have changed."
        ),
        source_url="https://mirror.pydantic.org/v2/migration",
        publisher="Pydantic Mirror",
        ecosystem="python",
        published_at="2023-06-30T12:05:00Z",
        version="2.0.0",
        expected_event_category="breaking_change",
        expected_severity="high",
        expected_primary_tech="pydantic",
        expected_entities=["pydantic"],
        expected_affected_dependents=["fastapi"],
        ground_truth_query="How are root validators migrated in Pydantic V2?",
        expected_relevant_keywords=["model_validator", "field_validator"],
    ),

    # =========================================================================
    # SCENARIO 4: OUTDATED / SUPERSEDED INFORMATION
    # =========================================================================
    EvaluationSample(
        id="sample-outdated-fastapi-on-event-docs",
        scenario="outdated_information",
        title="FastAPI 0.95.0 Tutorial: Registering Startup and Shutdown Events",
        content=(
            "To run events before the application starts up, register `@app.on_event('startup')`. "
            "To run cleanup events, register `@app.on_event('shutdown')`. This is the recommended pattern for initializing databases."
        ),
        source_url="https://fastapi.tiangolo.com/v095/events/",
        publisher="FastAPI Legacy Docs",
        ecosystem="python",
        published_at="2023-03-01T09:00:00Z",
        version="0.95.0",
        is_superseded=True,
        superseded_by_sample_id="sample-new-fastapi-lifespan",
        expected_event_category="general_update",
        expected_severity="low",
        expected_primary_tech="fastapi",
        expected_entities=["fastapi"],
        temporal_as_of="2024-06-01T00:00:00Z",
        ground_truth_query="Is app.on_event('startup') still the recommended pattern for FastAPI today?",
        expected_relevant_keywords=["deprecated", "lifespan", "superseded", "no longer recommended"],
    ),

    # =========================================================================
    # SCENARIO 5: CONFLICTING SOURCES
    # =========================================================================
    EvaluationSample(
        id="sample-conflicting-blog-pydantic-v2",
        scenario="conflicting_sources",
        title="TechBlog: Pydantic V2 will retain validator decorators without changes",
        content=(
            "Contrary to rumors, Pydantic V2 will not require code changes for standard models. "
            "Existing `@validator` decorators will work indefinitely with full backward compatibility."
        ),
        source_url="https://unverified-techblog.com/pydantic-v2-rumors",
        publisher="TechBlog Speculation",
        ecosystem="python",
        published_at="2023-05-10T10:00:00Z",
        version="1.0-draft",
        expected_conflict=True,
        expected_primary_tech="pydantic",
        expected_entities=["pydantic"],
        ground_truth_query="Does Pydantic V2 maintain indefinite backward compatibility for @validator decorators?",
        expected_relevant_keywords=["conflict", "breaking", "replaced", "field_validator"],
    ),

    # =========================================================================
    # SCENARIO 6: UNSUPPORTED DEPENDENCY SCENARIOS (Testing Hallucination Resistance)
    # =========================================================================
    EvaluationSample(
        id="sample-unsupported-kafka-rails",
        scenario="unsupported_dependency",
        title="Unrelated Ecosystem Query: Apache Kafka and Ruby on Rails",
        content=(
            "A question about whether Apache Kafka's distributed broker architecture depends on Ruby on Rails ActiveRecord ORM."
        ),
        source_url="https://example.com/unrelated-inquiry",
        publisher="Synthetic Test",
        ecosystem="generic",
        published_at="2024-01-01T00:00:00Z",
        version="1.0",
        expected_entities=[],
        expected_affected_dependents=[],  # STRICTLY EMPTY
        unsupported_dependents=["fastapi", "pydantic", "react", "nextjs", "internal_crm_service"],
        ground_truth_query="Does Apache Kafka directly depend on Ruby on Rails ActiveRecord?",
        expected_relevant_keywords=["no dependency", "unsupported", "not found", "no evidence"],
    ),
    EvaluationSample(
        id="sample-unsupported-fastapi-react",
        scenario="unsupported_dependency",
        title="FastAPI to React Dependency Query",
        content=(
            "An inquiry asking if Python FastAPI core framework has an upstream runtime dependency on React 18."
        ),
        source_url="https://example.com/fastapi-react-query",
        publisher="Synthetic Test",
        ecosystem="python",
        published_at="2024-01-01T00:00:00Z",
        version="1.0",
        expected_entities=["fastapi", "react"],
        expected_affected_dependents=[],  # FastAPI does NOT depend on React
        unsupported_dependents=["react", "nextjs"],
        ground_truth_query="Does FastAPI runtime depend directly on React?",
        expected_relevant_keywords=["independent", "backend", "frontend", "no direct dependency"],
    ),
    EvaluationSample(
        id="sample-unsupported-docker-pydantic",
        scenario="unsupported_dependency",
        title="Docker Engine and Pydantic Dependency Inquiry",
        content=(
            "A query testing whether Docker Engine daemon depends on Python Pydantic V2 for container isolation."
        ),
        source_url="https://example.com/docker-pydantic-query",
        publisher="Synthetic Test",
        ecosystem="cloud",
        published_at="2024-01-01T00:00:00Z",
        version="1.0",
        expected_entities=["docker", "pydantic"],
        expected_affected_dependents=[],
        unsupported_dependents=["pydantic", "fastapi"],
        ground_truth_query="Does the Docker engine daemon depend on Pydantic for container isolation?",
        expected_relevant_keywords=["no", "golang", "independent", "unsupported"],
    ),
]
