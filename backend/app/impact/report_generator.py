"""Markdown and textual dossier formatting for impact reports."""

from ..schemas.report import ImpactReport


def format_markdown_dossier(report: ImpactReport) -> str:
    """Format an ImpactReport into a clean, human-readable markdown briefing."""
    lines = [
        f"# [ORACLE INTELLIGENCE DOSSIER] {report.event_title}",
        f"**Report ID:** `{report.id}` | **Severity:** `{report.severity.value.upper()}` | **Confidence:** `{int(report.confidence_score * 100)}%`",
        f"**Target Technology:** `{report.primary_technology}` | **Ecosystem:** `{report.ecosystem}`",
        f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## Executive Summary",
        report.executive_summary,
        "",
        "## Technical Root Cause",
        report.technical_root_cause,
        "",
    ]

    if report.breaking_changes:
        lines.append("## Identified Breaking Changes")
        for bc in report.breaking_changes:
            lines.append(f"- {bc}")
        lines.append("")

    if report.impacted_components:
        lines.append("## Knowledge Graph Blast Radius")
        lines.append("| Component | Type | Depth | Likelihood | Dependency Path |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for comp in report.impacted_components:
            path_str = " -> ".join(comp.relationship_path) if comp.relationship_path else "Direct"
            lines.append(f"| `{comp.name}` | {comp.node_type.value} | {comp.depth} | {int(comp.impact_likelihood * 100)}% | `{path_str}` |")
        lines.append("")

    if report.evidence_trail:
        lines.append("## Evidence Provenance & Citations")
        for idx, ev in enumerate(report.evidence_trail, 1):
            lines.append(f"**[{idx}] {ev.title}**")
            lines.append(f"- Canonical URL: [{ev.source_url}]({ev.source_url})")
            lines.append(f"- Verbatim Snippet: > \"{ev.snippet}\"")
            lines.append(f"- Hash: `{ev.content_hash[:16]}`")
            lines.append("")

    if report.mitigation_playbook:
        lines.append("## Actionable Mitigation Playbook")
        for step in sorted(report.mitigation_playbook, key=lambda s: s.step_number):
            lines.append(f"### Step {step.step_number}: {step.title} [{step.priority.value.upper()}]")
            lines.append(step.description)
            if step.code_or_command:
                lines.append(f"```bash\n{step.code_or_command}\n```")
            if step.verification_check:
                lines.append(f"**Verification:** `{step.verification_check}`")
            lines.append("")

    prov = report.llm_provenance
    if prov:
        lines.append("---")
        lines.append(f"*Synthesized by LLM provider `{prov.get('provider')}` (model `{prov.get('model')}`, latency `{prov.get('latency_ms')}ms`)*")

    return "\n".join(lines)
