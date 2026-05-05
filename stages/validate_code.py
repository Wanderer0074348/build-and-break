import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path

GUIDES_PATH = Path("migration_guides.md")
OUTPUT_PATH = Path("migration_validation.json")

_SECTION_RE = re.compile(
    r"##\s+Function:\s+(?P<name>[A-Za-z_]\w*)\s*\n.*?###\s+After\s*\n```python\s*\n(?P<code>.*?)```",
    re.DOTALL,
)


def validate_migration_code() -> dict:
    if not GUIDES_PATH.exists():
        result = {
            "validated_at": _now_iso(),
            "results": [],
            "all_valid": True,
            "note": "migration_guides.md not present — nothing to validate.",
        }
        OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    text = GUIDES_PATH.read_text(encoding="utf-8")
    matches = list(_SECTION_RE.finditer(text))

    results: list[dict] = []
    all_valid = True

    if not matches:
        # No After sections found: treat as no-migration scenario.
        result = {
            "validated_at": _now_iso(),
            "results": [],
            "all_valid": True,
            "note": "No '### After' Python blocks found in migration_guides.md.",
        }
        OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    for m in matches:
        name = m.group("name")
        code = m.group("code")
        try:
            ast.parse(code)
            results.append({"function_name": name, "valid": True, "error": None})
        except SyntaxError as e:
            all_valid = False
            results.append({"function_name": name, "valid": False, "error": str(e)})

    result = {
        "validated_at": _now_iso(),
        "results": results,
        "all_valid": all_valid,
    }
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
