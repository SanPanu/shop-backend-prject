# Implementation Plan: Test Suite for Shop-Backend

## Overview

Implement a comprehensive test suite for the Shop-Backend FastAPI application. The work is organised into five areas: infrastructure hardening, API test case completion, agent test case completion, property-based tests (new file), and UI/browser test completion. All tests build on the existing `conftest.py`, `helpers.py`, and partially-written test files.

## Tasks

- [ ] 1. Harden test infrastructure in `conftest.py` and `helpers.py`
  - [-] 1.1 Verify and extend `conftest.py` reset fixture to assert completion within 5 seconds
    - Wrap the `POST /test/reset` call in the `client` fixture with a timeout assertion; if the response takes longer than 5 s or returns a non-200 status the fixture should abort via `pytest.fail`
    - Confirm the fixture already pre-resets before every test; add the timeout guard if missing
    - _Requirements: 1.1, 1.3_
  - [ ]* 1.2 Write integration test for reset fixture isolation
    - Register a user, place an order, then reset; assert that stock, users, carts, and orders are back to seed state
    - _Requirements: 1.2, 1.3_
  - [-] 1.3 Extend `live_server` fixture with explicit 30-second health-poll loop and port-freed teardown
    - Confirm the existing poll loop waits up to 30 s before calling `pytest.fail`; add the teardown `proc.wait(timeout=10)` if missing
    - _Requirements: 1.4, 1.5_
  - [-] 1.4 Verify Playwright skip logic in `browser` fixture
    - Confirm `pytest.skip(...)` is raised with a descriptive reason when Playwright or Chromium is absent, and that the session does not fail
    - _Requirements: 1.6_
  - [-] 1.5 Verify report-writing logic in `pytest_sessionfinish` and skip-merge behaviour
    - Confirm `test-report/results.json` and `test-report/test_cases.csv` are written after every session
    - Confirm that when a test is skipped, any previously recorded result for that test ID is preserved (not overwritten) in the merged report
    - _Requirements: 1.7, 1.8_

- [ ] 2. Complete authentication API test cases in `test_cases_api.py`
  - [~] 2.1 Add missing boundary and blank-input auth tests
    - `TC-AUTH-007`-style: 7-char password → 422, 8-char non-whitespace → 201 (already present; verify)
    - `TC-AUTH-008`: blank name (spaces only) → 422
    - `TC-AUTH-012`: password of 8 spaces → 422
    - `TC-AUTH-010`: 101-char name → 422, 100-char name → 201
    - `TC-AUTH-013`: malformed domains (`a@b..c`, `a@.com`, `a@b.c.`, `a@b_c.com`) → 422 each
    - _Requirements: 2.6, 2.7, 2.8, 2.9, 2.10_
  - [ ]* 2.2 Write unit tests for auth validation edge cases
    - Parameterised test asserting correct HTTP status for each invalid input variant
    - _Requirements: 2.6, 2.7, 2.8, 2.9_
  - [~] 2.3 Add multi-session isolation and logout tests
    - `TC-AUTH-011`: logout invalidates only the specific token; other sessions for the same user remain valid
    - Verify `TC-AUTH-009` covers all four protected endpoints with all four bad header forms
    - _Requirements: 2.11, 2.12, 2.13, 2.14_
  - [~] 2.4 Add user-response password-field absence assertion
    - Verify login, register, and `GET /me` responses do not contain any key whose name contains `"password"`
    - _Requirements: 2.1, 2.15_

- [ ] 3. Complete product catalogue API test cases in `test_cases_api.py`
  - [~] 3.1 Add literal `%` and `_` search tests and SQL injection safety tests
    - `TC-PROD-011`: `q=%` finds only products 5 and 26; `q=_` returns nothing
    - `TC-PROD-012`: SQL injection payloads return 200 + empty list and leave 30 products intact
    - _Requirements: 3.5, 3.6_
  - [~] 3.2 Add multi-word search and `specs`-field search tests
    - `TC-PROD-016`: `mob`, `MOB` → products 9,11,15; `amoled` → product 11; `run sh` → 1,2,3; `red lip` → 20; `mob zzz` → nothing
    - Verify the search also combines with other filters
    - _Requirements: 3.4_
  - [~] 3.3 Add sort tie-breaking and combined-filter tests
    - `TC-PROD-006`: each sort option orders all 30 products correctly
    - `TC-PROD-014`: category + max_price + sort + limit combine correctly
    - `TC-PROD-008`: invalid sort, negative price, non-integer max_price, limit=0, limit=101, in_stock=maybe → 422 each
    - _Requirements: 3.8, 3.9, 3.10_
  - [~] 3.4 Add suggest endpoint tests
    - `TC-PROD-017`: 1-char query → empty; `mob` → correct category + product ordering; `ph` → word-start ranking; `zz`/`%%` → empty; limit=2 with total; limit=0 and limit=21 → 422; q >100 chars → 422
    - _Requirements: 3.14, 3.15_

- [ ] 4. Complete cart API test cases in `test_cases_api.py`
  - [~] 4.1 Add cart isolation and token-ownership tests
    - `TC-CART-008`: Alice and Bob have independent carts; Bob's DELETE on Alice's product → 404; Alice's cart unchanged
    - `TC-CART-010`: cart persists across re-login (new token)
    - _Requirements: 4.14, 4.15_
  - [~] 4.2 Add missing-body and malformed-body 422 tests
    - `TC-CART-011`: PUT with no body, PUT with `{}`, POST with no body → 422 each; quantity unchanged
    - _Requirements: 4.5, 4.8_
  - [~] 4.3 Verify cart arithmetic assertion in all mutating operations
    - Assert `subtotal == sum(unit_price × quantity for line in items)` and `line_total == unit_price × quantity` for responses from POST, PUT, DELETE, and GET /cart
    - _Requirements: 4.1, 4.16_

- [ ] 5. Complete coupon API test cases in `test_cases_api.py`
  - [~] 5.1 Add coupon floor-arithmetic and empty-cart tests
    - `TC-COUP-005`: 10% of ₹499 → discount is 49 or 50 (floor), and `subtotal − discount == total`
    - `TC-COUP-006`: empty cart + validate → 400
    - _Requirements: 5.1, 5.8, 5.9_
  - [~] 5.2 Add flat coupon minimum-order boundary test
    - `TC-COUP-003`: cart below minimum → 400 with minimum stated; cart above minimum → discount applied correctly
    - _Requirements: 5.2, 5.7_

- [ ] 6. Complete checkout API test cases in `test_cases_api.py`
  - [~] 6.1 Add card-format, declined-card, and empty-cart checkout rejection tests
    - `TC-CHK-003`: empty cart → 400 "Cart is empty"
    - `TC-CHK-004`: declined card → 402; no order, stock unchanged, cart intact
    - `TC-CHK-005`: 15 digits, 17 digits, letters, empty, spaces-in-card, missing card field → 422 each
    - `TC-CHK-012`: Arabic-Indic and full-width digits → 422
    - _Requirements: 6.3, 6.4, 6.5_
  - [~] 6.2 Add invalid shipping and missing shipping tests
    - `TC-CHK-014`: bad email, blank name, blank address, unknown state, bad PIN codes, wrong country, 201-char line, missing field → 422 each; no order, stock and cart unchanged
    - `TC-CHK-015`: no shipping object → 422
    - _Requirements: 6.8, 6.9_
  - [~] 6.3 Add invalid/expired coupon at checkout and minimum re-check tests
    - `TC-CHK-006`: expired and unknown coupon at checkout → 400 each; no order
    - `TC-CHK-007`: coupon minimum no longer met after cart modification → 400; no order
    - _Requirements: 6.6, 6.7_
  - [~] 6.4 Add concurrency oversell prevention test
    - `TC-CHK-009`: 6 users × 1 unit of a 2-stock product, simultaneous checkout via `live_server` + `threading.Barrier`; exactly 2 get 201, 4 get 409, final stock is 0
    - _Requirements: 6.10_
  - [~] 6.5 Add double-checkout (same-cart idempotency) and stock rollback tests
    - `TC-CHK-010`: two sequential checkouts from the same cart → first 201, second 400; one order, stock −1
    - `TC-CHK-011`: 8 concurrent checkouts for the same cart via `live_server` + `threading.Barrier`; exactly 1 succeeds, rest refused; one order, stock −1 (repeat 5 times)
    - `TC-CHK-008`: partial oversell at checkout rolls back all stock changes for the failing user
    - _Requirements: 6.11, 6.12_
  - [~] 6.6 Add shipping-details-stored and shipping-options tests
    - `TC-CHK-013`: full_name with leading/trailing spaces is trimmed in stored order; `GET /shipping/options` returns India, 36 states, fee 0
    - _Requirements: 6.1_
  - [ ]* 6.7 Write integration tests for checkout total arithmetic
    - Assert `total == subtotal − discount` and each `line_total == unit_price × quantity` for every successful checkout response
    - _Requirements: 6.13_

- [~] 7. Checkpoint — run API tests and verify suite is green
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Complete order API test cases in `test_cases_api.py`
  - [~] 8.1 Add order-detail field-match and timestamp tests
    - `TC-ORD-002`: order detail items, subtotal, discount, total match checkout response
    - `TC-ORD-006`: `created_at` is a UTC timestamp within the last minute
    - _Requirements: 7.3_
  - [~] 8.2 Add order isolation (cross-user 404) test
    - `TC-ORD-003`: another user's GET and cancel on a known order id → 404; order status unchanged
    - _Requirements: 7.2_
  - [~] 8.3 Add cancel-once and stock-restoration tests
    - `TC-ORD-004`: cancel once → status `cancelled`, stock restored; cancel again → 409, stock stays
    - `TC-ORD-007`: cancel then re-order the same product succeeds
    - _Requirements: 7.4, 7.5, 7.8_
  - [~] 8.4 Add concurrent cancel test
    - `TC-ORD-008`: 6 simultaneous cancel requests for one paid order via `live_server` + `threading.Barrier`; exactly 1 returns 200, rest get 409; stock restored exactly once (repeat 3 times)
    - _Requirements: 7.6_

- [ ] 9. Complete system and security API test cases in `test_cases_api.py`
  - [~] 9.1 Add full seed-state verification and home-page HTML test
    - `TC-SYS-001`: after reset, stock at seed values, new user gone, old tokens gone, seed users log in, empty carts and orders
    - `TC-SYS-002`: `GET /health` → `{"status": "ok"}`; `GET /products/999` error body has `"detail"` field
    - Verify `GET /` returns 200 with HTML containing `"Practice Shop"` (Requirement 8.4)
    - _Requirements: 8.1, 8.3, 8.4, 8.5_
  - [~] 9.2 Add reset endpoint access-control test
    - `TC-SEC-001`: no key, wrong key, empty key → 403 each; order survives; correct key → 200 reset
    - _Requirements: 8.2, 9.6_
  - [~] 9.3 Add cross-user cart and order access tests
    - `TC-SEC-002`: Bob cannot PUT or DELETE items from Alice's cart by guessing product ids; Bob cannot read Alice's orders by guessing ids → 404 everywhere; Alice's data unchanged
    - _Requirements: 9.1, 9.2_
  - [~] 9.4 Add HTML-in-name stored-as-plain-text test
    - `TC-SEC-003`: register with `<script>alert(1)</script>` as name; `GET /me` returns name unchanged as JSON string; response `content-type` is `application/json`
    - _Requirements: 9.3_
  - [~] 9.5 Add integer overflow 4xx safety test
    - `TC-SEC-004`: use `10^30` as product id, order id, min_price, max_price, limit, cart product_id, cart quantity, cart PUT/DELETE id → 4xx each (no 500)
    - _Requirements: 9.4_

- [ ] 10. Complete agent test cases in `test_agent.py`
  - [~] 10.1 Verify existing agent tests cover all Requirement 11 acceptance criteria
    - Cross-check `test_not_configured_and_login_required`, `test_tool_call_changes_cart_and_is_logged`, `test_tool_errors_are_reported_not_hidden`, `test_conversation_continues_and_is_private`, `test_step_limit_stops_a_looping_agent`, `test_agent_can_cancel_only_own_order`, `test_gemini_request_and_response_format`, `test_anthropic_and_custom_providers`, `test_model_errors_become_clear_messages` against Requirements 11.1–11.13
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 11.10, 11.11, 11.12, 11.13_
  - [~] 10.2 Add agent actions isolation test if not already covered
    - Assert `GET /agent/actions` returns only the requesting user's actions (Requirement 11.9)
    - The existing `test_tool_call_changes_cart_and_is_logged` already verifies Bob gets an empty list; confirm and annotate
    - _Requirements: 11.9_

- [ ] 11. Create `tests/test_properties.py` with Hypothesis property-based tests
  - [~] 11.1 Set up file, imports, and `hypothesis` settings baseline
    - Import `given`, `settings`, `st` from `hypothesis`; import `client` fixture from `conftest.py`; set `@settings(max_examples=100)` as default; add `hypothesis` to `requirements.txt`
    - _Requirements: 12.1_
  - [~] 11.2 Write Property 1 — product detail consistency
    - `# Feature: test-cases, Property 1: product detail consistency`
    - `@given(st.integers(min_value=1, max_value=30))` — fetch both `GET /products` list and `GET /products/{id}`; assert the objects are equal
    - _Requirements: 3.11, 12.1_
  - [ ]* 11.3 Write property test for Property 1
    - Tag: `# Feature: test-cases, Property 1: product detail consistency`
    - Validates: Requirements 3.11, 12.1
  - [~] 11.4 Write Property 2 — product field invariants
    - `# Feature: test-cases, Property 2: product field invariants`
    - `@given(st.integers(min_value=1, max_value=30))` — assert `price > 0`, `price ≤ mrp`, `stock ≥ 0`, `0 ≤ rating ≤ 5`, `in_stock == (stock > 0)`, `discount_percent == round((mrp − price) × 100 / mrp)`
    - _Requirements: 3.2, 3.3_
  - [ ]* 11.5 Write property test for Property 2
    - Tag: `# Feature: test-cases, Property 2: product field invariants`
    - Validates: Requirements 3.2, 3.3
  - [~] 11.6 Write Property 3 — cart arithmetic invariant
    - `# Feature: test-cases, Property 3: cart arithmetic invariant`
    - `@settings(max_examples=200)` — generate random sequences of add/update/remove operations on in-stock products; after each mutation assert `subtotal == sum(unit_price × quantity)` and each `line_total == unit_price × quantity`
    - Reset state via `client` fixture before each iteration
    - _Requirements: 4.1, 4.16, 12.4_
  - [ ]* 11.7 Write property test for Property 3
    - Tag: `# Feature: test-cases, Property 3: cart arithmetic invariant`
    - Validates: Requirements 4.1, 4.16, 12.4
  - [~] 11.8 Write Property 4 — coupon discount invariant
    - `# Feature: test-cases, Property 4: coupon discount invariant`
    - `@settings(max_examples=200)` — for each valid coupon validation response assert `discount ≥ 0`, `discount ≤ subtotal`, `total == subtotal − discount`
    - _Requirements: 5.9, 12.5_
  - [ ]* 11.9 Write property test for Property 4
    - Tag: `# Feature: test-cases, Property 4: coupon discount invariant`
    - Validates: Requirements 5.9, 12.5
  - [~] 11.10 Write Property 5 — percentage coupon floor arithmetic
    - `# Feature: test-cases, Property 5: percentage coupon floor arithmetic`
    - `@settings(max_examples=200)` — generate positive integer subtotals; validate WELCOME10 (10%); assert `discount == subtotal * 10 // 100`
    - _Requirements: 5.1_
  - [ ]* 11.11 Write property test for Property 5
    - Tag: `# Feature: test-cases, Property 5: percentage coupon floor arithmetic`
    - Validates: Requirements 5.1
  - [~] 11.12 Write Property 6 — checkout and order detail agreement
    - `# Feature: test-cases, Property 6: checkout and order detail agreement`
    - `@given(st.integers(min_value=1, max_value=29))` (in-stock products) — checkout, then `GET /orders/{id}`; assert all fields match the checkout response and `total == subtotal − discount` and each `line_total == unit_price × quantity`
    - Reset state at start of each example
    - _Requirements: 6.1, 6.13, 12.2_
  - [ ]* 11.13 Write property test for Property 6
    - Tag: `# Feature: test-cases, Property 6: checkout and order detail agreement`
    - Validates: Requirements 6.1, 6.13, 12.2
  - [~] 11.14 Write Property 7 — stock restoration round-trip
    - `# Feature: test-cases, Property 7: stock restoration round-trip`
    - `@given(st.integers(min_value=1, max_value=29))` — record stock before checkout; checkout; cancel; assert stock after cancellation equals stock before checkout
    - Reset state at start of each example
    - _Requirements: 7.4, 7.8, 12.3_
  - [ ]* 11.15 Write property test for Property 7
    - Tag: `# Feature: test-cases, Property 7: stock restoration round-trip`
    - Validates: Requirements 7.4, 7.8, 12.3
  - [~] 11.16 Write Property 8 — order isolation between users
    - `# Feature: test-cases, Property 8: order isolation between users`
    - Place orders as Alice; assert Bob's `GET /orders` contains no order ids belonging to Alice; assert Bob's `GET /orders/{alice_order_id}` and `POST /orders/{alice_order_id}/cancel` return 404
    - _Requirements: 7.1, 7.2_
  - [ ]* 11.17 Write property test for Property 8
    - Tag: `# Feature: test-cases, Property 8: order isolation between users`
    - Validates: Requirements 7.1, 7.2
  - [~] 11.18 Write Property 9 — registration-then-login round-trip
    - `# Feature: test-cases, Property 9: registration-then-login round-trip`
    - `@given(st.from_regex(r"[a-z0-9]+@[a-z]+\.[a-z]+", fullmatch=True), st.text(min_size=1).filter(str.strip), st.text(min_size=8).filter(lambda s: s.strip()))` — register then immediately login; assert 200
    - Reset state at start of each example to avoid duplicate-email collisions
    - _Requirements: 2.4, 12.7_
  - [ ]* 11.19 Write property test for Property 9
    - Tag: `# Feature: test-cases, Property 9: registration-then-login round-trip`
    - Validates: Requirements 2.4, 12.7
  - [~] 11.20 Write Property 10 — user response excludes password data
    - `# Feature: test-cases, Property 10: user response excludes password data`
    - For login, register, and `GET /me` responses: assert `"id"`, `"email"`, `"name"` present; assert no key in the response body text contains the substring `"password"`
    - _Requirements: 2.1, 2.15_
  - [ ]* 11.21 Write property test for Property 10
    - Tag: `# Feature: test-cases, Property 10: user response excludes password data`
    - Validates: Requirements 2.1, 2.15
  - [~] 11.22 Write Property 11 — JSON round-trip fidelity
    - `# Feature: test-cases, Property 11: JSON round-trip fidelity`
    - For `GET /products`, `GET /cart`, and `GET /orders` responses: parse → serialize → parse again; assert resulting object equals first parse
    - _Requirements: 3.16, 12.8_
  - [ ]* 11.23 Write property test for Property 11
    - Tag: `# Feature: test-cases, Property 11: JSON round-trip fidelity`
    - Validates: Requirements 3.16, 12.8

- [~] 12. Checkpoint — run property tests and full API suite, verify all pass
  - Install `hypothesis` if missing (`pip install hypothesis`), then run `pytest tests/test_properties.py tests/test_cases_api.py tests/test_agent.py --tb=short -q`
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Complete browser/UI test cases in `test_cases_ui.py`
  - [~] 13.1 Verify all TC-UI-001 to TC-UI-036 cases are present and passing
    - Cross-check each case against Requirement 10 acceptance criteria 1–6, 8–16, 18
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.8, 10.9, 10.10, 10.11, 10.12, 10.13, 10.14, 10.15, 10.16, 10.18_
  - [~] 13.2 Verify chat assistant hidden test (TC-UI-028)
    - Assert `chat-open` button and `chat-panel` are hidden when `AGENT_ENABLED` is not `"true"` (the live_server fixture starts with `AGENT_ENABLED=false`)
    - _Requirements: 10.19_
  - [~] 13.3 Verify horizontal-scroll test at 375 px (TC-UI-026)
    - At 375 px width: for home, All products, product page, cart, checkout, orders, login, sign-up — assert `scrollWidth − innerWidth ≤ 0`
    - _Requirements: 10.17_
  - [~] 13.4 Verify browser Back/Forward navigation test (TC-UI-025)
    - _Requirements: 10.18_
  - [~] 13.5 Verify discount-percent UI consistency test (TC-UI-006)
    - For product cards showing a discount, assert displayed `discount_percent` equals `round((mrp − price) × 100 / mrp)`
    - _Requirements: 10.7_

- [~] 14. Final checkpoint — run the full test suite
  - Run `pytest tests/ --ignore=tests/test_cases_ui.py --tb=short -q` (API + property + agent) and confirm green
  - Optionally run UI suite: `pytest tests/test_cases_ui.py -v` (requires Playwright + Chromium)
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP; they add depth but are not blockers for the next task
- Each task references specific requirements for traceability
- Checkpoints (tasks 7, 12, 14) are meant to be run as a batch validate step
- `test_properties.py` is the only truly new file; all other work extends existing files
- The `hypothesis` package must be added to `requirements.txt` before property tests can run
- Property tests mutate application state; each test function should call `client.post("/test/reset", headers=RESET)` at the start of `@given`-decorated functions that perform write operations, or use a fresh `TestClient` context per example

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.3", "1.4", "1.5"] },
    { "id": 1, "tasks": ["1.2", "2.1", "2.3", "2.4", "3.1", "3.2", "3.3", "3.4", "4.1", "4.2", "4.3", "5.1", "5.2", "6.1", "6.2", "6.3", "9.1", "9.2", "9.3", "9.4", "9.5", "10.1", "10.2"] },
    { "id": 2, "tasks": ["2.2", "6.4", "6.5", "6.6", "6.7", "8.1", "8.2", "8.3", "8.4", "11.1"] },
    { "id": 3, "tasks": ["11.2", "11.4", "11.6", "11.8", "11.10", "11.12", "11.14", "11.16", "11.18", "11.20", "11.22"] },
    { "id": 4, "tasks": ["11.3", "11.5", "11.7", "11.9", "11.11", "11.13", "11.15", "11.17", "11.19", "11.21", "11.23"] },
    { "id": 5, "tasks": ["13.1", "13.2", "13.3", "13.4", "13.5"] }
  ]
}
```
