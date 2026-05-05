"""
Stretch item 10: produce a TypeScript equivalent of the Python migration guides.
Run standalone after the main pipeline: uv run typescript_migration.py
"""
import sys
from pathlib import Path

GUIDES_PATH = Path("migration_guides.md")
OUTPUT_PATH = Path("typescript_migration.md")

NO_MIGRATION_MARKERS = ["no migration is needed", "no affected functions"]


def main() -> int:
    if not GUIDES_PATH.exists():
        print(f"[typescript] {GUIDES_PATH} not found — run pipeline.py first")
        return 1

    guide_text = GUIDES_PATH.read_text(encoding="utf-8")

    lower = guide_text.lower()
    if any(m in lower for m in NO_MIGRATION_MARKERS):
        content = (
            "# TypeScript Migration Guides\n\n"
            "_No TypeScript migration needed: the Python migration guide contains no affected functions._\n"
        )
        OUTPUT_PATH.write_text(content, encoding="utf-8")
        print(f"[typescript] no migration needed — wrote note to {OUTPUT_PATH}")
        return 0

    from utils.llm import call_llm

    prompt = (
        "You are producing TypeScript migration guides that are functionally equivalent to the "
        "Python guides below, but using the Stripe Node.js SDK.\n\n"
        "Rules:\n"
        "- Use the same ## Function / ### Before / ### After section structure.\n"
        "- All After blocks must be valid TypeScript using `stripe` (Node.js SDK).\n"
        "- Preserve the same one-sentence **Why this change is necessary:** line.\n"
        "- Do not output any prose outside the specified sections.\n\n"
        "## Python migration guides to translate\n\n"
        f"{guide_text}\n"
    )

    print(f"[typescript] calling LLM to generate TypeScript migration…", flush=True)
    response = call_llm(
        stage="typescript_migration",
        source_id="stripe_node",
        entry_ids=[],
        prompt=prompt,
        input_artifacts=[str(GUIDES_PATH)],
        output_artifact=str(OUTPUT_PATH),
    )

    content = "# TypeScript Migration Guides\n\n" + response.strip() + "\n"
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"[typescript] wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
