# Changelog Impact Pipeline — Claude Code Instructions

## Project Overview

Build a staged, auditable pipeline that monitors public SDK and API changelogs, classifies changes, analyses impact on a codebase, and generates migration guides. The pipeline must be replayable from a clean checkout. Static precomputed outputs are not acceptable — every artifact must be regenerated at runtime.

---

## Repository Layout

Produce exactly this structure:

```
pipeline.py                  # main orchestrator, enforces stage machine
stages/
  __init__.py
  ingest.py                  # fetch + format-aware parse (markdown / html)
  filter.py                  # 90-day cutoff, writes parsed_changelogs/
  classify.py                # Stage 1: one LLM call per source
  impact.py                  # Stage 2: Stripe codebase impact analysis
  migrate.py                 # Stage 3: migration guide generation
  validate_code.py           # AST validation of generated Python after-blocks
  report.py                  # assembles impact_report.md + optional outputs
utils/
  __init__.py
  llm.py                     # single LLM wrapper, writes llm_calls.jsonl
  taxonomy.py                # controlled taxonomy constants + validation
  state.py                   # pipeline state machine
validate.py                  # standalone artifact validator (no pipeline rerun)
changelog_sources.json       # input — do not hardcode its content in code
codebase_snippet.py          # input — do not hardcode its content in code
parsed_changelogs/           # written at runtime, one file per source
requirements.txt
```

---

## Input Files

Read these from disk at runtime. Never hardcode their contents.

### `changelog_sources.json`
```json
{
  "sources": [
    {
      "source_id": "stripe_node",
      "name": "Stripe Node.js SDK",
      "url": "https://raw.githubusercontent.com/stripe/stripe-node/master/CHANGELOG.md",
      "format": "markdown"
    },
    {
      "source_id": "openai_python",
      "name": "OpenAI Python SDK",
      "url": "https://raw.githubusercontent.com/openai/openai-python/main/CHANGELOG.md",
      "format": "markdown"
    },
    {
      "source_id": "twilio",
      "name": "Twilio Changelog",
      "url": "https://www.twilio.com/en-us/changelog",
      "format": "html"
    }
  ]
}
```

### `codebase_snippet.py`
```python
# app/integrations/payment_gateway.py

import os
import stripe

stripe.api_key = os.environ["STRIPE_KEY"]

def create_payment_intent(amount_cents, currency, customer_id):
    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        customer=customer_id,
        payment_method_types=["card"],
        capture_method="automatic"
    )
    return intent.id, intent.client_secret

def list_recent_charges(customer_id, limit=10):
    charges = stripe.Charge.list(customer=customer_id, limit=limit)
    return [{"id": c.id, "amount": c.amount, "status": c.status} for c in charges.data]

def create_customer(email, name, metadata=None):
    return stripe.Customer.create(email=email, name=name, metadata=metadata or {})
```

---

## Environment Variables

The pipeline must read the Anthropic API key from the environment. Do not hardcode it.

```
ANTHROPIC_API_KEY=<set by user>
```

---

## LLM Configuration

- Provider: Anthropic
- Model: `claude-sonnet-4-5` (use this exact string)
- Use the `anthropic` Python SDK
- All LLM calls must go through `utils/llm.py` — no direct SDK calls elsewhere

---

## Pipeline Stage Machine — `utils/state.py`

Define an ordered list of stage names exactly as follows:

```python
STAGES = [
    "INIT",
    "SOURCES_LOADED",
    "CHANGELOGS_FETCHED",
    "ENTRIES_PARSED",
    "RECENT_ENTRIES_FILTERED",
    "CHANGES_CLASSIFIED",
    "HIGH_RISK_STRIPE_CHANGES_SELECTED",
    "CODEBASE_IMPACT_ANALYSED",
    "MIGRATION_GUIDES_GENERATED",
    "MIGRATION_CODE_VALIDATED",
    "IMPACT_REPORT_WRITTEN",
    "OPTIONAL_OUTPUTS_GENERATED",
    "VALIDATION_COMPLETE",
    "RESULTS_FINALISED",
]
```

The state machine must:
- Track current stage in memory during a run
- Expose an `advance(stage_name)` method
- Raise `RuntimeError` if `advance()` is called with a stage that is not the immediate next stage in the list
- This enforces that no stage can be skipped or run out of order

---

## Taxonomy — `utils/taxonomy.py`

Define these as Python sets/constants:

```python
CHANGE_TYPES = {"deprecation", "breaking", "enhancement", "bugfix", "security"}

BREAKING_RISK_LEVELS = {"critical", "high", "medium", "low", "none"}
```

Expose a `validate_classification(entry: dict) -> None` function that:
- Checks `change_type` is in `CHANGE_TYPES`
- Checks `breaking_risk` is in `BREAKING_RISK_LEVELS`
- Checks `affects_auth`, `affects_billing`, `affects_data_model` are booleans
- Raises `ValueError` with a descriptive message on any violation

All classified entries must pass this validation before being written to disk.

---

## LLM Wrapper — `utils/llm.py`

Function signature:

```python
def call_llm(
    stage: str,
    source_id: str | None,
    entry_ids: list[str],
    prompt: str,
    input_artifacts: list[str],
    output_artifact: str,
) -> str:
```

Behaviour:
- Calls the Anthropic API with `model="claude-sonnet-4-5"` and `max_tokens=4096`
- Appends one JSON record to `llm_calls.jsonl` (create or append, never overwrite the whole file)
- Returns the response text

Each log record must contain:

```json
{
  "stage": "stage_1_classification",
  "source_id": "stripe_node",
  "entry_ids": ["stripe_node-001", "stripe_node-002"],
  "timestamp": "2025-01-01T00:00:00Z",
  "provider": "anthropic",
  "model": "claude-sonnet-4-5",
  "prompt_hash": "<sha256 of prompt string>",
  "input_artifacts": ["parsed_changelogs/stripe_node.json"],
  "output_artifact": "classified_changes.json"
}
```

Compute `prompt_hash` as the SHA-256 hex digest of the UTF-8 encoded prompt string.

---

## Stage Implementations

### `stages/ingest.py` — Fetch and Parse

Fetch each source by URL. Handle connection errors gracefully — log the failure and continue.

**Markdown parser** (for `format: markdown`):
- Split on version/date headers: lines matching `## [version]` or `## YYYY-MM-DD` patterns
- Within each version block, extract individual change lines or sub-sections
- Each entry gets a deterministic `entry_id`: `{source_id}-{zero_padded_index}` e.g. `stripe_node-001`
- Parse `published_at` from the version header date if present, else `null`

**HTML parser** (for `format: html`):
- Use `beautifulsoup4` with `html.parser`
- Target changelog entry containers — look for dated sections or list items
- Extract date, title, and body text
- Same `entry_id` scheme

Each parsed entry schema:

```json
{
  "entry_id": "stripe_node-001",
  "source_id": "stripe_node",
  "source": "Stripe Node.js SDK",
  "version_or_date": "v16.0.0",
  "published_at": "2025-01-15",
  "change_title": "string",
  "change_body": "string",
  "change_type_raw": "string | null"
}
```

### `stages/filter.py` — 90-Day Filter

- Cutoff date = today minus 90 days, computed at runtime
- Keep entries where `published_at` is within the last 90 days
- If `published_at` is null, exclude the entry and log it as skipped
- If a source has zero entries after filtering, write an explicit result:

```json
{
  "source_id": "twilio",
  "entries": [],
  "reason": "No entries found within the last 90 days"
}
```

- Save to `parsed_changelogs/{source_id}.json`
- The 90-day filter must complete before any LLM call is made

### `stages/classify.py` — Stage 1 Classification

One LLM call per source. Do not batch sources together.

For each source, construct a prompt that includes:
- The filtered parsed entries for that source (as JSON)
- The full controlled taxonomy (change types and risk levels)
- The required output schema
- An explicit instruction not to invent categories outside the taxonomy

Expected output per entry:

```json
{
  "entry_id": "stripe_node-001",
  "change_type": "breaking",
  "breaking_risk": "high",
  "affects_auth": false,
  "affects_billing": true,
  "affects_data_model": false,
  "rationale": "string"
}
```

After receiving the response:
- Parse the JSON from the LLM output
- Run `validate_classification()` on every entry
- If validation fails, raise an error — do not silently drop invalid entries

Save all classified entries across all sources to `classified_changes.json`.

### `stages/impact.py` — Stage 2 Codebase Impact

Select Stripe entries where `breaking_risk` is `critical` or `high`.

If none exist:
- Write `codebase_impact.json` with `{"affected_functions": [], "explanation": "No high-risk Stripe changes found in the 90-day window."}`
- Log this as a no-op and continue

If high-risk entries exist, make one LLM call including:
- The selected high-risk Stripe entries
- The full contents of `codebase_snippet.py` (read from disk)
- Instruction to reason at function level and identify which functions are affected

Expected output per function:

```json
{
  "function_name": "create_payment_intent",
  "affected": true,
  "breaking_detail": "string",
  "suggested_fix_summary": "string",
  "related_entry_ids": ["stripe_node-001"]
}
```

Save to `codebase_impact.json`.

### `stages/migrate.py` — Stage 3 Migration Guides

Read affected functions from `codebase_impact.json`. Only functions where `affected: true` are included.

If no functions are affected, write `migration_guides.md` with a note explaining no migration is needed.

Otherwise, make one LLM call (or one call per affected function — either is acceptable) including:
- The affected function details from Stage 2
- The original function source from `codebase_snippet.py`
- Instruction to produce before/after Python code blocks and a one-sentence explanation

Required format per function in `migration_guides.md`:

```markdown
## Function: create_payment_intent

**Why this change is necessary:** One sentence explanation here.

### Before

```python
# original code
```

### After

```python
# corrected code
```
```

The after-code must be syntactically valid Python. Do not ask the LLM to comment out the fix — it must be real runnable code.

### `stages/validate_code.py` — AST Validation

- Extract all fenced Python code blocks from the `### After` sections of `migration_guides.md`
- For each block, attempt `ast.parse(code)`
- Record the result

Save to `migration_validation.json`:

```json
{
  "validated_at": "ISO-8601 timestamp",
  "results": [
    {
      "function_name": "create_payment_intent",
      "valid": true,
      "error": null
    }
  ],
  "all_valid": true
}
```

If any block is invalid, set `valid: false` and `error` to the exception message. Set `all_valid: false`. Do not raise — let the pipeline continue and flag it in the report.

### `stages/report.py` — Impact Report + Optional Outputs

**`impact_report.md`** must contain these sections in order:

1. **Executive Summary**
   - Total entries ingested (before filtering)
   - Entries remaining after 90-day filter
   - Breaking or high-risk change count (`breaking_risk` in `critical`, `high`)
   - Affected functions count

2. **Breaking Changes by Source** — one subsection per source

3. **Codebase Impact** — contents of `codebase_impact.json` rendered as readable text

4. **Migration Guides** — inline the content of `migration_guides.md`

5. **Unaffected Sources** — sources with zero recent entries or zero breaking changes

6. **Security Alerts** — if any entries have `change_type: security`, list them here

7. **Version Pinning Recommendations** — if `version_pinning.md` was generated, summarise it here

**`security_alerts.json`** — extract all entries where `change_type == "security"`:

```json
[
  {
    "entry_id": "string",
    "source_id": "string",
    "severity": "string",
    "summary": "string",
    "draft_slack_notification": "string"
  }
]
```

The `draft_slack_notification` must be a plain-text Slack message. It must not include API keys, internal URLs, or sensitive data.

**`version_pinning.md`** — for each source with breaking or high-risk changes, produce a pinning recommendation:

```markdown
## stripe (Python)

**Suggested pin:** `stripe==8.x.x`
**Reason:** Breaking change in PaymentIntent API detected.
**Unpin when:** Stripe publishes a migration guide and your codebase has been updated.
```

For Node dependencies, use npm-compatible syntax. For Python, use `requirements.txt` format.

---

## `pipeline.py` — Orchestrator

```python
def main():
    state = PipelineState()
    state.advance("INIT")

    sources = load_sources()          # reads changelog_sources.json
    state.advance("SOURCES_LOADED")

    raw = fetch_all(sources)          # stages/ingest.py — HTTP fetch only
    state.advance("CHANGELOGS_FETCHED")

    parsed = parse_all(raw, sources)  # stages/ingest.py — deterministic parse
    state.advance("ENTRIES_PARSED")

    filtered = filter_all(parsed)     # stages/filter.py — writes parsed_changelogs/
    state.advance("RECENT_ENTRIES_FILTERED")

    classified = classify_all(filtered)  # stages/classify.py — one call per source
    state.advance("CHANGES_CLASSIFIED")

    high_risk = select_high_risk_stripe(classified)
    state.advance("HIGH_RISK_STRIPE_CHANGES_SELECTED")

    impact = analyse_impact(high_risk)   # stages/impact.py
    state.advance("CODEBASE_IMPACT_ANALYSED")

    guides = generate_guides(impact)     # stages/migrate.py
    state.advance("MIGRATION_GUIDES_GENERATED")

    validation = validate_migration_code()  # stages/validate_code.py
    state.advance("MIGRATION_CODE_VALIDATED")

    write_report(classified, impact, validation)  # stages/report.py
    state.advance("IMPACT_REPORT_WRITTEN")

    write_optional_outputs(classified)   # security_alerts, version_pinning
    state.advance("OPTIONAL_OUTPUTS_GENERATED")

    run_validation()                     # calls validate.py logic
    state.advance("VALIDATION_COMPLETE")

    state.advance("RESULTS_FINALISED")
    print("Pipeline complete.")
```

---

## `validate.py` — Standalone Validator

This script must run independently without re-executing the pipeline.

Check and report on each of the following. Print a PASS/FAIL line for each check:

1. Required files exist: `classified_changes.json`, `codebase_impact.json`, `migration_guides.md`, `migration_validation.json`, `impact_report.md`, `llm_calls.jsonl`
2. `parsed_changelogs/` directory exists and contains one file per configured source
3. All JSON files are valid JSON
4. Every parsed entry contains required fields: `entry_id`, `source_id`, `source`, `version_or_date`, `published_at`, `change_title`, `change_body`
5. No entry in `parsed_changelogs/` has a `published_at` older than 90 days from today
6. `llm_calls.jsonl` contains at least one record with `stage` matching each of: `stage_1_classification`, `stage_2_impact`, `stage_3_migration`
7. `llm_calls.jsonl` contains separate records for each source ID in `changelog_sources.json`
8. All `change_type` values in `classified_changes.json` are in the allowed taxonomy
9. All `breaking_risk` values in `classified_changes.json` are in the allowed taxonomy
10. `codebase_impact.json` contains an `affected_functions` key
11. `migration_guides.md` exists and is non-empty (or contains explicit no-migration note)
12. `migration_validation.json` has an `all_valid` key
13. `impact_report.md` contains the strings: `Executive Summary`, `Breaking Changes`, `Codebase Impact`, `Migration Guides`, `Unaffected Sources`

Exit with code 0 if all checks pass. Exit with code 1 if any check fails. Print a summary count at the end.

---

## Required Artifacts Summary

These must exist after `python pipeline.py` completes:

| Artifact | Notes |
|---|---|
| `parsed_changelogs/{source_id}.json` | One per source |
| `classified_changes.json` | All sources combined |
| `codebase_impact.json` | Stripe only |
| `migration_guides.md` | Per affected function |
| `migration_validation.json` | AST results |
| `impact_report.md` | All sections required |
| `security_alerts.json` | If any security entries |
| `version_pinning.md` | If breaking changes found |
| `llm_calls.jsonl` | One record per LLM call |

---

## Dependencies — `requirements.txt`

```
anthropic
requests
beautifulsoup4
python-dateutil
```

No other external dependencies. Use Python stdlib for everything else (`ast`, `hashlib`, `json`, `datetime`, `pathlib`, `re`).

---

## Error Handling Rules

- If a changelog source fails to fetch: log the error, write an empty result for that source, continue the pipeline
- If the LLM returns invalid JSON: raise immediately with the raw response included in the error message
- If taxonomy validation fails: raise immediately — do not silently drop or coerce
- If AST validation fails on a migration code block: log it in `migration_validation.json`, set `all_valid: false`, continue
- If `codebase_snippet.py` cannot be read: raise immediately

---

## What Not To Do

- Do not make any LLM call before `RECENT_ENTRIES_FILTERED` is complete
- Do not batch multiple sources into a single Stage 1 classification call
- Do not hardcode changelog content, classification results, or any expected output
- Do not use any LLM call for parsing or date filtering — these must be deterministic
- Do not write to `llm_calls.jsonl` from anywhere except `utils/llm.py`
- Do not skip writing `parsed_changelogs/{source_id}.json` even if the source has zero recent entries

---

## Phase 2 — Stretch Goals (not in scope for this build)

The following are explicitly out of scope for the current build. Do not implement them yet:

- Delta simulation (`delta_processing_report.json`)
- TypeScript migration generation (`typescript_migration.md`)

These will be added in a follow-up session once the core pipeline is validated.