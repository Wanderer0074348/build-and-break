# Changelog Impact Report

## Executive Summary

- Total entries ingested (before filtering): **3866**
- Entries remaining after 90-day filter: **270**
- Breaking or high-risk changes (critical/high): **11**
- Affected functions in codebase: **0**

## Breaking Changes by Source

### Stripe Node.js SDK (`stripe_node`)

- **stripe_node-0015** — `breaking` / risk `low` — ⚠️ Change type of `Checkout.Session.payment_method_options.pix.setup_future_usage` and `PaymentIntent.payment_method_options.pix.setup_future_usage` from `literal('none')` to `enum('none'|'off_session
  - Marked with ⚠️, this changes the response type of setup_future_usage from a literal to an enum on Checkout.Session and PaymentIntent, which could break strict type comparisons in consumer code.
- **stripe_node-0045** — `breaking` / risk `low` — Changed `httpClient` config type from `HttpClient` class to `HttpClientInterface` interface.
  - Changes the httpClient config type from a concrete class to an interface, which could break existing code that passes HttpClient instances typed against the class.
- **stripe_node-0063** — `breaking` / risk `medium` — Removed top-level “stripe” ambient module. This allows import aliasing for the stripe package.
  - Removing the top-level 'stripe' ambient module is a breaking TypeScript change that will affect consumers relying on that ambient declaration.
- **stripe_node-0064** — `breaking` / risk `medium` — ⚠️ `Stripe.StripeContext` is no longer exported as a type. Use `Stripe.StripeContextType` instead.
  - Removes Stripe.StripeContext as an exported type, requiring consumers to migrate to Stripe.StripeContextType.
- **stripe_node-0065** — `breaking` / risk `medium` — ⚠️ `Stripe.errors.StripeError` is no longer a type. Use `typeof Stripe.errors.StripeError` or `Stripe.ErrorType` instead.
  - Removes Stripe.errors.StripeError as a usable type, requiring consumers to use typeof or the new ErrorType alias instead.
- **stripe_node-0066** — `breaking` / risk `high` — ⚠️ CJS entry point no longer exports .default or .Stripe as separate properties.
  - Removing .default and .Stripe from the CJS entry point will break CommonJS consumers that rely on those exports, a high-impact runtime breaking change.
- **stripe_node-0067** — `breaking` / risk `high` — ⚠️ Stripe import is now a true ES6 class. Use `new Stripe()` to create a StripeClient instead of calling it:
  - Requiring new Stripe() instead of calling Stripe() as a function is a fundamental API usage change that will break all existing call-style instantiation.
- **stripe_node-0068** — `breaking` / risk `high` — [#2645](https://github.com/stripe/stripe-node/pull/2645) ⚠️ Remove `stripeMethod` and standardize how function args are handled (including removing callback support)
  - Removing stripeMethod and callback support is a significant breaking change that affects all consumers using the callback pattern or extending via stripeMethod.
- **stripe_node-0069** — `breaking` / risk `medium` — ⚠️ Refactor how incoming method arguments are parsed. Type signatures for API methods should be _much_ more accurate and reliable now
  - Refactoring method argument parsing changes how arguments are handled, potentially breaking consumers relying on the previous lenient parsing behavior.
- **stripe_node-0070** — `breaking` / risk `high` — ⚠️ Remove support for providing callbacks to API methods. Use `async / await` instead
  - Removing callback support from all API methods is a critical breaking change requiring all callback-based consumers to migrate to async/await.
- **stripe_node-0071** — `breaking` / risk `high` — ⚠️ Remove support for passing a plain API key as a function arg. If supplied on a per-request basis, it should be in the `RequestOptions` under the `apiKey` property
  - Removing support for passing a plain API key as a function argument breaks all callers relying on per-request key passing in that style.
- **stripe_node-0072** — `breaking` / risk `high` — ⚠️ Keys from `params` and `options` objects are no longer mixed. If present on a method, `RequestParams` must always come first and `RequestOptions` must always come second. To supply options without 
  - Strictly separating params and options objects breaks any code that previously mixed keys from both in a single argument object.
- **stripe_node-0073** — `breaking` / risk `medium` — ⚠️ Removed methods from `StripeResource`: `createFullPath`, `createResourcePathWithSymbols`, `extend`, `method` and `_joinUrlParts`. These were mostly intended for internal use and we no longer need t
  - Removing internal methods from StripeResource breaks any third-party code or extensions that relied on these methods even though they were mostly internal.
- **stripe_node-0074** — `breaking` / risk `medium` — [#2643](https://github.com/stripe/stripe-node/pull/2643) ⚠️ Removed per-request host override. To use a custom host, set it in the client configuration. All requests from that client will use that hos
  - Removing the per-request host override forces consumers to configure the host at the client level, breaking any code that set host per request.
- **stripe_node-0076** — `breaking` / risk `low` — [#2638](https://github.com/stripe/stripe-node/pull/2638) Converted V2/Amount.ts to V2/V2Amount.ts
  - Renaming V2/Amount.ts to V2/V2Amount.ts is a breaking file-level change for any consumers directly importing from that internal path.
- **stripe_node-0079** — `breaking` / risk `high` — ⚠️ **Breaking change:** [#2617](https://github.com/stripe/stripe-node/pull/2617) Add decimal_string support with vendored Decimal type
  - Explicitly marked as a breaking change, introducing the Stripe.Decimal type for decimal_string fields that previously used string, requiring code changes across many financial fields.
- **stripe_node-0080** — `breaking` / risk `high` — All `decimal_string` fields changed type from `string` to `Stripe.Decimal` in both request params and response objects. Code that reads or writes these fields as `string` will need to use `Stripe.Deci
  - Changes the type of all decimal_string fields from string to Stripe.Decimal in both requests and responses, requiring widespread code changes.
- **stripe_node-0081** — `breaking` / risk `medium` — **Checkout.Session**: `currency_conversion.fx_rate`
  - The fx_rate field on Checkout.Session changes from string to Stripe.Decimal, breaking any code reading it as a string.
- **stripe_node-0082** — `breaking` / risk `medium` — **Climate.Order**: `metric_tons`; **Climate.Product**: `metric_tons_available`
  - metric_tons and metric_tons_available change from string to Stripe.Decimal, breaking existing string-based consumers.
- **stripe_node-0083** — `breaking` / risk `medium` — **CreditNoteLineItem**: `unit_amount_decimal`
  - unit_amount_decimal on CreditNoteLineItem changes from string to Stripe.Decimal, breaking string-based consumers.
- **stripe_node-0084** — `breaking` / risk `medium` — **InvoiceItem**: `quantity_decimal`, `unit_amount_decimal`
  - quantity_decimal and unit_amount_decimal on InvoiceItem change from string to Stripe.Decimal, breaking string-based consumers.
- **stripe_node-0085** — `breaking` / risk `medium` — **InvoiceLineItem**: `quantity_decimal`, `unit_amount_decimal`
  - quantity_decimal and unit_amount_decimal on InvoiceLineItem change from string to Stripe.Decimal, breaking string-based consumers.
- **stripe_node-0086** — `breaking` / risk `medium` — **Issuing.Authorization** / **Issuing.Transaction** (and TestHelpers): `quantity_decimal`, `unit_cost_decimal`, `gross_amount_decimal`, `local_amount_decimal`, `national_amount_decimal`
  - Multiple decimal fields on Issuing.Authorization and Issuing.Transaction change from string to Stripe.Decimal.
- **stripe_node-0087** — `breaking` / risk `medium` — **Plan**: `amount_decimal`, `flat_amount_decimal`, `unit_amount_decimal`
  - amount_decimal, flat_amount_decimal, and unit_amount_decimal on Plan change from string to Stripe.Decimal.
- **stripe_node-0088** — `breaking` / risk `medium` — **Price**: `unit_amount_decimal`, `flat_amount_decimal` (including `currency_options` and `tiers`)
  - unit_amount_decimal and flat_amount_decimal on Price (including currency_options and tiers) change from string to Stripe.Decimal.
- **stripe_node-0089** — `breaking` / risk `medium` — **V2.Core.Account** / **V2.Core.AccountPerson**: `percent_ownership`
  - percent_ownership on V2 Account and AccountPerson changes from string to Stripe.Decimal.
- **stripe_node-0090** — `breaking` / risk `medium` — Request params on **Invoice**, **Product**, **Quote**, **Subscription**, **SubscriptionItem**, **SubscriptionSchedule**, **PaymentLink**: `unit_amount_decimal`, `flat_amount_decimal`, `quantity_decima
  - Request param decimal fields across Invoice, Product, Quote, Subscription, etc. change from string to Stripe.Decimal.
- **stripe_node-0091** — `breaking` / risk `medium` — ⚠️ **Breaking change:** [#2618](https://github.com/stripe/stripe-node/pull/2618)[#2616](https://github.com/stripe/stripe-node/pull/2616) Throw an error when using the wrong webhook parsing method
  - Explicitly marked as a breaking change; now throws an error when the wrong webhook parsing method is used, changing previously silent behavior.
- **stripe_node-0092** — `breaking` / risk `medium` — ⚠️ **Breaking change:** [#2604](https://github.com/stripe/stripe-node/pull/2604) Add new OAuth Error classes
  - Explicitly marked as a breaking change; adds new OAuth Error classes that change how OAuth errors are represented and may break existing error handling code.
- **stripe_node-0093** — `breaking` / risk `high` — ⚠️ **Breaking change:** [#2609](https://github.com/stripe/stripe-node/pull/2609) Drop support for Node 16
  - Dropping Node 16 support is a critical breaking change for any consumers still running on Node 16.
- **stripe_node-0113** — `breaking` / risk `medium` — ⚠️ Remove support for `risk_level` on `Issuing.AuthorizationCreateParams.testHelpers.risk_assessment.card_testing_risk` and `Issuing.AuthorizationCreateParams.testHelpers.risk_assessment.merchant_disp
  - Removes risk_level from Issuing authorization test helper params, breaking any test code that passes this field.
- **stripe_node-0115** — `breaking` / risk `low` — ⚠️ Change type of `Issuing.Token.network_data.visa.card_reference_id` from `string` to `string | null`
  - Changes card_reference_id from string to string | null, which may break code that treats this field as always non-null.
- **stripe_node-0116** — `breaking` / risk `low` — ⚠️ Change type of `PaymentAttemptRecord.payment_method_details.card.brand` and `PaymentRecord.payment_method_details.card.brand` from `enum` to `enum | null`
  - Changes card brand from enum to enum | null, potentially breaking non-null assumptions in consumer code.
- **stripe_node-0117** — `breaking` / risk `low` — ⚠️ Change type of `PaymentAttemptRecord.payment_method_details.card.exp_month` and `PaymentRecord.payment_method_details.card.exp_month` from `longInteger` to `longInteger | null`
  - Changes card exp_month from longInteger to longInteger | null, potentially breaking non-null assumptions.
- **stripe_node-0118** — `breaking` / risk `low` — ⚠️ Change type of `PaymentAttemptRecord.payment_method_details.card.exp_year` and `PaymentRecord.payment_method_details.card.exp_year` from `longInteger` to `longInteger | null`
  - Changes card exp_year from longInteger to longInteger | null, potentially breaking non-null assumptions.
- **stripe_node-0119** — `breaking` / risk `low` — ⚠️ Change type of `PaymentAttemptRecord.payment_method_details.card.funding` and `PaymentRecord.payment_method_details.card.funding` from `enum('credit'|'debit'|'prepaid'|'unknown')` to `enum('credit'
  - Changes card funding from enum to enum | null, potentially breaking non-null assumptions in consumer code.
- **stripe_node-0120** — `breaking` / risk `low` — ⚠️ Change type of `PaymentAttemptRecord.payment_method_details.card.last4` and `PaymentRecord.payment_method_details.card.last4` from `string` to `string | null`
  - Changes card last4 from string to string | null, potentially breaking non-null assumptions in consumer code.
- **stripe_node-0121** — `breaking` / risk `low` — ⚠️ Change type of `PaymentAttemptRecord.payment_method_details.card.moto` and `PaymentRecord.payment_method_details.card.moto` from `boolean` to `boolean | null`
  - Changes card moto from boolean to boolean | null, potentially breaking strict boolean checks in consumer code.
- **stripe_node-0126** — `breaking` / risk `medium` — ⚠️ Remove support for `insights` on `Radar.PaymentEvaluation`
  - Removes the insights field from Radar.PaymentEvaluation, breaking any code that reads this field.
- **stripe_node-0130** — `breaking` / risk `medium` — ⚠️ Change type of `V2.Core.EventDestination.events_from` and `V2.Core.EventDestinationCreateParams.events_from` from `enum('other_accounts'|'self')` to `string`
  - Changes events_from type from a specific enum to string, which widens the type but breaks strict enum-based type checks in consumer code.
- **stripe_node-0144** — `breaking` / risk `low` — Change type of `PaymentAttemptRecord.payment_method_details.boleto.tax_id` and `PaymentRecord.payment_method_details.boleto.tax_id` from `string` to `string | null`
  - Changes boleto tax_id from string to string | null, potentially breaking non-null assumptions in consumer code.
- **stripe_node-0145** — `breaking` / risk `low` — Change type of `PaymentAttemptRecord.payment_method_details.us_bank_account.expected_debit_date` and `PaymentRecord.payment_method_details.us_bank_account.expected_debit_date` from `string | null` to 
  - Changes us_bank_account expected_debit_date from string | null to string, narrowing the type and potentially breaking null-handling code.
- **stripe_node-0148** — `breaking` / risk `low` — Remove support for unused `card_issuer_decline` on `Radar.PaymentEvaluation.insights`
  - Removes card_issuer_decline from Radar.PaymentEvaluation.insights, breaking any code that accesses this field.

### OpenAI Python SDK (`openai_python`)

- **openai_python-040** — `breaking` / risk `medium` — **types:** remove web_search_call.results from ResponseIncludable ([d3cc401](https://github.com/openai/openai-python/commit/d3cc40165cd86015833d15167cc7712b4102f932))
  - Removes web_search_call.results from the ResponseIncludable type, which is a breaking removal for any code referencing this type value.
- **openai_python-047** — `breaking` / risk `medium` — **types:** make type required in ResponseInputMessageItem ([cfdb167](https://github.com/openai/openai-python/commit/cfdb1676ea0550840330a58f1a31a40a41a0a53f))
  - Makes the type field required in ResponseInputMessageItem, which is a breaking change for code that creates this type without the field.
- **openai_python-059** — `breaking` / risk `medium` — **deps:** bump minimum typing-extensions version ([a2fb2ca](https://github.com/openai/openai-python/commit/a2fb2ca55142c6658a18be7bd1392a01f5a83f35))
  - Bumps the minimum required version of typing-extensions, which may break installations using older versions of this dependency.
- **openai_python-072** — `breaking` / risk `high` — **api:** The GA ComputerTool now uses the CompuerTool class. The 'computer_use_preview' tool is moved to ComputerUsePreview ([78f5b3c](https://github.com/openai/openai-python/commit/78f5b3c287b71ed6fb
  - Moves the GA ComputerTool to a new class and relocates 'computer_use_preview' to ComputerUsePreview, which is a breaking rename/restructure for existing code using these types.
- **openai_python-074** — `breaking` / risk `medium` — **api:** remove prompt_cache_key param from responses, phase field from message types ([44fb382](https://github.com/openai/openai-python/commit/44fb382698872d98d5f72c880b47846c7b594f4f))
  - Removes prompt_cache_key parameter from responses and the phase field from message types, breaking any code that relies on these fields.

### Twilio Changelog (`twilio`)

- **twilio-001** — `breaking` / risk `high` — Transit CallerID Sunset: Migrate to Verified CallerID or Immutable Call Forwarding Before May 31, 2026
  - The sunset of Transit CallerID forces customers to migrate to alternative solutions (Verified CallerID or Immutable Call Forwarding), which is a breaking change for any integration relying on presenting a different caller ID than the originating number. Failure to migrate before the deadline will result in loss of functionality.

## Codebase Impact

The codebase is written in Python and uses the Python Stripe SDK (stripe-python), whereas all listed high-risk changes (entry_ids stripe_node-0066 through stripe_node-0093) exclusively concern the stripe-node (Node.js/JavaScript) SDK. Breaking changes such as removal of CJS .default exports, the ES6 class instantiation requirement, removal of callback support, removal of plain API key as a function arg, and decimal_string type changes from string to Stripe.Decimal are all Node.js SDK-specific and do not apply to the Python SDK. Therefore, none of the functions in this Python codebase are concretely affected by any of the listed high-risk changes.

_No functions in the codebase were marked as affected._

## Migration Guides

_No migration is needed: no affected functions were identified for the high-risk Stripe changes in the 90-day window._

## Unaffected Sources

_All sources had at least one breaking or high-risk change._

## Security Alerts

_No security-classified entries in the 90-day window._

## Version Pinning Recommendations

Pinning recommendations were written to `version_pinning.md`. Summary:

# Version Pinning Recommendations

## stripe (Node)

**Suggested pin:** `stripe@^X.Y.Z (pin to last known-good minor)`
**Reason:** 43 breaking or high-risk change(s) detected in the last 90 days.
**Unpin when:** the upstream maintainers publish a migration guide and your codebase has been updated and tested against the new version.

Triggering entries:
  - `stripe_node-0015` (breaking/low): ⚠️ Change type of `Checkout.Session.payment_method_options.pix.setup_future_usage` and `PaymentIntent.payment_method_options.pix.setup_future_usage` from `literal('none')` to `enum('none'|'off_session
  - `stripe_node-0045` (breaking/low): Changed `httpClient` config type from `HttpClient` class to `HttpClientInterface` interface.
  - `stripe_node-0063` (breaking/medium): Removed top-level “stripe” ambient module. This allows import aliasing for the stripe package.
  - `stripe_node-0064` (breaking/medium): ⚠️ `Stripe.StripeContext` is no longer exported as a type. Use `Stripe.StripeContextType` instead.
  - `stripe_node-0065` (breaking/medium): ⚠️ `Stripe.errors.StripeError` is no longer a type. Use `typeof Stripe.errors.StripeError` or `Stripe.ErrorType` instead.

## openai (Python)

**Suggested pin:** `openai==X.Y.Z (pin to last known-good patch)`
**Reason:** 5 breaking or high-risk change(s) detected in the last 90 days.
**Unpin when:** the upstream maintainers publish a migration guide and your codebase has been updated and tested against the new version.

Triggering entries:
  - `openai_python-040` (breaking/medium): **types:** remove web_search_call.results from ResponseIncludable ([d3cc401](https://github.com/openai/openai-python/commit/d3cc40165cd86015833d15167cc7712b4102f932))
  - `openai_python-047` (breaking/medium): **types:** make type required in ResponseInputMessageItem ([cfdb167](https://github.com/openai/openai-python/commit/cfdb1676ea0550840330a58f1a31a40a41a0a53f))
  - `openai_python-059` (breaking/medium): **deps:** bump minimum typing-extensions version ([a2fb2ca](https://github.com/openai/openai-python/commit/a2fb2ca55142c6658a18be7bd1392a01f5a83f35))
  - `openai_python-072` (breaking/high): **api:** The GA ComputerTool now uses the CompuerTool class. The 'computer_use_preview' tool is moved to ComputerUsePreview ([78f5b3c](https://github.com/openai/openai-python/commit/78f5b3c287b71ed6fb
  - `openai_python-074` (breaking/medium): **api:** remove prompt_cache_key param from responses, phase field from message types ([44fb382](https://github.com/openai/openai-python/commit/44fb382698872d98d5f72c880b47846c7b594f4f))

## twilio (Python)

**Suggested pin:** `twilio==X.Y.Z (pin to last known-good patch)`
**Reason:** 1 breaking or high-risk change(s) detected in the last 90 days.
**Unpin when:** the upstream maintainers publish a migration guide and your codebase has been updated and tested against the new version.

Triggering entries:
  - `twilio-001` (breaking/high): Transit CallerID Sunset: Migrate to Verified CallerID or Immutable Call Forwarding Before May 31, 2026
