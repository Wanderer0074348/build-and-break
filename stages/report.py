import json
from collections import defaultdict
from pathlib import Path

from utils.taxonomy import BREAKING_RISK_LEVELS

REPORT_PATH = Path("impact_report.md")
SECURITY_PATH = Path("security_alerts.json")
PINNING_PATH = Path("version_pinning.md")
GUIDES_PATH = Path("migration_guides.md")
IMPACT_PATH = Path("codebase_impact.json")
PARSED_DIR = Path("parsed_changelogs")

HIGH_RISK = {"critical", "high"}


def write_report(
    sources: list[dict],
    parsed_lookup: dict[str, dict],
    filtered: dict[str, dict],
    classified: list[dict],
    impact: dict,
    validation: dict,
    parsed_total: int,
) -> None:
    filtered_total = sum(len(p.get("entries", [])) for p in filtered.values())
    high_risk_count = sum(1 for c in classified if c.get("breaking_risk") in HIGH_RISK)
    affected_count = sum(
        1 for f in impact.get("affected_functions", []) if f.get("affected")
    )

    by_source: dict[str, list[dict]] = defaultdict(list)
    for c in classified:
        sid = _source_id_from_entry_id(c["entry_id"])
        by_source[sid].append(c)

    security_entries = [c for c in classified if c.get("change_type") == "security"]
    pinning_written = _write_pinning(by_source, sources, parsed_lookup)
    _write_security(security_entries, parsed_lookup)

    lines: list[str] = []
    lines.append("# Changelog Impact Report\n")

    # 1. Executive Summary
    lines.append("## Executive Summary\n")
    lines.append(f"- Total entries ingested (before filtering): **{parsed_total}**")
    lines.append(f"- Entries remaining after 90-day filter: **{filtered_total}**")
    lines.append(f"- Breaking or high-risk changes (critical/high): **{high_risk_count}**")
    lines.append(f"- Affected functions in codebase: **{affected_count}**")
    if not validation.get("all_valid", True):
        lines.append("- ⚠️  One or more migration code blocks failed AST validation.")
    lines.append("")

    # 2. Breaking Changes by Source
    lines.append("## Breaking Changes by Source\n")
    source_name_by_id = {s["source_id"]: s["name"] for s in sources}
    for src in sources:
        sid = src["source_id"]
        entries = by_source.get(sid, [])
        breakers = [e for e in entries if e.get("breaking_risk") in HIGH_RISK
                    or e.get("change_type") == "breaking"]
        lines.append(f"### {source_name_by_id.get(sid, sid)} (`{sid}`)\n")
        if not breakers:
            lines.append("_No breaking or high-risk changes in the 90-day window._\n")
            continue
        for e in breakers:
            details = parsed_lookup.get(e["entry_id"], {})
            title = details.get("change_title", "(no title)")
            lines.append(
                f"- **{e['entry_id']}** — `{e['change_type']}` / risk `{e['breaking_risk']}` — {title}"
            )
            rationale = e.get("rationale")
            if rationale:
                lines.append(f"  - {rationale}")
        lines.append("")

    # 3. Codebase Impact
    lines.append("## Codebase Impact\n")
    explanation = impact.get("explanation")
    if explanation:
        lines.append(f"{explanation}\n")
    affected = [f for f in impact.get("affected_functions", []) if f.get("affected")]
    if affected:
        for f in affected:
            lines.append(f"### `{f['function_name']}`")
            lines.append(f"- Breaking detail: {f.get('breaking_detail', '')}")
            lines.append(f"- Suggested fix: {f.get('suggested_fix_summary', '')}")
            related = ", ".join(f.get("related_entry_ids", [])) or "—"
            lines.append(f"- Related entries: {related}")
            lines.append("")
    else:
        lines.append("_No functions in the codebase were marked as affected._\n")

    # 4. Migration Guides (inline)
    lines.append("## Migration Guides\n")
    if GUIDES_PATH.exists():
        guide_text = GUIDES_PATH.read_text(encoding="utf-8").strip()
        # Strip leading "# Migration Guides" heading if present to avoid double-heading.
        if guide_text.startswith("# Migration Guides"):
            guide_text = guide_text[len("# Migration Guides") :].lstrip("\n")
        lines.append(guide_text + "\n")
    else:
        lines.append("_No migration guides generated._\n")

    # 5. Unaffected Sources
    lines.append("## Unaffected Sources\n")
    unaffected: list[str] = []
    for src in sources:
        sid = src["source_id"]
        entries = filtered.get(sid, {}).get("entries", [])
        cls = by_source.get(sid, [])
        breakers = [e for e in cls if e.get("breaking_risk") in HIGH_RISK
                    or e.get("change_type") == "breaking"]
        if not entries:
            unaffected.append(f"- **{src['name']}** (`{sid}`): no entries in the last 90 days")
        elif not breakers:
            unaffected.append(f"- **{src['name']}** (`{sid}`): {len(entries)} recent entries, none breaking")
    if unaffected:
        lines.extend(unaffected)
    else:
        lines.append("_All sources had at least one breaking or high-risk change._")
    lines.append("")

    # 6. Security Alerts
    lines.append("## Security Alerts\n")
    if security_entries:
        for s in security_entries:
            details = parsed_lookup.get(s["entry_id"], {})
            lines.append(
                f"- **{s['entry_id']}** ({_source_id_from_entry_id(s['entry_id'])}) — "
                f"risk `{s['breaking_risk']}` — {details.get('change_title', '')}"
            )
            if s.get("rationale"):
                lines.append(f"  - {s['rationale']}")
        lines.append("\nSee `security_alerts.json` for draft Slack notifications.\n")
    else:
        lines.append("_No security-classified entries in the 90-day window._\n")

    # 7. Version Pinning Recommendations
    lines.append("## Version Pinning Recommendations\n")
    if pinning_written:
        lines.append(f"Pinning recommendations were written to `{PINNING_PATH.name}`. Summary:\n")
        lines.append(PINNING_PATH.read_text(encoding="utf-8"))
    else:
        lines.append("_No breaking or high-risk changes warranted a pinning recommendation._\n")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_optional_outputs(classified: list[dict]) -> None:
    """Optional outputs are written inline by write_report; this remains a no-op hook."""
    # security_alerts.json and version_pinning.md are handled inside write_report
    # so they share state. This function is kept to match the orchestrator stage.
    return None


def _source_id_from_entry_id(entry_id: str) -> str:
    # entry_id format: {source_id}-{NNN}
    return entry_id.rsplit("-", 1)[0]


def _write_security(security_entries: list[dict], parsed_lookup: dict[str, dict]) -> None:
    alerts = []
    for s in security_entries:
        details = parsed_lookup.get(s["entry_id"], {})
        title = details.get("change_title", "")
        body = details.get("change_body", "")
        summary = title or body[:160]
        sid = _source_id_from_entry_id(s["entry_id"])
        slack = (
            f":rotating_light: Security update from {sid}: {summary} "
            f"(risk: {s['breaking_risk']}). Review and patch promptly."
        )
        alerts.append({
            "entry_id": s["entry_id"],
            "source_id": sid,
            "severity": s["breaking_risk"],
            "summary": summary,
            "draft_slack_notification": slack,
        })
    SECURITY_PATH.write_text(json.dumps(alerts, indent=2), encoding="utf-8")


def _write_pinning(
    by_source: dict[str, list[dict]],
    sources: list[dict],
    parsed_lookup: dict[str, dict],
) -> bool:
    sections: list[str] = []
    name_by_id = {s["source_id"]: s["name"] for s in sources}

    pinning_map = {
        "stripe_node": ("stripe", "Node", "stripe@^X.Y.Z (pin to last known-good minor)"),
        "openai_python": ("openai", "Python", "openai==X.Y.Z (pin to last known-good patch)"),
        "twilio": ("twilio", "Python", "twilio==X.Y.Z (pin to last known-good patch)"),
    }

    for src in sources:
        sid = src["source_id"]
        cls = by_source.get(sid, [])
        breakers = [e for e in cls if e.get("breaking_risk") in HIGH_RISK
                    or e.get("change_type") == "breaking"]
        if not breakers:
            continue
        dep_name, lang, suggested = pinning_map.get(
            sid, (sid, "Unknown", f"{sid} (pin to last known-good version)")
        )
        rationales = []
        for e in breakers[:5]:
            title = parsed_lookup.get(e["entry_id"], {}).get("change_title", "")
            rationales.append(f"  - `{e['entry_id']}` ({e['change_type']}/{e['breaking_risk']}): {title}")
        sections.append(
            f"## {dep_name} ({lang})\n\n"
            f"**Suggested pin:** `{suggested}`\n"
            f"**Reason:** {len(breakers)} breaking or high-risk change(s) detected in the last 90 days.\n"
            f"**Unpin when:** the upstream maintainers publish a migration guide and your codebase has been "
            f"updated and tested against the new version.\n\n"
            f"Triggering entries:\n" + "\n".join(rationales) + "\n"
        )

    if not sections:
        if PINNING_PATH.exists():
            PINNING_PATH.unlink()
        return False

    PINNING_PATH.write_text("# Version Pinning Recommendations\n\n" + "\n".join(sections), encoding="utf-8")
    return True
