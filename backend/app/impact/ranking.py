"""Deterministic, transparent ranking engine for impact findings."""

from typing import List, Tuple
from pydantic import BaseModel, Field
from ..schemas.event import SeverityLevel
from ..schemas.investigation import (
    FindingPriority,
    ImpactCategory,
    ImpactStatus,
    InvestigationFinding,
)


class RankingRuleConfig(BaseModel):
    """Configurable scoring weights for deterministic finding prioritization."""
    weight_severity_critical: float = 40.0
    weight_severity_high: float = 28.0
    weight_severity_medium: float = 16.0
    weight_severity_low: float = 6.0

    weight_confirmed_status: float = 25.0
    weight_potential_status: float = 12.0
    weight_superseded_status: float = -20.0

    weight_direct_hop: float = 15.0
    weight_transitive_hop: float = 8.0
    weight_verified_evidence: float = 10.0

    boost_api_deprecation: float = 8.0
    boost_breaking_change: float = 10.0


class FindingRankingEngine:
    """Calculates transparent, deterministic scores and operational priorities for investigation findings.

    Reliability Rule: Use deterministic rules for measurable criteria without fabricating
    arbitrary probabilities or unverified financial figures.
    """

    def __init__(self, config: RankingRuleConfig = None):
        self.config = config or RankingRuleConfig()

    def score_finding(self, finding: InvestigationFinding, depth: int = 1) -> Tuple[float, FindingPriority, List[str]]:
        """Calculate finding score, assigned priority, and transparent audit explanation."""
        score = 0.0
        rules_applied: List[str] = []

        # 1. Severity weight
        if finding.severity == SeverityLevel.CRITICAL:
            score += self.config.weight_severity_critical
            rules_applied.append(f"+{self.config.weight_severity_critical} for CRITICAL severity level")
        elif finding.severity == SeverityLevel.HIGH:
            score += self.config.weight_severity_high
            rules_applied.append(f"+{self.config.weight_severity_high} for HIGH severity level")
        elif finding.severity == SeverityLevel.MEDIUM:
            score += self.config.weight_severity_medium
            rules_applied.append(f"+{self.config.weight_severity_medium} for MEDIUM severity level")
        else:
            score += self.config.weight_severity_low
            rules_applied.append(f"+{self.config.weight_severity_low} for LOW severity level")

        # 2. Impact Status certainty
        if finding.impact_status == ImpactStatus.CONFIRMED:
            score += self.config.weight_confirmed_status
            rules_applied.append(f"+{self.config.weight_confirmed_status} for CONFIRMED empirical impact")
        elif finding.impact_status == ImpactStatus.POTENTIAL:
            score += self.config.weight_potential_status
            rules_applied.append(f"+{self.config.weight_potential_status} for POTENTIAL exposed dependency")
        elif finding.impact_status == ImpactStatus.SUPERSEDED:
            score += self.config.weight_superseded_status
            rules_applied.append(f"{self.config.weight_superseded_status} penalty: superseded by newer version")

        # 3. Graph proximity
        if depth == 1:
            score += self.config.weight_direct_hop
            rules_applied.append(f"+{self.config.weight_direct_hop} for direct 1-hop relationship")
        else:
            score += self.config.weight_transitive_hop
            rules_applied.append(f"+{self.config.weight_transitive_hop} for transitive hop (depth {depth})")

        # 4. Verified primary evidence
        if finding.evidence_and_sources:
            score += self.config.weight_verified_evidence
            rules_applied.append(f"+{self.config.weight_verified_evidence} for {len(finding.evidence_and_sources)} verified evidence source(s)")

        # 5. Category-specific adjustments
        if finding.impact_category == ImpactCategory.API_DEPRECATION:
            score += self.config.boost_api_deprecation
            rules_applied.append(f"+{self.config.boost_api_deprecation} boost for API deprecation / sunset deadline")
        elif finding.impact_category == ImpactCategory.BREAKING_CHANGE:
            score += self.config.boost_breaking_change
            rules_applied.append(f"+{self.config.boost_breaking_change} boost for breaking change")

        # Clamp score to [0.0, 100.0]
        final_score = max(0.0, min(100.0, score))

        # Assign priority based on deterministic thresholds
        if final_score >= 75.0:
            priority = FindingPriority.P0_CRITICAL
        elif final_score >= 50.0:
            priority = FindingPriority.P1_HIGH
        elif final_score >= 25.0:
            priority = FindingPriority.P2_MEDIUM
        else:
            priority = FindingPriority.P3_LOW

        return final_score, priority, rules_applied

    def rank_findings(self, findings: List[InvestigationFinding]) -> List[InvestigationFinding]:
        """Sort findings deterministically by calculated score descending."""
        return sorted(findings, key=lambda f: f.score, reverse=True)
