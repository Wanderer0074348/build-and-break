import json
import re
from pathlib import Path

from utils.llm import call_llm

IMPACT_PATH = Path("codebase_impact.json")
CODEBASE_PATH = Path("codebase_snippet.py")
OUTPUT_PATH = Path("migration_guides.md")


def generate_guides(impact: dict) -> str:
    affected = [f for f in impact.get("affected_functions", []) if f.get("affected")]

    if not affected:
        content = (
            "# Migration Guides\n\n"
            "_No migration is needed: no affected functions were identified for the high-risk "
            "Stripe changes in the 90-day window._\n"
        )
        OUTPUT_PATH.write_text(content, encoding="utf-8")
        return content

    if not CODEBASE_PATH.exists():
        raise FileNotFoundError(f"Required input missing: {CODEBASE_PATH}")
    code_text = CODEBASE_PATH.read_text(encoding="utf-8")
    function_sources = _extract_function_sources(code_text)

    payload = []
    for fn in affected:
        name = fn["function_name"]
        payload.append({
            "function_name": name,
            "breaking_detail": fn.get("breaking_detail", ""),
            "suggested_fix_summary": fn.get("suggested_fix_summary", ""),
            "related_entry_ids": fn.get("related_entry_ids", []),
            "original_source": function_sources.get(name, ""),
        })

    prompt = (
        "You are producing migration guides for affected Python functions.\n"
        "For each function below, output a markdown section using EXACTLY this format:\n\n"
        "## Function: <function_name>\n\n"
        "**Why this change is necessary:** <one sentence>\n\n"
        "### Before\n\n"
        "```python\n"
        "<original code, unchanged>\n"
        "```\n\n"
        "### After\n\n"
        "```python\n"
        "<corrected, runnable Python code>\n"
        "```\n\n"
        "Rules:\n"
        "- The After code MUST be syntactically valid Python — no commented-out fixes.\n"
        "- Do not invent additional functions. One section per function provided.\n"
        "- Do not output any prose outside the specified sections.\n\n"
        "## Functions to migrate\n\n"
        f"{json.dumps(payload, indent=2)}\n"
    )

    response = call_llm(
        stage="stage_3_migration",
        source_id="stripe_node",
        entry_ids=sorted({eid for fn in affected for eid in fn.get("related_entry_ids", [])}),
        prompt=prompt,
        input_artifacts=[str(IMPACT_PATH), str(CODEBASE_PATH)],
        output_artifact=str(OUTPUT_PATH),
    )

    content = "# Migration Guides\n\n" + response.strip() + "\n"
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    return content


_FUNC_RE = re.compile(r"^def\s+([a-zA-Z_]\w*)\s*\(", re.MULTILINE)


def _extract_function_sources(code_text: str) -> dict[str, str]:
    """Extract def-block source by function name (naive but deterministic)."""
    matches = list(_FUNC_RE.finditer(code_text))
    sources: dict[str, str] = {}
    for i, m in enumerate(matches):
        name = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(code_text)
        sources[name] = code_text[start:end].rstrip() + "\n"
    return sources
