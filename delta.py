"""
Stretch item 9: Changelog Diff Simulation.
Run standalone after the main pipeline: uv run delta.py

Loads today's stripe_node parsed snapshot, fabricates 2 new entries,
runs Stage 1 classification on the delta only, and writes delta_processing_report.json.
"""
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from utils.llm import call_llm
from utils.taxonomy import validate_classification
from stages.classify import _parse_json_array, _build_prompt

SNAPSHOT_SOURCE = Path("parsed_changelogs/stripe_node.json")
DELTA_SNAPSHOT_PATH = Path("delta_snapshot.json")
OUTPUT_PATH = Path("delta_processing_report.json")
SOURCE_ID = "stripe_node"
SOURCE_NAME = "Stripe Node.js SDK"


FABRICATED_ENTRIES = [
    {
        "entry_id": "stripe_node-DELTA-001",
        "source_id": SOURCE_ID,
        "source": SOURCE_NAME,
        "version_or_date": "v17.0.0-delta-sim",
        "published_at": date.today().isoformat(),
        "change_title": "Deprecate payment_method_types on PaymentIntent",
        "change_body": (
            "The payment_method_types parameter on PaymentIntent.create() is deprecated. "
            "Pass payment_method_configuration instead. Existing integrations will continue "
            "to work until the next major release, but new features will only be available "
            "via payment_method_configuration."
        ),
        "change_type_raw": "deprecated",
    },
    {
        "entry_id": "stripe_node-DELTA-002",
        "source_id": SOURCE_ID,
        "source": SOURCE_NAME,
        "version_or_date": "v17.0.0-delta-sim",
        "published_at": date.today().isoformat(),
        "change_title": "Breaking: capture_method 'automatic' renamed to 'automatic_async'",
        "change_body": (
            "The capture_method value 'automatic' on PaymentIntent has been renamed to "
            "'automatic_async' to better reflect its behaviour. Passing 'automatic' will "
            "raise an invalid_request_error starting in API version 2026-01-01. "
            "Update all PaymentIntent.create() calls that set capture_method='automatic'."
        ),
        "change_type_raw": "breaking",
    },
]


def main() -> int:
    if not SNAPSHOT_SOURCE.exists():
        print(f"[delta] {SNAPSHOT_SOURCE} not found — run pipeline.py first")
        return 1

    baseline = json.loads(SNAPSHOT_SOURCE.read_text(encoding="utf-8"))
    baseline_entries = baseline.get("entries", [])
    print(f"[delta] baseline: {len(baseline_entries)} entries from {SNAPSHOT_SOURCE}")

    # Confirm delta entry IDs don't collide with baseline
    existing_ids = {e["entry_id"] for e in baseline_entries}
    for e in FABRICATED_ENTRIES:
        if e["entry_id"] in existing_ids:
            print(f"[delta] ERROR: fabricated id {e['entry_id']!r} collides with baseline — abort")
            return 1

    # Write combined snapshot for auditability
    combined = {
        "source_id": SOURCE_ID,
        "snapshot_taken_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entries": baseline_entries + FABRICATED_ENTRIES,
    }
    DELTA_SNAPSHOT_PATH.write_text(json.dumps(combined, indent=2), encoding="utf-8")
    print(f"[delta] wrote combined snapshot ({len(combined['entries'])} entries) → {DELTA_SNAPSHOT_PATH}")

    # Classify delta entries ONLY
    print(f"[delta] classifying {len(FABRICATED_ENTRIES)} delta entries…", flush=True)
    prompt = _build_prompt(SOURCE_ID, FABRICATED_ENTRIES)
    response = call_llm(
        stage="stage_1_classification_delta",
        source_id=SOURCE_ID,
        entry_ids=[e["entry_id"] for e in FABRICATED_ENTRIES],
        prompt=prompt,
        input_artifacts=[str(DELTA_SNAPSHOT_PATH)],
        output_artifact=str(OUTPUT_PATH),
    )

    delta_classifications = _parse_json_array(response)
    for c in delta_classifications:
        validate_classification(c)

    # Verify only delta entry IDs appear in classification output
    classified_ids = {c.get("entry_id") for c in delta_classifications}
    delta_ids = {e["entry_id"] for e in FABRICATED_ENTRIES}
    leaked = classified_ids - delta_ids
    verification_ok = not leaked
    verification_note = (
        "Only delta entries were classified."
        if verification_ok
        else f"WARNING: unexpected entry IDs in output: {sorted(leaked)}"
    )

    report = {
        "snapshot_taken_at": combined["snapshot_taken_at"],
        "baseline_source": str(SNAPSHOT_SOURCE),
        "baseline_entry_count": len(baseline_entries),
        "delta_entry_count": len(FABRICATED_ENTRIES),
        "delta_entries": FABRICATED_ENTRIES,
        "delta_classifications": delta_classifications,
        "verification": verification_note,
        "verification_ok": verification_ok,
    }
    OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[delta] wrote {OUTPUT_PATH}")
    print(f"[delta] verification: {verification_note}")
    return 0 if verification_ok else 1


if __name__ == "__main__":
    sys.exit(main())
