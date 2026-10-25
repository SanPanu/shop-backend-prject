---
name: test-strategy
description: Assign Practice Shop test scenarios to the best test layer (Unit, API, Component, E2E). Use when asked for a test strategy, test pyramid or layer assignment, for example "/test-strategy order management". Output follows the format of the Order Management example in this file.
---

When asked for a test strategy, read the scenario document for the requested area (created by `create-scenarios`),
`CLAUDE.md`, `app/main.py` and `app/static/index.html`, then write a document in exactly the format below: same
header, same seven sections, same table columns. Never invent a function, line number or message; quote what the
code does and re-check every `File:Line` against the current files. Save it as `docs/test-design/strategy-<area>.md`.

# Practice Shop — Order Management Test Strategy

Generated: 2026-10-11
Input: `.claude/skills/create-scenarios/SKILL.md` (53 scenarios, TC-001 to TC-510)

---

## 1. Layer Distribution Summary

| Layer | TC Count | Focus | Approx. Run Time |
|---|---|---|---|
| **Unit** | 4 | Pure functions with no I/O (`compute_discount`, `order_out`, line total calc) | < 1s total |
| **API / Integration** | 27 | Backend contract, auth enforcement, business rule execution, DB state | 10–30s total |
| **Component** | 9 | Client-side UI states, conditional rendering, mocked API responses | 5–15s total |
| **E2E** | 13 | Critical user journeys, multi-page flows, cross-session security | 2–5 min total |
| **Total** | **53** | | |

**Pyramid shape**: Unit (4) → API (27) → Component (9) → E2E (13) ✓

> **Note on multi-layer coverage**: TC-102 (order total and discount) and TC-105 (line total calculation) are intentionally tested at Unit + API for defense-in-depth. The E2E layer confirms only the critical happy path end-to-end.

---

## 2. Layer Assignments

### Unit Tests
_Criteria: Pure function, no I/O, no DB. Source: `app/main.py`_

| TC | Title | Function Under Test | File:Line |
|---|---|---|---|
| TC-102 | Order total equals subtotal minus discount | `compute_discount(db, code, subtotal)` with mocked `db.get` | `main.py:189` |
| TC-103 | Flat coupon — order at or above the minimum gets 200 off | `compute_discount(db, 'FLAT200', subtotal)` with mocked `db.get` | `main.py:190` |
| TC-105 | Line total is calculated as unit price × quantity | inline expression `i.unit_price * i.quantity` in `order_out(o)` | `main.py:209` |
| TC-404 | Flat coupon boundary — subtotal exactly 1500 IS accepted | `compute_discount(db, 'FLAT200', 1500)` and `(…, 1499)` | `main.py:186` |

**Rationale**: `compute_discount()` and `order_out()` are pure/near-pure functions requiring only a mocked `db.get` (a coupon object) or a plain order object. Testing them at API or E2E adds overhead with no added confidence. The line total formula is a one-liner with no branching — unit is the correct and only layer needed.

---

### API / Integration Tests
_Criteria: Backend business rule, API contract, or requires real DB state. Auth enforced via bearer token. Source: `checkout`, `cancel_order`, `_own_order`, `CheckoutIn` in `app/main.py`_

#### Happy Path — API contracts
| TC | Title | Endpoint | Route Function |
|---|---|---|---|
| TC-007 | Lookup order by ID | `GET /orders/{order_id}` | `get_order` |
| TC-106 | Orders list is sorted newest first | `GET /orders` | `list_orders` |
| TC-108 | Checkout empties the cart | `POST /checkout` then `GET /cart` | `checkout` |

#### Business Rules — DB-dependent
| TC | Title | Route Function | Key Code |
|---|---|---|---|
| TC-100 | Stock reduces at checkout by the ordered quantity | `checkout` | guarded `update(Product)` with `Product.stock >= i.quantity` at `main.py:488` |
| TC-101 | Cancelling an order restores stock for every item | `cancel_order` | `Product.stock + i.quantity` at `main.py:542` |
| TC-107 / TC-400 | An order can be cancelled only once — also with two requests at the same moment | `cancel_order` | guarded `update(Order)` where `status == "paid"` at `main.py:537` |
| TC-401 | Two checkout requests at the same moment — one cart becomes one order | `checkout` | cart claim `delete(CartItem)` + `rowcount` check at `main.py:481` |
| TC-104 | Flat coupon — order below the minimum is NOT accepted | `checkout` | `compute_discount` raises at `main.py:187`, called at `main.py:475` before any write |
| TC-403 | Order for all remaining stock (maximum) | `checkout`, `_set_quantity` | `Only {product.stock} in stock` at `main.py:410` |
| TC-406 | Cancel when only one order exists — record is kept | `cancel_order` | `update(Order)` (never a delete) at `main.py:537` |
| TC-407 | Coupon code typed in lower case with spaces | `checkout` | `code.strip().upper()` at `main.py:179` and `main.py:502` |
| TC-408 | Order placed time on MySQL — checkout response versus later reads | `order_out` | `o.created_at.isoformat()` at `main.py:201`; column `created_at` in `app/models.py`. Known open defect; reproduces only on MySQL, not on the SQLite test database |

#### Security — Auth Enforcement
| TC | Title | Endpoint | Enforcement Point |
|---|---|---|---|
| TC-201 | Cross-user GET order returns 404 | `GET /orders/{order_id}` | `main.py:517`: `order.user_id != user.id` |
| TC-202 | Cross-user cancel order returns 404 | `POST /orders/{order_id}/cancel` | `main.py:535`: `_own_order(db, user, order_id)` |
| TC-206 | Token is rejected after logout | `POST /auth/logout` then `GET /orders` | `main.py:140`: `token is None` → "Invalid token" |
| TC-203 | Unauthenticated GET /orders returns 401 | `GET /orders` | `current_user` dependency (no token) at `main.py:137` |
| TC-204 | Unauthenticated GET /orders/:id returns 401 | `GET /orders/{order_id}` | `current_user` dependency |
| TC-205 | Unauthenticated POST /orders/:id/cancel returns 401 | `POST /orders/{order_id}/cancel` | `current_user` dependency |

#### Negative / Validation
| TC | Title | Validator / Route Function | Validation Rule |
|---|---|---|---|
| TC-301 | GET non-existent order returns 404 | `_own_order` | `HTTPException(404, "Order not found")` at `main.py:518` |
| TC-302 | Checkout with insufficient stock returns 409 | `checkout` | `Not enough stock for {name}` at `main.py:495` |
| TC-303 | Checkout with an empty cart returns 400 | `checkout` | `Cart is empty` at `main.py:473` |
| TC-304 | Missing required fields returns 422 | `CheckoutIn`, `ShippingIn` | `main.py:129-132`, `main.py:91` |
| TC-305 | Order ID that is not a number returns 422 | `get_order` | `order_id: int = PathParam(le=MAX_INT)` at `main.py:529` |
| TC-306 | Checkout with the declined card returns 402 | `checkout` | `body.card_number == DECLINED_CARD` at `main.py:476` |
| TC-307 | Cancel already-cancelled order returns 409 | `cancel_order` | `changed.rowcount != 1` → `Order is already cancelled` at `main.py:540` |
| TC-405 | Order ID 0 and negative order ID return 404 | `_own_order` | `db.get(Order, order_id)` returns `None` → 404 at `main.py:518` |

---

### Component Tests
_Criteria: Single view renders correctly for a given mocked API response or stored state. No real backend data needed. Source: `showOrders` (`index.html:880`), `showOrder` (`index.html:898`) in `app/static/index.html`_

#### Display Formatting — `showOrder` view (`index.html:898`)
| TC | Title | Mocked State | Assertion |
|---|---|---|---|
| TC-502 | Status pill shows the order status with the matching style | Mock `GET /orders` with one `paid` and one `cancelled` order | `order-status` has text and class `paid` / `cancelled` |
| TC-507 | Discount row shows the coupon code when a coupon was used | Mock order with `coupon_code: "WELCOME10"`, then with `null` | Label "Discount (WELCOME10)" / "Discount"; `order-discount` shows the amount |
| TC-508 | Amounts are shown in rupees with Indian digit grouping | Mock order with `total: 124999` | `order-total` contains "₹1,24,999" |
| TC-109 | "Cancel order" button only while the order is paid | Mock order `status: "paid"`, then `"cancelled"` | `order-cancel` visible, then count 0 |

#### Orders List — `showOrders` view (`index.html:880`)
| TC | Title | Mocked State | Assertion |
|---|---|---|---|
| TC-500 | Logged-out visit to orders redirects to login | No token in storage | URL is `#/login`; message "Please log in first."; no `/orders` request sent |
| TC-501 | Empty state when no orders | Mock `GET /orders` → `[]` | `orders-empty` shows "You have no orders yet." + "Start shopping" link; no `orders-table`, no `orders-count` |
| TC-308 | Error state when server unreachable | `route.abort()` on `GET /orders` | `message` shows a plain-language error. By code reading (not run), `e.message` is shown as-is at `index.html:1129`, so the browser's raw text such as "Failed to fetch" is expected — report as a defect if confirmed |
| TC-510 | Ended session on the orders page sends the user to login | Token in storage; mock `GET /orders` → 401 | URL is `#/login`; message "Your session has ended. Please log in again." |

#### Order Detail — `showOrder` view (`index.html:898`)
| TC | Title | Mocked State | Assertion |
|---|---|---|---|
| TC-300 | "Order not found" renders on 404 | Mock `GET /orders/99999` → 404 `{"detail": "Order not found"}` | `message` = "Order not found"; view is empty |

---

### E2E Tests
_Criteria: Multi-page user journey, full-stack data flow, cross-session security requiring real browser state. Source: Playwright for Python, fixtures in `tests/conftest.py`_

#### Critical Happy Paths (must have green before shipping)
| TC | Title | Precondition | Journey Scope |
|---|---|---|---|
| TC-001 | View orders list with existing orders | 1+ orders in DB | Login → `#/orders` → assert rows rendered |
| TC-002 | View single order detail page | 1+ orders | Login → `#/orders` → order number link → `#/orders/:id` → assert all sections |
| TC-003 | Cancel a single order from detail page | 1+ `paid` orders | Login → detail → "Cancel order" → assert message + status `cancelled` + still in list |
| TC-004 | Place an order and land on its detail page | Cart has a product | Login → `#/checkout` → Shipping → Payment → Review → place order → assert `#/orders/:id` + "Order placed." |
| TC-006 | Navigate to orders via "Orders" link after completing an order | Fresh account | Login → place order → "Orders" → assert new order is the first row |
| TC-005 | Navigate back to orders list from detail page | On detail page | "Back to orders" → assert `#/orders` |

#### Business Rule Validation (E2E confirms end-to-end rule enforcement)
| TC | Title | What E2E Adds Over API Test |
|---|---|---|
| TC-402 | Order with quantity = 1 (minimum) — full happy path | Validates the product page, cart, checkout and order detail UI carry the quantity and totals through, not just API response |

#### Security (requires two browser sessions)
| TC | Title | Why Must Be E2E |
|---|---|---|
| TC-200 | Cross-user order access shows "Order not found" UI | Requires login as User A, capture order ID, logout, login as User B, navigate — multi-session flow |
| TC-509 | Another user's order — "Order not found" state rendered, nothing of User A shown | Validates the `else` branch at `index.html:1129` clears the view (`view.innerHTML = ''`) and shows the API message |

#### Edge Case UI Behaviors (requires real UI interaction)
| TC | Title | Why Must Be E2E |
|---|---|---|
| TC-503 | Cancel order acts immediately with no confirmation dialog | Dialog absence requires real DOM interaction |
| TC-504 | Leaving the detail page without clicking cancel does NOT cancel | Requires real navigation; must verify no cancel API call was made |
| TC-507* | Discount row shows the coupon code | *Preferred as Component; E2E only if Component tests don't exist |

#### UI State Requiring Real Navigation
| TC | Title | Why Must Be E2E |
|---|---|---|
| TC-505 | Order detail title and browser tab display the order number | Part of TC-002; verify `o.id` rendered in `order-title` and `document.title` |
| TC-506 | Cancel success — message + updated page | Validates the `cancel` action at `index.html:1196`: "Order cancelled." visible + re-render without `order-cancel` |

---

## 3. Decision Rationale — Contested Assignments

### TC-502 / TC-507 / TC-508 — Display Formatting → Component (not E2E)
**Original suggestion**: E2E
**Decision**: Component only

**Rationale**: The amount and label formatting in `showOrder` at `index.html:898` is 100% client-side. The logic is:
```javascript
const rupee = n => '₹' + Number(n).toLocaleString('en-IN');
```
There is no backend rule behind it. No database. This makes E2E testing this rule wasteful — it adds login overhead, placing a real order worth 100000 or more, and a second order with a coupon per test. A component test with a mocked order (`total: 124999`, `coupon_code: "WELCOME10"`) covers all branches in milliseconds. The status pill is also best validated at Component level using Playwright's `page.route()` to return one `paid` and one `cancelled` order.

---

### TC-304 / TC-305 / TC-306 — Validation Errors → API (not E2E)
**Original suggestion**: API
**Decision**: API confirmed — do NOT add E2E coverage

**Rationale**: Input validation lives entirely in the `CheckoutIn` and `ShippingIn` models (`main.py:129`, `main.py:91`). The models are validated before the `checkout` function body is even reached. Testing a missing `full_name` at E2E would require filling a form, submitting, and checking a field message — and the UI's own field-level checks stop the request before it reaches the server, so the server rule is never exercised. The same rule is proven more precisely with a direct `POST /checkout` returning `422`. E2E for validation errors is the **ice cream cone anti-pattern**: slow, brittle, and testing at the wrong level.

---

### TC-100 / TC-101 / TC-400 / TC-401 — Stock and Concurrency Guards → API (not E2E)
**Original suggestion**: API
**Decision**: API confirmed — do NOT add E2E coverage for stock guards

**Rationale**: Stock handling is orchestrated entirely in `checkout` (`main.py:470-511`) and `cancel_order` (`main.py:534-545`). It involves:
1. `delete(CartItem)` + `claimed.rowcount` — cart claim, one cart becomes one order
2. `update(Product).where(Product.stock >= i.quantity)` — guarded stock take
3. `update(Order).where(Order.status == "paid")` — guarded cancel
4. `update(Product).values(stock=Product.stock + i.quantity)` — stock return on cancel

None of these are observable in the UI without checking stock before and after. An API test can precisely note the stock, send two requests in parallel, and assert DB state. E2E would be fragile (requires two simultaneous clicks, timing-sensitive).

---

### TC-200 / TC-509 — Cross-User Security → E2E (not just API)
**Original suggestion**: E2E (Security)
**Decision**: Both API and E2E required

**Rationale**: TC-201 covers the API-level 404. But TC-200 and TC-509 test the **frontend handling** of the 404 response:
```javascript
// index.html:1127
} catch (e) {
  if (e.status === 401) { flash = { text: 'Your session has ended. Please log in again.', kind: 'error' }; go('#/login'); }
  else { view.innerHTML = ''; say(e.message); }
}
```
This branch is only exercised by navigating to a real cross-user URL in a real browser. The view being cleared and the "Order not found" message being rendered is a UI-layer assertion that API tests cannot make.

---

### TC-500 / TC-501 / TC-308 — Login/Error/Empty States → Component (not E2E)
**Original suggestion**: E2E
**Decision**: Component with mocked API responses

**Rationale**: All three states (logged out, error, empty) are driven by client-side checks (`needLogin()` at `index.html:520`, the `catch` at `index.html:1127`, the `orders.length` branch at `index.html:885`). These are testable via `page.route()` interception:
```python
page.route("**/orders", lambda route: route.fulfill(status=200, json=[]))   # empty state
page.route("**/orders", lambda route: route.abort())                        # server unreachable
```
Running a full E2E test just to verify the empty state rendering is wasteful. Component tests with route interception isolate the frontend logic from backend availability.

---

## 4. Anti-Patterns to Avoid

These anti-patterns were identified from the suggested layers in the scenario document and must NOT be implemented:

| Anti-Pattern | Affected TCs | Correct Approach |
|---|---|---|
| Testing order ID boundary (`abc`, 2147483648) at E2E | TC-305, TC-405 | API test: `GET /orders/abc` → verify 422 response from `PathParam(le=MAX_INT)` at `main.py:529` |
| Testing rupee formatting at E2E (login + place a 100000 order + navigate) | TC-502, TC-507, TC-508 | Component test: mock `GET /orders/1`, open `#/orders/1`, assert `order-total` and the discount label |
| Testing concurrency guards at E2E (requires two simultaneous clicks) | TC-400, TC-401 | API test: use direct parallel `POST /checkout` or `POST /orders/:id/cancel` calls to set up state precisely |
| Testing "Order not found" by navigating to `#/orders/99999` at E2E | TC-300 | Component test: mock a 404 with `{"detail": "Order not found"}` via route interception |
| Testing auth 401 responses by manipulating UI session at E2E | TC-203, TC-204, TC-205 | API test: send requests without `Authorization` header, assert 401 |
| No E2E coverage for the cancel order flow | — | TC-003 and TC-506 must have E2E — cancellation is a destructive action visible to users |

---

## 5. Defense-in-Depth Coverage Map

Critical rules covered at multiple layers for maximum confidence:

| Rule | Unit | API | Component | E2E |
|---|---|---|---|---|
| Total = subtotal − discount | TC-102 | TC-102 | — | TC-004 (implicit) |
| Line total = unit price × quantity | TC-105 | TC-105 | — | TC-002 (implicit) |
| Flat coupon: subtotal ≥ 1500 accepted, below rejected | TC-103, TC-404 | TC-104 | — | — |
| Cross-user access denied | — | TC-201, TC-202 | — | TC-200, TC-509 |
| Cancel order — status `cancelled`, record kept, message shown | — | TC-307, TC-406 | TC-109 | TC-003, TC-506 |
| Stock taken at checkout, returned once on cancel | — | TC-100, TC-101, TC-400, TC-401 | — | — |
| Auth required (401 on all order endpoints) | — | TC-203, TC-204, TC-205, TC-206 | TC-510 | — |

---

## 6. Implementation Priority Order

Ship in this order — each tier unblocks the next:

**Tier 1 — P0, must pass before any release**
- `TC-001, TC-002, TC-003, TC-004` (E2E happy paths)
- `TC-102, TC-105` (order totals rule — Unit + API)
- `TC-201, TC-202` (security — API)
- `TC-200` (cross-user access — E2E)
- `TC-100, TC-101, TC-302` (stock and insufficient stock — API)

**Tier 2 — P1, run on every change**
- `TC-400, TC-401` (concurrency guards — API)
- `TC-103, TC-104, TC-404` (flat coupon — Unit + API)
- `TC-203, TC-204, TC-205, TC-206` (auth enforcement — API)
- `TC-304, TC-305, TC-306` (validation — API)
- `TC-107, TC-307, TC-303, TC-301` (cancel once, empty cart, not found — API)
- `TC-500, TC-501, TC-308` (UI states — Component)
- `TC-503, TC-506, TC-509` (cancel behaviour + cross-user state — E2E)

**Tier 3 — P2, run nightly or pre-release**
- `TC-405, TC-408` (edge cases — API)
- `TC-007, TC-106, TC-108, TC-403, TC-406, TC-407` (contracts and remaining rules — API)
- `TC-005, TC-006, TC-402, TC-504, TC-505` (navigation and quantity boundary — E2E)
- `TC-109, TC-300, TC-502, TC-507, TC-508, TC-510` (UI micro-states — Component)

---

## 7. Source File Map for Test Generation

| Layer | Test File Location | Key Source Files |
|---|---|---|
| Unit | `tests/unit/test_orders_unit.py` (folder does not exist yet) | `app/main.py` (`compute_discount`, `order_out`) |
| API | `tests/test_cases_api.py` | `app/main.py` (`checkout`, `cancel_order`, `_own_order`, `CheckoutIn`, `ShippingIn`) |
| Component | `tests/components/test_orders_ui_states.py` (folder does not exist yet) | `app/static/index.html` (`showOrders`, `showOrder`, `api`, `needLogin`) |
| E2E | `tests/test_cases_ui.py` | Full stack; use `alice@example.com` / `bob@example.com` |
