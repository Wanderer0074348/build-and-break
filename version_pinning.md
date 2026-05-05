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
