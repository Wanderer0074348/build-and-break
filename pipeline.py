import json
import subprocess
import sys
import time
from pathlib import Path

from stages.classify import classify_all
from stages.filter import filter_all
from stages.impact import analyse_impact, select_high_risk_stripe
from stages.ingest import fetch_all, parse_all
from stages.migrate import generate_guides
from stages.report import write_optional_outputs, write_report
from stages.validate_code import validate_migration_code
from utils.state import PipelineState

SOURCES_PATH = Path("changelog_sources.json")


def load_sources() -> list[dict]:
    if not SOURCES_PATH.exists():
        raise FileNotFoundError(f"Required input missing: {SOURCES_PATH}")
    data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"{SOURCES_PATH} must contain a non-empty 'sources' array")
    return sources


def _banner(stage: str, detail: str = "") -> None:
    bar = "─" * 60
    suffix = f" — {detail}" if detail else ""
    print(f"\n{bar}\n▶ {stage}{suffix}\n{bar}", flush=True)


def main() -> int:
    t0 = time.monotonic()
    state = PipelineState()
    state.advance("INIT")
    _banner("INIT", "pipeline starting")

    sources = load_sources()
    state.advance("SOURCES_LOADED")
    _banner("SOURCES_LOADED", f"{len(sources)} source(s): {[s['source_id'] for s in sources]}")

    _banner("CHANGELOGS_FETCHED", "fetching all sources…")
    raw = fetch_all(sources)
    state.advance("CHANGELOGS_FETCHED")
    for sid, payload in raw.items():
        if payload["error"]:
            print(f"  ✗ {sid}: FAILED — {payload['error']}")
        else:
            print(f"  ✓ {sid}: {len(payload['text']):,} bytes")

    _banner("ENTRIES_PARSED", "parsing markdown / html…")
    parsed = parse_all(raw, sources)
    parsed_total = sum(len(v) for v in parsed.values())
    state.advance("ENTRIES_PARSED")
    for sid, entries in parsed.items():
        print(f"  • {sid}: {len(entries)} entries")
    print(f"  Σ total parsed: {parsed_total}")

    _banner("RECENT_ENTRIES_FILTERED", "applying 90-day cutoff…")
    filtered = filter_all(parsed)
    filtered_total = sum(len(p.get("entries", [])) for p in filtered.values())
    state.advance("RECENT_ENTRIES_FILTERED")
    for sid, payload in filtered.items():
        n = len(payload.get("entries", []))
        if n == 0:
            print(f"  • {sid}: 0 entries (within window) → wrote empty result")
        else:
            print(f"  • {sid}: {n} entries within window")
    print(f"  Σ total within window: {filtered_total}")

    parsed_lookup = {e["entry_id"]: e for entries in parsed.values() for e in entries}

    _banner("CHANGES_CLASSIFIED", "Stage 1 — one LLM call per source")
    classified = classify_all(filtered)
    state.advance("CHANGES_CLASSIFIED")
    print(f"  classified entries: {len(classified)}")

    _banner("HIGH_RISK_STRIPE_CHANGES_SELECTED")
    high_risk = select_high_risk_stripe(classified)
    state.advance("HIGH_RISK_STRIPE_CHANGES_SELECTED")
    print(f"  high-risk Stripe entries: {len(high_risk)}")
    for c in high_risk:
        print(f"    - {c['entry_id']} risk={c['breaking_risk']} type={c['change_type']}")

    _banner("CODEBASE_IMPACT_ANALYSED", "Stage 2 — Stripe codebase impact")
    impact = analyse_impact(high_risk, parsed_lookup=parsed_lookup)
    state.advance("CODEBASE_IMPACT_ANALYSED")
    affected = [f for f in impact.get("affected_functions", []) if f.get("affected")]
    print(f"  affected functions: {len(affected)}")
    for f in affected:
        print(f"    - {f['function_name']}")

    _banner("MIGRATION_GUIDES_GENERATED", "Stage 3 — migration guides")
    generate_guides(impact)
    state.advance("MIGRATION_GUIDES_GENERATED")
    print("  wrote migration_guides.md")

    _banner("MIGRATION_CODE_VALIDATED", "AST-checking after-blocks…")
    validation = validate_migration_code()
    state.advance("MIGRATION_CODE_VALIDATED")
    results = validation.get("results", [])
    valid_n = sum(1 for r in results if r.get("valid"))
    print(f"  blocks validated: {valid_n}/{len(results)} valid (all_valid={validation.get('all_valid')})")
    for r in results:
        if not r.get("valid"):
            print(f"    ✗ {r.get('function_name')}: {r.get('error')}")

    _banner("IMPACT_REPORT_WRITTEN", "assembling impact_report.md…")
    write_report(
        sources=sources,
        parsed_lookup=parsed_lookup,
        filtered=filtered,
        classified=classified,
        impact=impact,
        validation=validation,
        parsed_total=parsed_total,
    )
    state.advance("IMPACT_REPORT_WRITTEN")
    print("  wrote impact_report.md")

    _banner("OPTIONAL_OUTPUTS_GENERATED", "security_alerts / version_pinning")
    write_optional_outputs(classified)
    state.advance("OPTIONAL_OUTPUTS_GENERATED")
    for path in ("security_alerts.json", "version_pinning.md"):
        if Path(path).exists():
            print(f"  ✓ {path}")
        else:
            print(f"  – {path} (not generated)")

    _banner("VALIDATION_COMPLETE", "running validate.py…")
    rc = subprocess.call([sys.executable, "validate.py"])
    state.advance("VALIDATION_COMPLETE")

    state.advance("RESULTS_FINALISED")
    elapsed = time.monotonic() - t0
    _banner("RESULTS_FINALISED", f"pipeline complete in {elapsed:.1f}s (validate.py exit={rc})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
