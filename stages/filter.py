import json
from datetime import date, timedelta
from pathlib import Path

OUT_DIR = Path("parsed_changelogs")
WINDOW_DAYS = 90


def filter_all(parsed: dict[str, list[dict]]) -> dict[str, dict]:
    """Apply 90-day cutoff and write parsed_changelogs/{source_id}.json for every source."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = date.today() - timedelta(days=WINDOW_DAYS)
    results: dict[str, dict] = {}

    for source_id, entries in parsed.items():
        kept: list[dict] = []
        skipped_no_date = 0
        for entry in entries:
            published = entry.get("published_at")
            if not published:
                skipped_no_date += 1
                continue
            try:
                pub_date = date.fromisoformat(published[:10])
            except ValueError:
                skipped_no_date += 1
                continue
            if pub_date >= cutoff:
                kept.append(entry)

        if skipped_no_date:
            print(f"[filter] {source_id}: skipped {skipped_no_date} entries with missing/invalid date")

        path = OUT_DIR / f"{source_id}.json"
        if kept:
            payload = {
                "source_id": source_id,
                "entries": kept,
            }
        else:
            payload = {
                "source_id": source_id,
                "entries": [],
                "reason": "No entries found within the last 90 days",
            }
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        results[source_id] = payload

    return results
