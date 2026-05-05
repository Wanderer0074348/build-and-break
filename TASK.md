## BUILD

Build a replayable pipeline that monitors public SDK and API changelogs, parses recent entries deterministically, classifies changes by type and breaking-change risk, evaluates high-risk changes against a specific codebase snippet, generates migration guides, and produces a developer impact report.

This is not a one-shot changelog summary task. The evaluator will run your pipeline from a clean checkout, may replace changelog sources or code snippets with equivalent fixtures, and will verify that ingestion, 90-day filtering, classification, impact analysis, migration generation, and reporting are staged and auditable.

The pipeline must preserve intermediate artifacts, enforce classification taxonomies, log LLM calls, and ensure generated migration code is syntactically valid.

---

## INPUT FILES

Your pipeline must read these files from disk:

- `changelog_sources.json`
- `codebase_snippet.py`

The sample sources and code snippet below are provided for local testing. The evaluator may replace them with equivalent sources or snippets.

---

## SAMPLE `changelog_sources.json`

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

---

## SAMPLE `codebase_snippet.py`

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

## CONTROLLED TAXONOMY

Define the classification taxonomy in code and validate LLM outputs against it.

Allowed change types:

```text
deprecation
breaking
enhancement
bugfix
security
```

Allowed breaking risk levels:

```text
critical
high
medium
low
none
```

Classification fields:

```json
{
  "change_type": "deprecation | breaking | enhancement | bugfix | security",
  "breaking_risk": "critical | high | medium | low | none",
  "affects_auth": true,
  "affects_billing": true,
  "affects_data_model": true
}
```

---

## PIPELINE STAGES

Your implementation must enforce these stages in code:

```text
INIT
 -> SOURCES_LOADED
 -> CHANGELOGS_FETCHED
 -> ENTRIES_PARSED
 -> RECENT_ENTRIES_FILTERED
 -> CHANGES_CLASSIFIED
 -> HIGH_RISK_STRIPE_CHANGES_SELECTED
 -> CODEBASE_IMPACT_ANALYSED
 -> MIGRATION_GUIDES_GENERATED
 -> MIGRATION_CODE_VALIDATED
 -> IMPACT_REPORT_WRITTEN
 -> OPTIONAL_OUTPUTS_GENERATED
 -> VALIDATION_COMPLETE
 -> RESULTS_FINALISED
```

Impact analysis must not run before source-specific classification is complete.

Migration guides must not be generated before affected functions are identified.

---

## MUST COMPLETE

### 1. Changelog Ingestion and Parsing

Fetch all configured changelog sources.

Parse individual change entries deterministically before any LLM call.

Each parsed entry must include:

```json
{
  "entry_id": "string",
  "source_id": "stripe_node",
  "source": "Stripe Node.js SDK",
  "version_or_date": "string",
  "published_at": "ISO-8601 date | null",
  "change_title": "string",
  "change_body": "string",
  "change_type_raw": "string | null"
}
```

Apply the 90-day filter in code before any LLM classification.

Discard older entries before Stage 1.

If a source has no entries in the last 90 days, write an explicit empty result with a reason.

Save parsed entries to:

```text
parsed_changelogs/{source_id}.json
```

---

### 2. Change Classification

For each source, make one separate Stage 1 LLM call.

Do not batch multiple sources into one classification call.

Each call must include:

- recent parsed entries for that source
- controlled taxonomy
- output schema
- instruction not to invent categories

Each classified entry must include:

```json
{
  "entry_id": "string",
  "change_type": "breaking",
  "breaking_risk": "high",
  "affects_auth": false,
  "affects_billing": true,
  "affects_data_model": false,
  "rationale": "string"
}
```

Save output to `classified_changes.json`.

---

### 3. Codebase Impact Analysis

Make a Stage 2 LLM call for Stripe only.

This call must include:

- Stripe entries classified as `breaking_risk: critical` or `breaking_risk: high`
- `codebase_snippet.py`
- instruction to reason at function level

For each function, output:

```json
{
  "function_name": "create_payment_intent",
  "affected": true,
  "breaking_detail": "string",
  "suggested_fix_summary": "string",
  "related_entry_ids": ["stripe_node-001"]
}
```

If no high-risk Stripe changes are present, write `codebase_impact.json` with no affected functions and an explanation.

Save output to `codebase_impact.json`.

---

### 4. Migration Guide Generation

For each affected function from Stage 2, make a Stage 3 LLM call or one structured Stage 3 call containing only affected functions.

Each migration guide must include:

- before code from the current implementation
- after code with corrected implementation
- one-sentence explanation of why the change is necessary

The after code must be syntactically valid Python.

Save output to `migration_guides.md`.

---

### 5. Migration Code Validation

Extract the generated Python after-code blocks.

Validate them using deterministic tooling, such as Python AST parsing or compilation.

Save results to `migration_validation.json`.

If generated code is invalid, flag it and do not present it as ready to apply.

---

### 6. Developer Impact Report

Combine all stages into `impact_report.md`.

The report must include:

- Executive Summary
- Breaking Changes by Source
- Codebase Impact
- Migration Guides
- Unaffected Sources
- Security Alerts, if any
- Version Pinning Recommendation, if attempted

The executive summary must include:

- total changes ingested
- number of recent entries after 90-day filtering
- breaking or high-risk change count
- affected functions count

---

## SHOULD ATTEMPT

### 7. Security Change Escalation

Any entry classified as `change_type: security` must be extracted into `security_alerts.json`.

Each alert must include:

```json
{
  "entry_id": "string",
  "source_id": "string",
  "severity": "string",
  "summary": "string",
  "draft_slack_notification": "string"
}
```

Slack notifications must not include secrets or sensitive internal data.

---

### 8. Version Pinning Recommendation

Based on classified breaking changes, output exact dependency pinning recommendations.

Save to `version_pinning.md`.

For Python dependencies, use `requirements.txt` style.

For Node dependencies, use `package.json` or npm-compatible syntax.

Each recommendation must include:

- dependency name
- suggested pin
- reason
- when to unpin or upgrade

---

## STRETCH

### 9. Changelog Diff Simulation

Save today's parsed entries to a snapshot file.

Simulate a future run by adding 2 fabricated entries to the Stripe parsed changelog snapshot.

Re-run Stage 1 classification on the delta only.

Verify that only new entries are processed.

Save output to `delta_processing_report.json`.

---

### 10. Multi-Language Migration

Take the Stage 3 Python migration guide and produce an equivalent TypeScript migration using the Stripe Node.js SDK.

The TypeScript version must be functionally equivalent to the Python fix.

Save output to `typescript_migration.md`.

---

## REQUIRED ARTIFACTS

Your repository must produce:

- `changelog_sources.json`
- `codebase_snippet.py`
- `parsed_changelogs/`
- `classified_changes.json`
- `codebase_impact.json`
- `migration_guides.md`
- `migration_validation.json`
- `impact_report.md`
- `security_alerts.json`, if applicable
- `version_pinning.md`, if attempted
- `delta_processing_report.json`, if attempted
- `typescript_migration.md`, if attempted
- `llm_calls.jsonl`

---

## `llm_calls.jsonl` REQUIREMENTS

Log one JSON object per LLM call.

Each record must include:

```json
{
  "stage": "string",
  "source_id": "string | null",
  "entry_ids": ["string"],
  "timestamp": "ISO-8601 timestamp",
  "provider": "string",
  "model": "string",
  "prompt_hash": "string",
  "input_artifacts": ["path"],
  "output_artifact": "path"
}
```

There must be separate records for:

- each source-specific Stage 1 classification call
- Stage 2 Stripe codebase impact analysis
- Stage 3 migration guide generation
- TypeScript migration, if attempted

---

## VALIDATION REQUIREMENTS

The repository must include a validation command, for example:

```bash
make validate
```

or:

```bash
python validate.py
```

The validation command must check that:

- required artifacts exist
- JSON files are valid
- all configured sources were fetched or failures were logged
- parsed changelog entries include required fields
- the 90-day filter was applied before classification
- each source has its own Stage 1 LLM call record
- classification values use only the controlled taxonomy
- Stage 2 impact analysis uses the codebase snippet
- Stage 3 migration guides exist for affected functions
- generated after-code is validated as Python syntax
- impact report includes all required sections
- LLM call logs contain separate records for required stages

---

## EXECUTION REQUIREMENTS

The evaluator will run the pipeline from a clean checkout.

Generated artifacts may be deleted before evaluation.

The evaluator may replace `changelog_sources.json` and `codebase_snippet.py` with equivalent inputs.

Static precomputed outputs are not sufficient.

The solution must actually run the staged pipeline and regenerate required artifacts.

---

## TOOLS

Python is preferred.

Any LLM provider or AI tooling may be used.

---

## TECHNICAL CONSTRAINTS

- Fetch all configured changelogs.
- Parse changelog entries deterministically before LLM calls.
- Apply the 90-day filter in code before classification.
- Each source must have its own Stage 1 classification call.
- Do not batch multiple sources in one classification call.
- Stage 2 impact analysis must use the actual codebase snippet.
- Migration guide after-code must be syntactically valid Python.
- Validate generated migration code with deterministic tooling.
- Static precomputed outputs are not sufficient.