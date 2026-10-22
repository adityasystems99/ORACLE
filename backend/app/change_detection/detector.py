"""Change detection engine classifying raw signals into evidence-backed IntelligenceEvents."""

import logging
import re
from typing import List, Optional, Tuple
from ..schemas.event import ChangeCategory, EvidenceRef, IntelligenceEvent, SeverityLevel
from ..schemas.ingestion import RawSignal, SourceType
from ..storage.disk_store import DiskStore

logger = logging.getLogger(__name__)

BREAKING_PATTERNS = [
    r"\bbreaking\s+change[s]?\b",
    r"\bbackward[s]?\s+incompatible\b",
    r"\bdeprecated\b",
    r"\bremoved\s+in\s+v?\d+",
    r"\bno\s+longer\s+supported\b",
    r"\bmigration\s+guide\b",
]

VULNERABILITY_PATTERNS = [
    r"\bCVE-\d{4}-\d{4,7}\b",
    r"\bvulnerability\b",
    r"\bsecurity\s+advisory\b",
    r"\bremote\s+code\s+execution\b",
    r"\bdenial\s+of\s+service\b",
    r"\bprivilege\s+escalation\b",
    r"\bexploit\b",
]

OUTAGE_PATTERNS = [
    r"\boutage\b",
    r"\bmajor\s+outage\b",
    r"\bdegraded\s+performance\b",
    r"\bservice\s+disruption\b",
    r"\bincident\s+resolved\b",
]

KNOWN_TECH_ENTITIES = {
    "fastapi": ["fastapi", "starlette", "pydantic"],
    "pydantic": ["pydantic", "pydantic-core", "fastapi"],
    "python": ["python", "cpython", "pep", "pip"],
    "nodejs": ["node", "node.js", "npm", "v8"],
    "react": ["react", "react-dom", "nextjs", "vite"],
    "cloudflare": ["cloudflare", "workers", "pages", "dns"],
    "aws": ["aws", "s3", "lambda", "dynamodb", "ecs"],
    "postgresql": ["postgres", "postgresql", "psycopg", "pg"],
    "docker": ["docker", "containerd", "dockerfile"],
    "kubernetes": ["kubernetes", "k8s", "kubectl"],
}


class ChangeDetector:
    """Evaluates raw signals for breaking changes, vulnerabilities, and incidents."""

    def __init__(self, disk_store: Optional[DiskStore] = None):
        self.disk_store = disk_store

    def _extract_primary_technology(self, signal: RawSignal) -> Tuple[str, List[str]]:
        """Identify primary technology and related ecosystem entities."""
        text = f"{signal.title} {signal.content}".lower()
        matched_primary = "unknown"
        related: List[str] = []

        # Check metadata source name or repository first
        repo = signal.metadata.get("repository", "").lower()
        if repo:
            for tech, aliases in KNOWN_TECH_ENTITIES.items():
                if tech in repo:
                    return tech, aliases

        for tech, aliases in KNOWN_TECH_ENTITIES.items():
            for alias in aliases:
                if re.search(r"\b" + re.escape(alias) + r"\b", text):
                    matched_primary = tech
                    related = [a for a in aliases if a != tech]
                    return matched_primary, related

        # Fallback to source ecosystem
        eco = signal.metadata.get("ecosystem", "generic")
        return eco, []

    def _extract_cve(self, text: str) -> Optional[str]:
        """Extract CVE identifier if present."""
        match = re.search(r"\b(CVE-\d{4}-\d{4,7})\b", text, re.IGNORECASE)
        return match.group(1).upper() if match else None

    def _extract_evidence_snippet(self, text: str, pattern_list: List[str], max_len: int = 240) -> str:
        """Extract verbatim sentence or snippet matching trigger patterns."""
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start = max(0, match.start() - 60)
                end = min(len(text), match.end() + 180)
                snippet = text[start:end].strip()
                return f"...{snippet}..." if start > 0 else f"{snippet}..."
        return text[:max_len].strip() + ("..." if len(text) > max_len else "")

    def classify_signal(self, signal: RawSignal) -> Optional[IntelligenceEvent]:
        """Classify a single raw signal into an IntelligenceEvent, or None if negligible."""
        full_text = f"{signal.title}\n{signal.content}"
        primary_tech, related_entities = self._extract_primary_technology(signal)
        cve_id = self._extract_cve(full_text)

        category = ChangeCategory.GENERAL_UPDATE
        severity = SeverityLevel.LOW
        confidence = 0.70
        rationale = "General technological update or patch notice."
        trigger_patterns = []

        # 1. Security Vulnerabilities
        if cve_id or signal.source_type == SourceType.SECURITY_ADVISORY or any(re.search(p, full_text, re.I) for p in VULNERABILITY_PATTERNS):
            category = ChangeCategory.SECURITY_VULNERABILITY
            severity = SeverityLevel.CRITICAL if ("remote code" in full_text.lower() or "critical" in full_text.lower()) else SeverityLevel.HIGH
            confidence = 0.95 if cve_id else 0.85
            rationale = f"Detected security advisory/vulnerability alert ({cve_id or 'flaw'})."
            trigger_patterns = VULNERABILITY_PATTERNS

        # 2. Outages / Status incidents
        elif signal.source_type == SourceType.STATUS_PAGE or any(re.search(p, full_text, re.I) for p in OUTAGE_PATTERNS):
            category = ChangeCategory.OUTAGE
            impact = signal.metadata.get("impact", "").lower()
            severity = SeverityLevel.CRITICAL if impact == "critical" else SeverityLevel.HIGH if impact == "major" else SeverityLevel.MEDIUM
            confidence = 0.92
            rationale = f"Detected live service disruption/incident on {primary_tech}."
            trigger_patterns = OUTAGE_PATTERNS

        # 3. Breaking changes / Deprecations
        elif any(re.search(p, full_text, re.I) for p in BREAKING_PATTERNS):
            category = ChangeCategory.BREAKING_CHANGE if "breaking" in full_text.lower() else ChangeCategory.DEPRECATION
            severity = SeverityLevel.HIGH if category == ChangeCategory.BREAKING_CHANGE else SeverityLevel.MEDIUM
            confidence = 0.90
            rationale = f"Identified backward-incompatible breaking change or deprecation notice."
            trigger_patterns = BREAKING_PATTERNS

        # 4. Major releases
        elif "v" in signal.title and any(tag in signal.title for tag in [".0.0", ".0 ", "release"]):
            category = ChangeCategory.MAJOR_RELEASE
            severity = SeverityLevel.MEDIUM
            confidence = 0.85
            rationale = f"Detected major release milestone for {primary_tech}."
            trigger_patterns = [r"\bv?\d+\.0(\.0)?\b"]

        # Build evidence citation
        snippet = self._extract_evidence_snippet(full_text, trigger_patterns)
        evidence = EvidenceRef(
            source_url=signal.url,
            source_type=str(signal.source_type.value),
            title=signal.title,
            snippet=snippet,
            published_at=signal.published_at,
            content_hash=signal.content_hash,
        )

        event_id = f"evt_{signal.content_hash[:10]}"
        return IntelligenceEvent(
            id=event_id,
            raw_signal_id=signal.id,
            category=category,
            severity=severity,
            title=signal.title,
            summary=signal.content[:300].strip() + ("..." if len(signal.content) > 300 else ""),
            primary_technology=primary_tech,
            affected_entities=related_entities,
            cve_id=cve_id,
            confidence=confidence,
            detection_rationale=rationale,
            evidence=[evidence],
            timestamp=signal.retrieved_at,
            is_live_data=True,
            metadata=signal.metadata,
        )

    def process_signals(self, signals: List[RawSignal]) -> List[IntelligenceEvent]:
        """Detect and persist intelligence events from raw signals."""
        events: List[IntelligenceEvent] = []
        for signal in signals:
            event = self.classify_signal(signal)
            if event:
                events.append(event)
                if self.disk_store:
                    self.disk_store.upsert_item("events", event)

        logger.info(f"Classified {len(events)} intelligence events from {len(signals)} raw signals.")
        return events
