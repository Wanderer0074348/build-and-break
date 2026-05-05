import json
import sys
from datetime import date, timedelta
from pathlib import Path

from utils.taxonomy import BREAKING_RISK_LEVELS, CHANGE_TYPES

REQUIRED_FILES = [
    "classified_changes.json",
    "codebase_impact.json",
    "migration_guides.md",
    "migration_validation.json",
    "impact_report.md",
    "llm_calls.jsonl",
]
PARSED_DIR = Path("parsed_changelogs")
SOURCES_PATH = Path("changelog_sources.json")

REQUIRED_PARSED_FIELDS = [
    "entry_id", "source_id", "source", "version_or_date",
    "published_at", "change_title", "change_body",
]
REQUIRED_REPORT_SECTIONS = [
    "Executive Summary", "Breaking Changes", "Codebase Impact",
    "Migration Guides", "Unaffected Sources",
]
REQUIRED_STAGES = {"stage_1_classification", "stage_2_impact", "stage_3_migration"}


class CheckRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        status = "PASS" if ok else "FAIL"
        suffix = f" — {detail}" if detail else ""
        print(f"[{status}] {name}{suffix}")
        if ok:
            self.passed += 1
        else:
            self.failed += 1


def _load_sources() -> list[dict]:
    if not SOURCES_PATH.exists():
        return []
    try:
        return json.loads(SOURCES_PATH.read_text(encoding="utf-8")).get("sources", [])
    except Exception:
        return []


def _load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            records.append(json.loads(ln))
    return records


def main() -> int:
    runner = CheckRunner()
    sources = _load_sources()
    source_ids = [s["source_id"] for s in sources]

    # 1. required files exist
    for fname in REQUIRED_FILES:
        runner.check(f"file exists: {fname}", Path(fname).exists())

    # 2. parsed_changelogs dir + one file per source
    runner.check("parsed_changelogs/ directory exists", PARSED_DIR.is_dir())
    for sid in source_ids:
        runner.check(
            f"parsed_changelogs/{sid}.json exists",
            (PARSED_DIR / f"{sid}.json").exists(),
        )

    # 3. JSON files are valid
    json_files = ["classified_changes.json", "codebase_impact.json", "migration_validation.json"]
    if PARSED_DIR.is_dir():
        json_files.extend(str(p) for p in PARSED_DIR.glob("*.json"))
    for fname in json_files:
        path = Path(fname)
        if not path.exists():
            runner.check(f"valid JSON: {fname}", False, "missing")
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            runner.check(f"valid JSON: {fname}", True)
        except Exception as e:
            runner.check(f"valid JSON: {fname}", False, str(e))

    # 4. parsed entries contain required fields
    if PARSED_DIR.is_dir():
        bad: list[str] = []
        for p in PARSED_DIR.glob("*.json"):
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            for entry in payload.get("entries", []):
                missing = [f for f in REQUIRED_PARSED_FIELDS if f not in entry]
                if missing:
                    bad.append(f"{p.name}:{entry.get('entry_id', '?')} missing {missing}")
        runner.check(
            "parsed entries have required fields",
            not bad,
            f"{len(bad)} bad entries: {bad[:3]}" if bad else "",
        )

    # 5. no entry older than 90 days
    cutoff = date.today() - timedelta(days=90)
    if PARSED_DIR.is_dir():
        old: list[str] = []
        for p in PARSED_DIR.glob("*.json"):
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            for entry in payload.get("entries", []):
                pub = entry.get("published_at")
                if not pub:
                    old.append(f"{p.name}:{entry.get('entry_id')} (no date)")
                    continue
                try:
                    if date.fromisoformat(pub[:10]) < cutoff:
                        old.append(f"{p.name}:{entry.get('entry_id')} ({pub})")
                except Exception:
                    old.append(f"{p.name}:{entry.get('entry_id')} (bad date {pub})")
        runner.check(
            "no parsed entry older than 90 days",
            not old,
            f"{len(old)} stale: {old[:3]}" if old else "",
        )

    # 6 & 7. llm_calls.jsonl checks
    log_path = Path("llm_calls.jsonl")
    if log_path.exists():
        try:
            records = _load_jsonl(log_path)
        except Exception as e:
            runner.check("llm_calls.jsonl is valid JSONL", False, str(e))
            records = []
        else:
            runner.check("llm_calls.jsonl is valid JSONL", True)

        present_stages = {r.get("stage") for r in records}
        for stage in REQUIRED_STAGES:
            runner.check(
                f"llm_calls.jsonl has stage record: {stage}",
                stage in present_stages,
            )

        for sid in source_ids:
            has_record = any(
                r.get("source_id") == sid and r.get("stage") == "stage_1_classification"
                for r in records
            )
            runner.check(
                f"llm_calls.jsonl has stage_1 record for source: {sid}",
                has_record,
            )
    else:
        runner.check("llm_calls.jsonl present", False)

    # 8 & 9. taxonomy values in classified_changes.json
    cls_path = Path("classified_changes.json")
    if cls_path.exists():
        try:
            classified = json.loads(cls_path.read_text(encoding="utf-8"))
        except Exception as e:
            runner.check("classified_changes.json parses", False, str(e))
            classified = []
        else:
            bad_ct = [c for c in classified if c.get("change_type") not in CHANGE_TYPES]
            bad_br = [c for c in classified if c.get("breaking_risk") not in BREAKING_RISK_LEVELS]
            runner.check(
                "all change_type values within taxonomy",
                not bad_ct,
                f"{len(bad_ct)} invalid" if bad_ct else "",
            )
            runner.check(
                "all breaking_risk values within taxonomy",
                not bad_br,
                f"{len(bad_br)} invalid" if bad_br else "",
            )

    # 10. codebase_impact.json has affected_functions
    imp_path = Path("codebase_impact.json")
    if imp_path.exists():
        try:
            imp = json.loads(imp_path.read_text(encoding="utf-8"))
            runner.check(
                "codebase_impact.json has 'affected_functions' key",
                "affected_functions" in imp,
            )
        except Exception as e:
            runner.check("codebase_impact.json parses", False, str(e))

    # 11. migration_guides.md exists and non-empty
    mg = Path("migration_guides.md")
    runner.check(
        "migration_guides.md is non-empty",
        mg.exists() and mg.stat().st_size > 0,
    )

    # 12. migration_validation.json has all_valid key
    mv = Path("migration_validation.json")
    if mv.exists():
        try:
            data = json.loads(mv.read_text(encoding="utf-8"))
            runner.check(
                "migration_validation.json has 'all_valid' key",
                "all_valid" in data,
            )
        except Exception as e:
            runner.check("migration_validation.json parses", False, str(e))

    # 13. impact_report.md sections
    ir = Path("impact_report.md")
    if ir.exists():
        text = ir.read_text(encoding="utf-8")
        for section in REQUIRED_REPORT_SECTIONS:
            runner.check(
                f"impact_report.md contains section: {section}",
                section in text,
            )

    print(f"\nSummary: {runner.passed} passed, {runner.failed} failed")
    return 0 if runner.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
