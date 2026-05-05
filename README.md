# Changelog Impact Pipeline

Monitors public SDK and API changelogs, classifies changes, analyses impact on a codebase, and generates migration guides.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- An Anthropic API key

## Setup

```bash
# Install dependencies
uv sync

# Add your API key
cp .env.example .env
# then edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
# Full pipeline (fetch → classify → impact → migrate → report → validate)
uv run pipeline.py

# Standalone validator only (no LLM calls, reads existing artifacts)
uv run validate.py
```

## Stretch scripts

```bash
# Changelog diff simulation — fabricates 2 delta entries and classifies them
uv run delta.py

# TypeScript migration — translates migration_guides.md to TypeScript
uv run typescript_migration.py
```

Both require the main pipeline to have run first.

## Artifacts

Generated at runtime into the project root:

| File | Description |
|---|---|
| `parsed_changelogs/{source_id}.json` | Filtered changelog entries per source |
| `classified_changes.json` | All entries with change type and risk |
| `codebase_impact.json` | Affected functions in `codebase_snippet.py` |
| `migration_guides.md` | Before/after Python migration per function |
| `migration_validation.json` | AST validity of generated after-blocks |
| `impact_report.md` | Full developer impact report |
| `security_alerts.json` | Security-classified entries + Slack drafts |
| `version_pinning.md` | Pinning recommendations for breaking changes |
| `llm_calls.jsonl` | Audit log of every LLM call |
| `delta_processing_report.json` | Delta simulation output (stretch) |
| `typescript_migration.md` | TypeScript migration guides (stretch) |

## Inputs

Replace these files to run against a different codebase or sources:

- `changelog_sources.json` — list of changelog URLs and formats
- `codebase_snippet.py` — the Python code to analyse for impact
