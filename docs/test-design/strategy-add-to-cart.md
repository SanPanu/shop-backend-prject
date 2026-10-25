# Practice Shop — Add to Cart Test Strategy

Generated: 2026-10-25
Input: `test-report/scenarios-add-to-cart.md` (39 scenarios, TC-001 to TC-506)

---

## 1. Layer Distribution Summary

| Layer | TC Count | Focus | Approx. Run Time |
|---|---|---|---|
| **Unit** | 4 | `CartAddIn` input model and the `cart_out` line total / subtotal calculation, no HTTP | < 1s total |
| **API / Integration** | 19 | `POST /cart/items` contract, stock limit, quantity merge, auth, cart isolation, concurrency | 10–20s total |
| **Component** | 11 | Add buttons, quantity field errors, message placement, badge count, with mocked API responses | 5–15s total |
| **E2E** | 5 | Add from card and detail page through to the cart page, logged-out add, stock display after reload | 1–2 min total |
| **Total** | **39** | | |

**Pyramid shape**: Unit (4) → API (19) → Component (11) → E2E (5) ✓

> **Note on multi-layer coverage**: TC-105 (line total uses the current price), TC-302 (quantity 0 or negative) and TC-303 (missing or non-integer product ID) are intentionally tested at Unit + API: the unit test proves the rule, the API test proves FastAPI turns it into a 422 and never a 500. The E2E layer confirms only the add-to-cart journeys.

---

## 2. Layer Assignments

### Unit Tests
_Criteria: Pure function, no I/O, no DB. Source: `app/main.py`_

| TC | Title | Function Under Test | File:Line |
|---|---|---|---|
| TC-004 | Quantity defaults to 1 when it is not sent | `CartAddIn(product_id=9).quantity == 1` | `main.py:69` |
| TC-105 | Cart line uses the product's current price | `cart_out(db, user)` with mocked `db.scalars` returning cart items whose `product.price` is 1999 | `main.py:169-171` |
| TC-302 | Quantity 0 or negative returns 422 | `CartAddIn(product_id=5, quantity=0)` and `(…, quantity=-1)` raise `ValidationError` (`ge=1`) | `main.py:69` |
| TC-303 | Missing or non-integer product ID returns 422 | `CartAddIn(quantity=1)`, `CartAddIn(product_id="abc")`, `CartAddIn(product_id=5, quantity=1.5)` raise `ValidationError` | `main.py:67-69` |

**Rationale**: `CartAddIn` is a pydantic model, so its default and limits can be checked by building the model directly, with no app, database or token. `cart_out` only reads `db.scalars(...)` and multiplies `i.product.price * i.quantity`; a mocked session returning plain objects covers the `unit_price`, `line_total` and `subtotal` fields. Testing these through the browser adds login and seed data with no added confidence.

---

### API / Integration Tests
_Criteria: Backend business rule, API contract, or requires real DB state. Auth enforced via bearer token. Source: `add_to_cart`, `_set_quantity`, `cart_out`, `current_user`, `CartAddIn` in `app/main.py`_

#### Happy Path — API contracts
| TC | Title | Endpoint | Route Function |
|---|---|---|---|
| TC-003 | Add a product via API | `POST /cart/items` | `add_to_cart` → `_set_quantity(add=True)` |
| TC-005 | Add several different products | `POST /cart/items` ×3 then `GET /cart` | `add_to_cart`, `get_cart` (`cart_out` orders by `CartItem.id`) |
| TC-006 | Cart is kept after logging out and back in | `POST /cart/items`, `POST /auth/logout`, `POST /auth/login`, `GET /cart` | `get_cart` (rows keyed by `user_id`, not by token) |

#### Business Rules — DB-dependent
| TC | Title | Route Function | Key Code |
|---|---|---|---|
| TC-100 | Adding a product already in the cart increases its quantity | `_set_quantity` | `wanted = quantity + (item.quantity if item and add else 0)` at `main.py:408`; `item.quantity = wanted` at `main.py:414` |
| TC-101 | Cart quantity cannot exceed the product's stock | `_set_quantity` | `wanted > product.stock` → `Only {product.stock} in stock` at `main.py:409-410` |
| TC-102 | Stock limit counts what is already in the cart | `_set_quantity` | same check on `wanted` at `main.py:409`, after the merge at `main.py:408` |
| TC-103 | Adding to the cart does not reduce stock | `_set_quantity` | writes only `CartItem` (`main.py:412` / `main.py:414`); `GET /products/10` still returns `stock: 2` |
| TC-104 | Two users can each add the same last units | `_set_quantity` | stock limit is per request against `product.stock`; nothing is reserved |
| TC-400 | Add exactly all remaining stock (maximum) | `_set_quantity` | `>` not `>=` at `main.py:409`, so `wanted == stock` passes |
| TC-401 | Quantity at the integer limit | `CartAddIn`, `_set_quantity` | `le=MAX_INT` at `main.py:68-69` (`MAX_INT` at `main.py:21`); 2147483647 reaches the stock check → 409 "Only 50 in stock" |
| TC-402 | Product ID 0 and negative product ID | `_set_quantity` | `db.get(Product, product_id)` is `None` → `Product not found` at `main.py:404` |
| TC-403 | Two adds of a new product at the same moment | `_set_quantity` | `except IntegrityError` → `The cart was changed by another request. Please try again` at `main.py:417-419`; `UniqueConstraint("user_id", "product_id")` at `models.py:47` |
| TC-404 | Two adds of a product already in the cart at the same moment | `_set_quantity` | read at `main.py:405`, unlocked write `item.quantity = wanted` at `main.py:414`. Lost update suspected by code reading, not run |

#### Security — Auth Enforcement
| TC | Title | Endpoint | Enforcement Point |
|---|---|---|---|
| TC-200 | Add to cart without a token returns 401 | `POST /cart/items` | `main.py:137-138`: no header → "Missing bearer token" |
| TC-201 | Add to cart with an invalid or logged-out token returns 401 | `POST /auth/logout` then `POST /cart/items` | `main.py:141`: `token is None` → "Invalid token" |
| TC-202 | Adding as one user does not change another user's cart | `POST /cart/items` (alice), `GET /cart` (bob) | `CartItem(user_id=user.id, …)` at `main.py:412`; `cart_out` filters `CartItem.user_id == user.id` at `main.py:164` |
| TC-203 | Authorization header without the "Bearer " prefix is rejected | `POST /cart/items` | `main.py:137`: `not authorization.startswith("Bearer ")` |

#### Negative / Validation
| TC | Title | Validator / Route Function | Validation Rule |
|---|---|---|---|
| TC-300 | Add a product that does not exist returns 404 | `_set_quantity` | `HTTPException(404, "Product not found")` at `main.py:404` |
| TC-301 | Add the out-of-stock product via API returns 409 | `_set_quantity` | `wanted (1) > product.stock (0)` → "Only 0 in stock" at `main.py:410`; product 8 seeded with stock 0 at `seed.py:38` |
| TC-302* | Quantity 0 or negative returns 422 | `CartAddIn` | `ge=1` at `main.py:69` (*primary: Unit; API confirms 422) |
| TC-303* | Missing or non-integer product ID returns 422 | `CartAddIn` | `product_id: int` required at `main.py:68` (*primary: Unit; API confirms 422, never 500) |
| TC-105* | Cart line uses the product's current price | `cart_out` | `"unit_price": i.product.price` at `main.py:169` (*primary: Unit) |

---

### Component Tests
_Criteria: Single view renders correctly for a given mocked API response or stored state. No real backend data needed. Source: product card (`index.html:540`), `showProduct` (`index.html:683`), `showCart` (`index.html:723`), add handler (`index.html:1183-1192`) in `app/static/index.html`_

#### Quantity field — `showProduct` view (`index.html:683`)
| TC | Title | Mocked State | Assertion |
|---|---|---|---|
| TC-304 | Detail page — empty, decimal or zero quantity shows a field error | Logged in; no `POST /cart/items` route needed (assert it is never called) | `error-detail-qty` shows "Enter a quantity" / "Quantity must be a whole number" / "Quantity must be at least 1" (`qtyMessage` at `index.html:1238`); no request sent; no page-level message |
| TC-305 | Detail page — quantity above stock shows the API message under the field | Mock `POST /cart/items` → 409 `{"detail": "Only 2 in stock"}` | `error-detail-qty` = "Only 2 in stock"; "Added to cart." not shown (`return 'handled'` at `index.html:1190`, checked at `index.html:1135`) |
| TC-405 | Very large quantity typed on the detail page | Mock `POST /cart/items` → 422 with FastAPI's `detail` list for `quantity` `le` | Expected: plain message under the field. By code reading (not run), `err.status !== 409` rethrows at `index.html:1190`, `act` shows it with `say` at `index.html:1138`, and `api` builds the raw `loc: msg` text at `index.html:493` — report as a defect if confirmed |
| TC-406 | Field error clears after a valid add | Mock `POST /cart/items` → 200 cart | After 0 then 1: `error-detail-qty` removed (`fieldError(qty, '')` at `index.html:1187`); "Added to cart." shown |
| TC-502 | Detail page quantity starts at 1 | Mock `GET /products/5` with `stock: 50` | `detail-qty` value 1, `min` 1 (`index.html:710`); `detail-stock` "50 in stock" (`index.html:530`) |
| TC-501 | Add buttons are disabled for an out-of-stock product | Mock product with `stock: 0`, `in_stock: false` in list and detail responses | `add-to-cart` disabled (`index.html:540`); `detail-qty` and `detail-add` disabled (`index.html:710-711`); stock text "Out of stock" |

#### Product card add and header badge (`index.html:540`, `refreshNav` at `index.html:505`)
| TC | Title | Mocked State | Assertion |
|---|---|---|---|
| TC-306 | Product card — adding past stock shows the API message at the top of the page | Mock `POST /cart/items` → 409 `{"detail": "Only 2 in stock"}` | Card has no quantity field (`!qty` at `index.html:1190`), so `message` shows "Only 2 in stock"; no field error |
| TC-307 | Add to cart when the server is unreachable | `route.abort()` on `POST /cart/items` | Expected: plain-language error. By code reading (not run), `say(e.message)` at `index.html:1138` shows the browser's raw text such as "Failed to fetch" — report as a defect if confirmed |
| TC-504 | Ended session on add sends the user to login | Token in storage; mock `POST /cart/items` → 401 | URL is `#/login`; message "Your session has ended. Please log in again." (`e.expired` at `index.html:1137`, set at `index.html:490`) |
| TC-106 | Header badge shows total units, not number of lines | Mock `GET /cart` with lines of quantity 3 and 1 | `cart-count` = 4 (`reduce` at `index.html:513`) |

#### Cart page — `showCart` view (`index.html:723`)
| TC | Title | Mocked State | Assertion |
|---|---|---|---|
| TC-506 | Empty cart before any add | Mock `GET /cart` → `{"items": [], "subtotal": 0}` | `cart-empty` shows "Your cart is empty." and "Browse products" to `#/` (`index.html:729`); badge 0 |

---

### E2E Tests
_Criteria: Multi-page user journey, full-stack data flow, cross-session security requiring real browser state. Source: Playwright for Python, fixtures in `tests/conftest.py`_

#### Critical Happy Paths (must have green before shipping)
| TC | Title | Precondition | Journey Scope |
|---|---|---|---|
| TC-001 | Add a product to the cart from a product card | Logged in, empty cart | Login → `#/` → `add-to-cart` on product 5 → assert "Added to cart." + `cart-count` 1 + still on `#/` |
| TC-002 | Add a chosen quantity from the product detail page | Logged in, empty cart | Login → `#/p/5` → `detail-qty` 3 → `detail-add` → `#/cart` → assert `cart-row-5`, ₹1,497, "3 item(s)" |

#### Business Rule Validation (E2E confirms end-to-end rule enforcement)
| TC | Title | What E2E Adds Over API Test |
|---|---|---|
| TC-503 | Shown stock does not change after adding | Confirms the detail page reads stock from the server after a reload; the rule itself is proven by TC-103 (API) |

#### Security / Session (requires real login flow)
| TC | Title | Why Must Be E2E |
|---|---|---|
| TC-500 | Logged-out add redirects to login and returns afterwards | Needs the real login form: `needLogin` stores `returnTo` (`index.html:522`) and the login handler returns to it (`index.html:1341`); also asserts nothing was added |

#### UI State Requiring Real Navigation
| TC | Title | Why Must Be E2E |
|---|---|---|
| TC-505 | Added product appears on the cart page with a link back | Add on one page, read it on `#/cart` (`cart-row-7` at `index.html:743`), follow the name link to `#/p/7` — a real round trip through the backend |

---

## 3. Decision Rationale — Contested Assignments

### TC-304 / TC-305 / TC-306 / TC-405 / TC-406 — Quantity Errors → Component (not E2E)
**Original suggestion**: E2E
**Decision**: Component only

**Rationale**: Where an add-to-cart error appears is decided entirely in the click handler:
```javascript
// index.html:1187-1190
if (qty) { const msg = qtyMessage(qty.value); fieldError(qty, msg); if (msg) { qty.focus(); return; } }
act(async () => {
  try { await api('POST', '/cart/items', { product_id: id, quantity }); }
  catch (err) { if (!qty || err.status !== 409) throw err; fieldError(qty, err.message); return 'handled'; }
```
The branches are: client check fails (no request), 409 on the detail page (under the field), 409 on a card (page message), any other error (page message). Each is reached by mocking one `POST /cart/items` response with `page.route()`. The real 409 rule is already proven at API (TC-101, TC-102); repeating it in a full browser journey only adds login and seed data.

---

### TC-302 / TC-303 / TC-401 — Validation Errors → Unit + API (not E2E)
**Original suggestion**: API
**Decision**: Unit for the model rule, API to confirm 422 — do NOT add E2E coverage

**Rationale**: `CartAddIn` (`main.py:67-69`) rejects bad input before `add_to_cart` runs. In the browser, `qtyMessage` stops 0, decimals and empty input before any request, so an E2E test would never reach the server rule. Product ID cannot be typed by the user at all. A direct `POST /cart/items` returning 422 proves the contract precisely.

---

### TC-100 / TC-101 / TC-102 / TC-403 / TC-404 — Quantity Merge, Stock Limit and Concurrency → API (not E2E)
**Original suggestion**: API
**Decision**: API confirmed — do NOT add E2E coverage

**Rationale**: All of it happens in `_set_quantity` (`main.py:401-420`):
1. `wanted = quantity + item.quantity` — merge with the existing line
2. `wanted > product.stock` → 409 `Only {stock} in stock`
3. `db.add(CartItem(...))` or `item.quantity = wanted`
4. `except IntegrityError` → 409 "The cart was changed by another request. Please try again"

Parallel requests (TC-403, TC-404) cannot be timed reliably with two browser clicks. An API test can send them with a thread pool and then read `GET /cart`.

---

### TC-006 — Cart Kept Between Logins → API (not E2E)
**Original suggestion**: E2E
**Decision**: API

**Rationale**: The rule is that cart rows belong to the user, not to the token or the browser (`main.py:412`, `main.py:164`). Logging in again with a new token and calling `GET /cart` proves it directly. The UI only renders whatever `GET /cart` returns, which TC-505 already covers. Existing case `TC-CART-010` already tests this.

---

### TC-500 — Logged-out Add → E2E (not Component)
**Original suggestion**: E2E
**Decision**: E2E confirmed

**Rationale**: The redirect alone could be a component test, but the scenario also checks the return after a real login (`returnTo` at `index.html:522`, used at `index.html:1341`) and that nothing was added. That needs the real login form and the real `GET /cart`. Existing case `TC-UI-008` covers this journey.

---

## 4. Anti-Patterns to Avoid

These anti-patterns were identified from the suggested layers in the scenario document and must NOT be implemented:

| Anti-Pattern | Affected TCs | Correct Approach |
|---|---|---|
| Testing quantity limits (`2147483648`, 0, -1) by typing in the browser | TC-302, TC-401 | Unit test on `CartAddIn`, plus API `POST /cart/items` → 422 |
| Testing concurrency with two browser clicks | TC-403, TC-404 | API test: parallel `POST /cart/items` calls, then `GET /cart` |
| Placing real orders to reach a "stock 0" state for the disabled button | TC-501 | Component: mock a product with `stock: 0`; or use seeded product 8 (`seed.py:38`) |
| Adding past stock in a full E2E journey to check the message position | TC-305, TC-306 | Component: mock a 409 `{"detail": "Only 2 in stock"}` |
| Testing 401 by tampering with the browser session in E2E | TC-200, TC-201, TC-203 | API test: send `POST /cart/items` with no, invalid or unprefixed `Authorization` header |
| Using a fixed sleep to wait for the badge after "Add to cart" | TC-001, TC-106 | `expect(page.get_by_test_id("cart-count")).to_have_text("1")` |
| No E2E coverage for adding from the detail page | — | TC-002 must have E2E — it is the only path that sends a chosen quantity |

---

## 5. Defense-in-Depth Coverage Map

Critical rules covered at multiple layers for maximum confidence:

| Rule | Unit | API | Component | E2E |
|---|---|---|---|---|
| Line total = current price × quantity; subtotal = sum | TC-105 | TC-003, TC-005, TC-105 | — | TC-002 (implicit) |
| Quantity must be a whole number ≥ 1 | TC-302 | TC-302 | TC-304 | — |
| Cart quantity ≤ stock, counting existing lines | — | TC-101, TC-102, TC-301, TC-400 | TC-305, TC-306 | — |
| Same product merges into one line | — | TC-100, TC-403 | — | — |
| Adding does not reserve stock | — | TC-103, TC-104 | — | TC-503 |
| Out-of-stock product cannot be added | — | TC-301 | TC-501 | — |
| Auth required; carts are separate per user | — | TC-200, TC-201, TC-202, TC-203 | TC-504 | TC-500 |

---

## 6. Implementation Priority Order

Ship in this order — each tier unblocks the next:

**Tier 1 — P0, must pass before any release**
- `TC-001, TC-002, TC-500` (E2E happy paths and logged-out add)
- `TC-003, TC-100, TC-101, TC-102, TC-103, TC-301` (contract, merge, stock limit — API)
- `TC-200, TC-201, TC-202` (security — API)
- `TC-305, TC-501` (stock message under the field, disabled buttons — Component)

**Tier 2 — P1, run on every change**
- `TC-004, TC-302, TC-303` (input model — Unit + API)
- `TC-105` (line price — Unit + API)
- `TC-005, TC-006, TC-104, TC-300, TC-400, TC-403` (contracts, maximum stock, parallel add — API)
- `TC-304, TC-306` (quantity field and card errors — Component)
- `TC-505` (cart page round trip — E2E)

**Tier 3 — P2, run nightly or pre-release**
- `TC-203, TC-401, TC-402, TC-404` (edge cases — API)
- `TC-106, TC-307, TC-405, TC-406, TC-502, TC-504, TC-506` (UI micro-states — Component)
- `TC-503` (stock shown after reload — E2E)

---

## 7. Source File Map for Test Generation

| Layer | Test File Location | Key Source Files |
|---|---|---|
| Unit | `tests/unit/test_cart_unit.py` (folder does not exist yet) | `app/main.py` (`CartAddIn`, `cart_out`) |
| API | `tests/test_cases_api.py` (existing `TC-CART-001` to `TC-CART-011` already cover TC-003, TC-100, TC-102, TC-202, TC-006, TC-300, TC-301, TC-302) | `app/main.py` (`add_to_cart`, `_set_quantity`, `cart_out`, `current_user`, `CartAddIn`); `app/models.py` (`CartItem` unique constraint) |
| Component | `tests/components/test_cart_ui_states.py` (folder does not exist yet) | `app/static/index.html` (product card, `showProduct`, `showCart`, add handler, `qtyMessage`, `fieldError`, `act`, `api`, `refreshNav`) |
| E2E | `tests/test_cases_ui.py` (existing `TC-UI-008` covers TC-500; `TC-UI-017` overlaps TC-106) | Full stack; use `alice@example.com` / `bob@example.com` |
