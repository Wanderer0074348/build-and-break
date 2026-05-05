import json
import re
from pathlib import Path

from utils.llm import call_llm

OUTPUT_PATH = Path("codebase_impact.json")
CODEBASE_PATH = Path("codebase_snippet.py")


def select_high_risk_stripe(classified: list[dict]) -> list[dict]:
    return [
        c for c in classified
        if c.get("entry_id", "").startswith("stripe_")
        and c.get("breaking_risk") in {"critical", "high"}
    ]


def analyse_impact(high_risk: list[dict], parsed_lookup: dict[str, dict] | None = None) -> dict:
    if not high_risk:
        result = {
            "affected_functions": [],
            "explanation": "No high-risk Stripe changes found in the 90-day window.",
        }
        with OUTPUT_PATH.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print("[impact] no high-risk Stripe entries; skipping LLM call")
        return result

    if not CODEBASE_PATH.exists():
        raise FileNotFoundError(f"Required input missing: {CODEBASE_PATH}")
    code_text = CODEBASE_PATH.read_text(encoding="utf-8")

    enriched = high_risk
    if parsed_lookup:
        merged = []
        for c in high_risk:
            details = parsed_lookup.get(c["entry_id"], {})
            merged.append({**c, "change_title": details.get("change_title"),
                           "change_body": details.get("change_body")})
        enriched = merged

    prompt = (
        "You are analysing the impact of high-risk Stripe SDK changes on a Python codebase.\n"
        "Reason at the function level. For each function in the codebase, decide whether any "
        "of the listed high-risk changes affects it. Only mark affected=true when there is a "
        "concrete reason linked to one or more entry_ids.\n\n"
        "## High-risk Stripe changes\n\n"
        f"{json.dumps(enriched, indent=2)}\n\n"
        "## Codebase under review (codebase_snippet.py)\n\n"
        "```python\n"
        f"{code_text}\n"
        "```\n\n"
        "## Output schema\n\n"
        "Return a single JSON object with this exact shape:\n"
        "{\n"
        '  "affected_functions": [\n'
        "    {\n"
        '      "function_name": "string",\n'
        '      "affected": true,\n'
        '      "breaking_detail": "string",\n'
        '      "suggested_fix_summary": "string",\n'
        '      "related_entry_ids": ["string"]\n'
        "    }\n"
        "  ],\n"
        '  "explanation": "string"\n'
        "}\n\n"
        "Include one object per function found in the codebase. Do not include any prose "
        "outside the JSON.\n"
    )

    response = call_llm(
        stage="stage_2_impact",
        source_id="stripe_node",
        entry_ids=[c["entry_id"] for c in high_risk],
        prompt=prompt,
        input_artifacts=["classified_changes.json", str(CODEBASE_PATH)],
        output_artifact=str(OUTPUT_PATH),
    )

    parsed = _parse_json_object(response)
    if "affected_functions" not in parsed:
        raise ValueError(
            f"Stage 2 LLM response missing 'affected_functions' key. Raw response:\n{response}"
        )

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2)
    return parsed


def _parse_json_object(text: str) -> dict:
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidate = fence.group(1).strip() if fence else text.strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Could not locate JSON object in LLM response. Raw response:\n{text}")
    snippet = candidate[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}. Raw response:\n{text}") from e
