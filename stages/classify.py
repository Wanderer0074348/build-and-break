import json
import re
from pathlib import Path

from utils.llm import call_llm
from utils.taxonomy import BREAKING_RISK_LEVELS, CHANGE_TYPES, validate_classification

OUTPUT_PATH = Path("classified_changes.json")


def classify_all(filtered: dict[str, dict]) -> list[dict]:
    """One LLM call per source. Returns combined classified entries."""
    all_classified: list[dict] = []
    for source_id, payload in filtered.items():
        entries = payload.get("entries", [])
        classified = _classify_source(source_id, entries)
        for c in classified:
            validate_classification(c)
        all_classified.extend(classified)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(all_classified, f, indent=2)
    return all_classified


def _classify_source(source_id: str, entries: list[dict]) -> list[dict]:
    input_artifact = f"parsed_changelogs/{source_id}.json"
    entry_ids = [e["entry_id"] for e in entries]

    prompt = _build_prompt(source_id, entries)
    response = call_llm(
        stage="stage_1_classification",
        source_id=source_id,
        entry_ids=entry_ids,
        prompt=prompt,
        input_artifacts=[input_artifact],
        output_artifact=str(OUTPUT_PATH),
    )

    if not entries:
        # Still made the call to satisfy auditing; nothing to classify.
        return []

    return _parse_json_array(response)


def _build_prompt(source_id: str, entries: list[dict]) -> str:
    if not entries:
        return (
            f"You are classifying changelog entries for source {source_id!r}.\n"
            "There are zero entries to classify in the last 90 days.\n"
            "Respond with exactly: []\n"
        )

    return (
        "You are a strict classifier for SDK / API changelog entries.\n"
        f"Source: {source_id}\n\n"
        "## Controlled taxonomy\n\n"
        f"Allowed change_type values (use exactly one): {sorted(CHANGE_TYPES)}\n"
        f"Allowed breaking_risk values (use exactly one): {sorted(BREAKING_RISK_LEVELS)}\n\n"
        "Do not invent any categories. Use only values from the lists above.\n\n"
        "## Required output schema (per entry)\n\n"
        "{\n"
        '  "entry_id": "string",\n'
        '  "change_type": "<one of allowed change_type values>",\n'
        '  "breaking_risk": "<one of allowed breaking_risk values>",\n'
        '  "affects_auth": <true|false>,\n'
        '  "affects_billing": <true|false>,\n'
        '  "affects_data_model": <true|false>,\n'
        '  "rationale": "string (1-2 sentences)"\n'
        "}\n\n"
        "Return a single JSON array with one object per input entry, in the same order. "
        "Do not wrap in extra keys. Do not include prose outside the JSON.\n\n"
        "## Entries to classify\n\n"
        f"{json.dumps(entries, indent=2)}\n"
    )


def _parse_json_array(text: str) -> list[dict]:
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        candidate = fence.group(1).strip()
    else:
        candidate = text.strip()
    start = candidate.find("[")
    end = candidate.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Could not locate JSON array in LLM response. Raw response:\n{text}")
    snippet = candidate[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}. Raw response:\n{text}") from e
