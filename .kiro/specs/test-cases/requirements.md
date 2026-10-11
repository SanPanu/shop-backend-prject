# Requirements Document

## Introduction

This document specifies the requirements for a comprehensive test suite for the Shop-Backend application — a FastAPI-based online shop with SQLite persistence, a static HTML/JS frontend, and an optional AI chat agent.

The test suite covers six functional areas (Authentication, Products, Cart, Coupons, Checkout, Orders), two cross-cutting areas (System/Reset, Security), and two additional areas (UI/Browser, Chat Agent). Each requirement describes what must be verified and states the acceptance criteria in EARS pattern form.

The test suite extends and formalises the test coverage already begun in `tests/test_shop.py`, `tests/test_cases_api.py`, `tests/test_cases_ui.py`, and `tests/test_agent.py`.

---

## Glossary

- **System**: The Shop-Backend FastAPI application.
- **Client**: Any HTTP client (test runner, browser, or curl) that sends requests to the System.
- **Authenticated_Client**: A Client that includes a valid `Authorization: Bearer <token>` header.
- **Seed_State**: The known starting state produced by `POST /test/reset`: 30 products, 2 users (Alice, Bob), 4 coupons, empty carts, no orders.
- **Test_Runner**: The pytest process that executes the test suite.
- **Live_Server**: A real uvicorn process started on a free port for concurrency tests.
- **Browser**: A Playwright-controlled Chromium instance for UI tests.
- **Alice**: Seed user with email `alice@example.com`, password `Password123`, id 1.
- **Bob**: Seed user with email `bob@example.com`, password `Password123`, id 2.
- **CARD**: Valid mock card number `4111111111111111`.
- **DECLINED_CARD**: Declined mock card number `4000000000000002`.
- **SHIP**: Valid shipping object (Asha Rao, 12 MG Road, Bengaluru, Karnataka, 560001, India).
- **RESET_KEY**: The value `practice-reset` sent in the `X-Reset-Key` header to authorise a data reset.
- **Token**: An opaque bearer string returned by login or register and stored in the `tokens` table.
- **Coupon**: A discount code stored in the `coupons` table (WELCOME10 10%, FLAT200 flat ₹200 min ₹1500, EXPIRED50 expired, DISABLED20 disabled).
- **Product_Id**: The integer primary key of a row in the `products` table (1–30 in seed data).
- **Order_Id**: The integer primary key of a row in the `orders` table.
- **Stock**: The integer quantity remaining for a product; the System rejects cart additions that would exceed it.
- **Subtotal**: Sum of `unit_price × quantity` for all cart lines (no discounts).
- **Discount**: The amount deducted by a coupon (whole rupees, rounded down for percent coupons).
- **Total**: `Subtotal − Discount`.
- **Property_Test**: A test that generates many random inputs and asserts an invariant holds for all of them.
- **Integration_Test**: A test that exercises one realistic scenario end-to-end with a fixed set of inputs.

---

## Requirements

### Requirement 1: Test Infrastructure Setup

**User Story:** As a test engineer, I want a reliable, isolated test environment, so that every test run starts from a clean, deterministic state.

#### Acceptance Criteria

1. THE Test_Runner SHALL use an in-memory or temporary SQLite database that is separate from `shop.db`.
2. WHEN `POST /test/reset` is called with the correct RESET_KEY, THE System SHALL restore the Seed_State in full within 5 seconds, including all products, users, coupons, tokens, carts, and orders defined in the seed data, and SHALL return a response indicating success.
3. THE Test_Runner SHALL reset to Seed_State before every individual API test that depends on database content, and SHALL treat a reset that does not complete within 5 seconds as a failure and abort the test.
4. WHEN the Live_Server fixture is requested, THE Test_Runner SHALL start a uvicorn process on a free port and SHALL wait up to 30 seconds for `/health` to return HTTP 200 before yielding; IF `/health` does not return HTTP 200 within 30 seconds, THEN THE Test_Runner SHALL abort the fixture setup and mark all dependent tests as errors.
5. WHEN the Live_Server fixture is torn down, THE Test_Runner SHALL terminate the uvicorn process within 10 seconds and confirm the port is no longer bound before continuing teardown.
6. WHERE Playwright is installed, THE Test_Runner SHALL launch Chromium against the Live_Server base URL; IF Playwright or its browser binary is not installed, THEN THE Test_Runner SHALL skip all browser tests and record each skipped test with a `skipped` status and reason indicating missing Playwright installation, without marking the session as failed.
7. THE Test_Runner SHALL write test results to `test-report/test_cases.csv` and `test-report/results.json` after every session, and IF either file cannot be written, THEN THE Test_Runner SHALL report a file write error without suppressing it.
8. WHEN a test is skipped, THE Test_Runner SHALL preserve any previously recorded result for that test ID in the merged report rather than overwriting it with a skipped status; IF no previously recorded result exists for that test ID, THEN THE Test_Runner SHALL record the skipped status.

---

### Requirement 2: Authentication Tests

**User Story:** As a test engineer, I want automated tests for every authentication endpoint, so that regressions in login, registration, token lifecycle, and input validation are caught immediately.

#### Acceptance Criteria

1. WHEN `POST /auth/login` is called with valid credentials, THE System SHALL return 200, a token between 1 and 2048 characters, and the user object `{id, email, name}` with no password field present anywhere in the response body.
2. WHEN `POST /auth/login` is called with a wrong password for a known email, THE System SHALL return 401 with the same response body structure and error message as when called with an unknown email.
3. WHEN `POST /auth/login` is called with the email in a different letter case, THE System SHALL return 200 and the same user object that would be returned with the exact-case email.
4. WHEN `POST /auth/register` is called with a new email, name (1–100 non-whitespace characters), and password (at least 8 non-whitespace characters), THE System SHALL return 201 and a token between 1 and 2048 characters that is immediately accepted by `GET /me`.
5. WHEN `POST /auth/register` is called with an email that differs only in letter case from an existing user's email, THE System SHALL return 409 with detail `"Email already registered"`.
6. WHEN `POST /auth/register` is called with a malformed email (no `@`, no domain, double dot, leading dot in domain, underscore in domain), THE System SHALL return 422 with a non-empty validation error detail.
7. WHEN `POST /auth/register` is called with a password shorter than 8 characters, THE System SHALL return 422 with a non-empty validation error detail; WHEN the password is exactly 8 non-whitespace characters, THE System SHALL return 201.
8. WHEN `POST /auth/register` is called with a name consisting only of whitespace, THE System SHALL return 422 with a non-empty validation error detail.
9. WHEN `POST /auth/register` is called with a password consisting only of whitespace of length >= 8, THE System SHALL return 422 with a non-empty validation error detail.
10. WHEN `POST /auth/register` is called with a name exceeding 100 characters, THE System SHALL return 422 with a non-empty validation error detail; WHEN the name is exactly 100 non-whitespace characters, THE System SHALL return 201.
11. IF a request to `GET /me` is sent without an Authorization header, THEN THE System SHALL return 401; IF it is sent with a malformed Authorization header (not `Bearer <token>`), THEN THE System SHALL return 401; IF it is sent with an unknown token, THEN THE System SHALL return 401. The same rule applies to `GET /cart`, `GET /orders`, and `POST /checkout`.
12. WHEN `POST /auth/logout` is called with a valid token, THE System SHALL return 200 or 204 and within 1 second the same token SHALL be rejected with 401 by all protected endpoints.
13. WHEN `POST /auth/logout` is called a second time with an already-invalidated token, THE System SHALL return 401 with a non-empty validation error detail.
14. WHEN one session is logged out, THE System SHALL leave all other sessions for the same user active such that `GET /me` called with any remaining token returns 200.
15. THE System SHALL ensure that for all valid user objects returned, the response contains `id`, `email`, and `name` and does not contain any field whose name contains the substring `"password"`.

---

### Requirement 3: Product Catalogue Tests

**User Story:** As a test engineer, I want automated tests for the product catalogue endpoints, so that search, filtering, sorting, and data integrity are always verified.

#### Acceptance Criteria

1. WHEN `GET /products` is called with no filters, THE System SHALL return all 30 seed products, each containing fields `id`, `name`, `category`, `specs`, `description`, `price`, `mrp`, `discount_percent`, `rating`, `reviews`, `image`, `stock`, and `in_stock`.
2. THE System SHALL ensure that for all products returned by `GET /products`, `price` is greater than 0, `price` is less than or equal to `mrp`, `stock` is greater than or equal to 0, `rating` is between 0 and 5 inclusive, and `in_stock` equals `stock > 0`.
3. THE System SHALL ensure that for all products returned by `GET /products`, `discount_percent` equals `round((mrp − price) × 100 / mrp)`.
4. WHEN `GET /products` is called with a `q` parameter containing one or more words, THE System SHALL return only products where each word in the query appears as a case-insensitive substring in at least one of `name`, `category`, or `specs`; WHEN `q` is empty or contains only whitespace, THE System SHALL return all 30 seed products.
5. WHEN `GET /products` is called with `q` containing `%` or `_`, THE System SHALL treat those characters as literals, not as SQL wildcards.
6. WHEN `GET /products` is called with `q` containing SQL injection payloads, THE System SHALL return 200 with an empty list and leave all 30 products intact in the database.
7. WHEN `GET /products` is called with a `category` filter, THE System SHALL return only products in that category; WHEN the category does not exist, THE System SHALL return an empty list.
8. WHEN `GET /products` is called with `min_price` and/or `max_price`, THE System SHALL apply inclusive bounds; WHEN `min_price` exceeds `max_price`, THE System SHALL return an empty list.
9. WHEN `GET /products` is called with `sort=price_asc`, THE System SHALL return products ordered by ascending price with ties broken by ascending `id`; `sort=price_desc` descending price (ties by ascending `id`); `sort=name` alphabetically by name (ties by ascending `id`); `sort=rating` descending rating (ties by ascending `id`); `sort=discount` descending discount percentage (ties by ascending `id`).
10. WHEN `GET /products` is called with an unrecognised `sort` value, a negative `min_price`, a non-integer `max_price`, `limit=0`, `limit=101`, or `in_stock=maybe`, THE System SHALL return 422.
11. WHEN `GET /products/{product_id}` is called for an existing product, THE System SHALL return the same object that appears in `GET /products` for that product.
12. WHEN `GET /products/{product_id}` is called with a non-existent id or id 0, THE System SHALL return 404; WHEN called with a non-integer id, THE System SHALL return 422.
13. WHEN `GET /categories` is called, THE System SHALL return all 10 seed categories each with a `count` equal to the number of products in that category, and the sum of all counts SHALL equal 30.
14. WHEN `GET /products/suggest` is called with `q` shorter than 2 characters or only whitespace, THE System SHALL return empty `categories`, `products`, and `total=0`.
15. WHEN `GET /products/suggest` is called with `q` of at least 2 characters, THE System SHALL return up to 5 matching products and up to 5 matching categories; products whose name starts with the query word SHALL appear at a lower index in the results than products where the query word only appears internally.
16. THE System SHALL ensure that for all product search response objects, serializing the response to JSON and parsing it again produces an object with equal field values to the original (round-trip property).

---

### Requirement 4: Cart Tests

**User Story:** As a test engineer, I want automated tests for cart operations, so that per-user isolation, stock enforcement, and quantity arithmetic are verified.

#### Acceptance Criteria

1. WHEN `POST /cart/items` is called with a valid `product_id` and a quantity between 1 and available stock (inclusive), THE System SHALL add the item and return the updated cart with correct `unit_price`, `quantity`, `line_total` (equal to `unit_price × quantity`), and `subtotal`.
2. WHEN `POST /cart/items` is called for a product already in the cart with a quantity between 1 and (available stock minus current cart quantity) inclusive, THE System SHALL increase the quantity by the requested amount and return one line for that product.
3. WHEN `POST /cart/items` is called for a product whose stock is 0, THE System SHALL return 409 and leave the cart items list and subtotal unchanged.
4. WHEN `POST /cart/items` is called and the sum of the quantity already in the cart and the requested quantity would exceed the product's stock, THE System SHALL return 409 and leave the cart items list and subtotal unchanged.
5. WHEN `POST /cart/items` is called with `quantity=0`, a negative quantity, a non-integer quantity, or a missing quantity, THE System SHALL return 422.
6. WHEN `POST /cart/items` is called with an unknown `product_id`, THE System SHALL return 404; WHEN called with a non-integer `product_id`, THE System SHALL return 422.
7. WHEN `PUT /cart/items/{product_id}` is called with a quantity between 1 and available stock (inclusive) for a product in the cart, THE System SHALL set the quantity to the requested value and return the updated subtotal.
8. WHEN `PUT /cart/items/{product_id}` is called with `quantity=0`, a negative quantity, or a non-integer quantity, THE System SHALL return 422.
9. WHEN `PUT /cart/items/{product_id}` is called with a quantity that would exceed the product's stock, THE System SHALL return 409 and leave the cart items list and subtotal unchanged.
10. WHEN `PUT /cart/items/{product_id}` is called for a product not in the cart, THE System SHALL return 404.
11. WHEN `DELETE /cart/items/{product_id}` is called for a product in the cart, THE System SHALL remove that line and return the updated cart.
12. WHEN `DELETE /cart/items/{product_id}` is called for a product not in the cart, THE System SHALL return 404.
13. WHEN `DELETE /cart` is called, THE System SHALL remove all items and return an empty cart with `subtotal=0`.
14. WHILE two users are both logged in, THE System SHALL keep their carts independent: changes to one user's cart SHALL NOT affect the other user's cart.
15. WHEN `GET /cart` is called with a valid token, THE System SHALL return only the cart belonging to the owner of that token.
16. THE System SHALL ensure that for all cart states, `subtotal` equals the sum of `unit_price × quantity` for every line in `items`, and each `line_total` equals `unit_price × quantity` for that line.

---

### Requirement 5: Coupon Tests

**User Story:** As a test engineer, I want automated tests for coupon validation, so that percentage and flat discount calculations, expiry, disabled state, and minimum order enforcement are verified.

#### Acceptance Criteria

1. WHEN `POST /coupons/validate` is called with a valid percentage coupon, THE System SHALL return a response containing a `discount` equal to `floor(subtotal × rate / 100)` and a `total` equal to `subtotal − discount`.
2. WHEN `POST /coupons/validate` is called with a valid flat coupon, THE System SHALL return a response containing a `discount` equal to `min(coupon_value, subtotal)` and a `total` equal to `subtotal − discount`.
3. WHEN `POST /coupons/validate` is called with a coupon code in lowercase or with leading or trailing spaces, THE System SHALL accept it and return the canonical uppercase trimmed code in the response.
4. WHEN `POST /coupons/validate` is called with an expired coupon, THE System SHALL return HTTP 400 with an error message indicating the coupon has expired.
5. WHEN `POST /coupons/validate` is called with a disabled coupon, THE System SHALL return HTTP 400 with an error message indicating the coupon is not active.
6. WHEN `POST /coupons/validate` is called with an unknown coupon code, THE System SHALL return HTTP 400 with an error message indicating the coupon was not found.
7. WHEN `POST /coupons/validate` is called for a flat coupon and the cart subtotal is below the coupon's minimum order value, THE System SHALL return HTTP 400 with an error message that includes the minimum order amount.
8. WHEN `POST /coupons/validate` is called with a cart containing zero items or a subtotal of 0, THE System SHALL return HTTP 400 with an error message indicating the cart is empty or has no value.
9. THE System SHALL ensure that for all valid coupon responses, `discount` is a non-negative integer, `total` equals `subtotal − discount`, and `discount` does not exceed the subtotal.
10. WHEN `POST /coupons/validate` is called, THE System SHALL accept a request body containing a coupon code (1–50 characters) and a subtotal amount (0.01 to 999,999,999.99); IF either field is absent or outside these bounds, THEN THE System SHALL return HTTP 400 with an error message indicating which field is invalid.

---

### Requirement 6: Checkout Tests

**User Story:** As a test engineer, I want automated tests for the checkout flow, so that order creation, stock deduction, coupon application, payment validation, shipping validation, and atomicity under concurrent load are all verified.

#### Acceptance Criteria

1. WHEN `POST /checkout` is called with a valid card, valid shipping, and a non-empty cart, THE System SHALL return 201 with a paid order whose `subtotal`, `discount`, `total`, `items`, and `shipping` fields match the cart state and applied coupon at the time of the call.
2. WHEN a checkout succeeds, THE System SHALL clear the cart (so `GET /cart` returns an empty cart) and reduce the stock of each purchased product by the purchased quantity.
3. WHEN `POST /checkout` is called with an empty cart, THE System SHALL return 400 and create no order, leaving the order list and all stock levels unchanged.
4. WHEN `POST /checkout` is called with the DECLINED_CARD, THE System SHALL return 402 and leave the cart items, all stock levels, and the order list unchanged.
5. WHEN `POST /checkout` is called with a card number that is not exactly 16 ASCII digits, THE System SHALL return 422 and create no order, leaving the cart items, all stock levels, and the order list unchanged.
6. WHEN `POST /checkout` is called with an expired, disabled, or unknown coupon, THE System SHALL return 400 and leave the cart items, all stock levels, and the order list unchanged.
7. WHEN `POST /checkout` is called with a coupon whose minimum order is no longer met because the cart was modified after validation, THE System SHALL return 400 and create no order, leaving the cart items, all stock levels, and the order list unchanged.
8. WHEN `POST /checkout` is called without a shipping object, THE System SHALL return 422.
9. WHEN `POST /checkout` is called with an invalid shipping field (bad email, blank name, blank address, unknown state, malformed PIN, unsupported country, field exceeding max length), THE System SHALL return 422 and create no order.
10. WHEN two concurrent checkouts compete for the last unit of a product, THE System SHALL allow exactly one to succeed with 201 and return 409 to the other, and the product's stock SHALL NOT go below 0.
11. WHEN multiple concurrent checkout requests are sent for the same cart, THE System SHALL create exactly one order and return a non-2xx status to all others, and the total stock reduction across all responses SHALL equal the quantity in one order.
12. IF a checkout fails for any reason after partial stock has been reserved internally, THEN THE System SHALL roll back all stock changes so that no stock level is permanently altered.
13. THE System SHALL ensure that for all successful checkouts, `total` equals `subtotal − discount` and each `line_total` in the order items equals `unit_price × quantity`.

---

### Requirement 7: Order Tests

**User Story:** As a test engineer, I want automated tests for order retrieval and cancellation, so that listing, isolation, detail accuracy, and concurrent cancel protection are verified.

#### Acceptance Criteria

1. WHEN `GET /orders` is called by an authenticated user, THE System SHALL return only that user's orders sorted by `id` descending, with no orders belonging to other users included.
2. WHEN `GET /orders/{order_id}` is called by a user who did not place that order, THE System SHALL return 404 and leave the order status unchanged.
3. WHEN `GET /orders/{order_id}` is called by the order owner, THE System SHALL return the order with `items`, `shipping`, `created_at`, `subtotal`, `discount`, and `total` values equal to those submitted at checkout and confirmed in the `POST /checkout` response.
4. WHEN `POST /orders/{order_id}/cancel` is called on a paid order by its owner, THE System SHALL return 200, change the order status to `"cancelled"`, and restore the stock of each item by the purchased quantity.
5. WHEN `POST /orders/{order_id}/cancel` is called on an already-cancelled order, THE System SHALL return 409 and NOT increase any stock level again.
6. WHEN multiple concurrent cancel requests are sent for the same paid order, THE System SHALL allow exactly one to succeed with 200, reject the rest with 409, and restore the stock of each item by the purchased quantity exactly once.
7. WHEN `GET /orders/{order_id}` or `POST /orders/{order_id}/cancel` is called with an unknown id, THE System SHALL return 404; WHEN called with a non-integer id, THE System SHALL return 422.
8. THE System SHALL ensure that for all cancelled orders whose stock has been restored, the product's stock level after cancellation equals the stock level recorded immediately before the checkout that created the order.

---

### Requirement 8: System and Reset Tests

**User Story:** As a test engineer, I want automated tests for the system health and reset endpoints, so that environment integrity is verified before and after test runs.

#### Acceptance Criteria

1. WHEN `GET /health` is called, THE System SHALL return 200 with body `{"status": "ok"}`.
2. WHEN `POST /test/reset` is called without the `X-Reset-Key` header, with a wrong value, or with an empty string, THE System SHALL return 403 and leave all products, users, coupons, tokens, carts, and orders unchanged.
3. WHEN `POST /test/reset` is called with the correct RESET_KEY, THE System SHALL return 200 with `{"status": "reset"}` and restore the Seed_State: 30 products at seed stock levels, 2 seed users, 4 coupons, no extra users, empty carts, no orders, no tokens.
4. WHEN `GET /` is called, THE System SHALL return 200 with HTML containing `"Practice Shop"`.
5. WHEN any endpoint returns a 4xx or 5xx error, THE System SHALL return a JSON body containing a `"detail"` field.

---

### Requirement 9: Security Tests

**User Story:** As a test engineer, I want automated tests for common security properties, so that authorisation boundaries, injection safety, and integer overflow protection are all verified.

#### Acceptance Criteria

1. WHEN a user attempts to access another user's cart items via `PUT /cart/items/{product_id}` or `DELETE /cart/items/{product_id}` using known product ids, THE System SHALL return 404; a subsequent `GET /cart` by the original user SHALL show the cart unchanged.
2. WHEN a user attempts to read another user's order via `GET /orders/{order_id}` or cancel it via `POST /orders/{order_id}/cancel` using a known order id, THE System SHALL return 404; a subsequent `GET /orders/{order_id}` by the original user SHALL show the order status unchanged.
3. WHEN a username or product name containing HTML or script tags is stored and then retrieved, THE System SHALL return the text unchanged as a JSON string, not as rendered HTML.
4. WHEN any numeric path or query parameter is given a value exceeding 2^31−1, THE System SHALL return 4xx (not 5xx) for every affected endpoint.
5. WHEN `GET /products` is called with SQL injection strings in the `q` query parameter, THE System SHALL return 200 and a response that contains either an empty list or valid matching products, and a subsequent `GET /products` with no filters SHALL return all 30 seed products unchanged; WHEN `POST /cart/items` is called with SQL injection strings in body fields, THE System SHALL return 422.
6. WHEN `POST /test/reset` is called by an unauthenticated client with the correct key, THE System SHALL apply the reset.

---

### Requirement 10: Browser / UI Tests

**User Story:** As a test engineer, I want automated Playwright tests for the key user journeys in the frontend, so that visual and interaction regressions in the SPA are caught before release.

#### Acceptance Criteria

1. WHEN the Browser opens the home page, THE System SHALL display 4 banners, 3 product strips with 8 products each, and 11 category tabs with "For You" active.
2. WHEN a category tab is clicked, THE System SHALL filter the product list to show only products in that category and mark only that tab as active.
3. WHEN a search query containing at least one non-whitespace character is entered in the header and submitted, THE System SHALL display only products matching the query.
4. WHEN a search query is submitted that matches no products, THE System SHALL show a no-results message and display no product cards.
5. WHEN a search query consisting only of spaces is submitted, THE System SHALL show all 30 products.
6. WHEN the filter panel is used to set category, max price, and sort order, THE System SHALL encode the filters in the URL and restore them on page reload; WHEN Clear is clicked, THE System SHALL show all 30 products.
7. WHEN a product card shows a discount, the displayed `discount_percent` and the value derived from `round((mrp − price) × 100 / mrp)` SHALL agree.
8. WHEN the Browser navigates to an out-of-stock product page, THE System SHALL disable the Add to Cart button and the quantity input.
9. WHEN an unauthenticated user clicks Add to Cart, THE System SHALL redirect to the login page with the message `"Please log in first."` and return to the product page after successful login.
10. WHEN the user logs in with wrong credentials, THE System SHALL show `"Wrong email or password"` under the password field without navigating away from the login page.
11. WHEN the user logs out, THE System SHALL invalidate the session token on the server so that a subsequent `GET /me` call with that token returns 401.
12. WHEN the cart badge is visible, THE System SHALL update its count immediately after each add-to-cart action.
13. WHEN the cart quantity for a line is set to a value exceeding the product's stock, THE System SHALL show an inline error message and revert the displayed quantity to the last valid value.
14. WHEN a coupon code is applied successfully, THE System SHALL show the discount line and update the total; WHEN the coupon is removed, THE System SHALL restore the original total.
15. WHEN the order is placed successfully, THE System SHALL navigate to the order detail page showing the order id, status `"paid"`, and a `"Order placed."` message, and the cart badge SHALL show 0.
16. WHEN an order is cancelled from the UI, THE System SHALL change the displayed status to `"cancelled"`, hide the Cancel button, and display the restored product stock on the product detail page.
17. WHEN any page is viewed at a 375 px viewport width, THE System SHALL NOT scroll horizontally (no page is wider than the screen).
18. WHEN the browser Back and Forward buttons are used, THE System SHALL navigate to the correct page.
19. WHERE the AGENT_ENABLED environment variable is not set to `"true"`, THE System SHALL hide the chat button and chat panel on all pages.

---

### Requirement 11: Chat Agent Tests

**User Story:** As a test engineer, I want automated tests for the chat agent API, so that tool dispatch, error propagation, conversation state, step-limit enforcement, and provider format compatibility are all verified.

#### Acceptance Criteria

1. WHEN `GET /agent/status` is called with no AI provider configured, THE System SHALL return `{"enabled": false, "configured": false}`.
2. WHEN `POST /agent/chat` is called without authentication, THE System SHALL return 401.
3. WHEN `POST /agent/chat` is called and no AI provider is configured, THE System SHALL return 503 with a message referencing the required environment variables.
4. WHEN the agent model calls a tool successfully, THE System SHALL execute the corresponding shop function, record the action in `agent_actions`, and pass the result back to the model in the next turn.
5. WHEN a tool call returns an error (out-of-stock, unknown id, not a real tool name), THE System SHALL record `is_error=true` in `agent_actions` and pass the error result to the model without crashing.
6. WHEN `POST /agent/chat` is called a second time with the same `conversation_id`, THE System SHALL continue the conversation with the full prior message history.
7. WHEN `POST /agent/chat` is called with a `conversation_id` belonging to a different user, THE System SHALL return 404.
8. WHEN the model keeps requesting tool calls beyond the configured MAX_STEPS (where MAX_STEPS >= 1) per turn, THE System SHALL stop and return a message containing `"allowed number of steps"`.
9. WHEN `GET /agent/actions` is called, THE System SHALL return only the actions belonging to the requesting user.
10. WHEN the agent's `cancel_order` tool is called for an order owned by a different user, THE System SHALL record `is_error=true` in `agent_actions` and leave the order status as `"paid"`.
11. WHEN the Gemini provider is configured, THE System SHALL send requests in OpenAI-compatible format to the Gemini endpoint, preserve the `extra_content` value on tool calls without modification, and convert the response back to internal format.
12. WHEN the Anthropic provider is configured, THE System SHALL send requests in Anthropic native format with the API key in `x-api-key` and the system prompt as a top-level field.
13. WHEN the model returns a 429, THE System SHALL return 503 with a message indicating a rate limit; WHEN the model returns a 404, THE System SHALL return 503 with a message indicating the model was not found; WHEN the model returns any other HTTP error, THE System SHALL return 503 with a plain-language message describing the failure.

---

### Requirement 12: Data Integrity and Round-Trip Properties

**User Story:** As a test engineer, I want property-based tests for the most critical invariants, so that edge cases involving arbitrary inputs are discovered automatically.

#### Acceptance Criteria

1. THE System SHALL ensure that for all valid product ids, `GET /products/{id}` returns an object whose field values are equal to those of the corresponding entry in `GET /products` when both responses are parsed as Python objects.
2. THE System SHALL ensure that for all completed orders, the order object returned by `GET /orders/{id}` has field values equal to those of the order object returned in the `POST /checkout` response body when both are parsed as Python objects.
3. THE System SHALL ensure that for all successful checkouts followed by a cancellation of the same order, the product's stock level after cancellation equals the stock level recorded immediately before the checkout.
4. THE System SHALL ensure that for all cart states with at least one item, the `subtotal` returned by `POST /cart/items`, `PUT /cart/items/{product_id}`, `DELETE /cart/items/{product_id}`, and `GET /cart` equals the sum of `unit_price × quantity` for all items in the cart at that moment.
5. THE System SHALL ensure that for all coupon validation responses, `subtotal − discount` equals `total`.
6. WHEN a product's `in_stock` field is read, THE System SHALL return `true` if and only if `stock > 0`.
7. THE System SHALL ensure that for all registered users, logging in immediately after registration with the same credentials returns 200.
8. THE System SHALL ensure that for all API JSON responses, parsing the response body and re-serializing to JSON and parsing again produces a Python object with field values equal to those of the first parse.
