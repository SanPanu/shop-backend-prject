---
name: create-scenarios
description: Create test scenario documents for a Practice Shop feature area. Use when asked to create, write or list test scenarios, for example "/create-scenarios cart". Output follows the format of the Order Management example in this file.
---

When asked for scenarios, read `CLAUDE.md`, `app/main.py` and `app/static/index.html` for the real behaviour of the
requested area, then write a document in exactly the format below: same header, same six sections, same fields per
scenario. Never invent a rule, message or endpoint; quote what the code does. Save it as
`test-report/scenarios-<area>.md`.

# Practice Shop — Order Management Test Scenarios

Generated: 2026-10-11
Scope: Order Management (Flow 4 — View, Cancel, Stock Restore, Totals)

---

## Happy Path

### TC-001: View orders list with existing orders
**Category**: Happy Path
**Priority**: P0
**Preconditions**: User is logged in; user has at least one placed order
**Steps**:
1. Navigate to `#/orders`
2. Observe the rows rendered in the orders table
**Expected Results**: Each order row displays order number link (`#id`), placed date and time, status pill, and total; the header chip shows "N order(s)"
**Business Rule**: Flow 4 — Manage Orders
**Suggested Layer**: E2E

---

### TC-002: View single order detail page
**Category**: Happy Path
**Priority**: P0
**Preconditions**: User is logged in; user has at least one placed order
**Steps**:
1. Navigate to `#/orders`
2. Click the order number link on any order row
3. Observe the order detail page at `#/orders/:id`
**Expected Results**: Page shows title "Order #id", placed date, status pill, items table (Product, Price, Quantity, Total), Subtotal, Discount (with coupon code when one was used), Total, "Deliver to" block (full name, address lines, city, state, PIN code, country, email), "Back to orders" link, and "Cancel order" button
**Business Rule**: Order model fields; Flow 4
**Suggested Layer**: E2E

---

### TC-003: Cancel a single order from the detail page
**Category**: Happy Path
**Priority**: P0
**Preconditions**: User is logged in; user has at least one order with status `paid`
**Steps**:
1. Navigate to `#/orders/:id`
2. Click "Cancel order" button
3. Observe the message and the status pill
4. Navigate to `#/orders` and observe the list
**Expected Results**: Success message "Order cancelled." appears; user stays on `#/orders/:id`; status pill changes to `cancelled`; the order still appears in the list with status `cancelled`
**Business Rule**: Order cancellation keeps the record and sets status to `cancelled`; stock is returned to each product
**Suggested Layer**: E2E

---

### TC-004: Place an order and land on its detail page
**Category**: Happy Path
**Priority**: P0
**Preconditions**: User is logged in; cart has at least one product
**Steps**:
1. Navigate to `#/checkout`
2. Complete Shipping, Payment (card `4111111111111111`) and Review
3. Click the place order button
4. Observe the page after ordering
**Expected Results**: Message "Order placed." appears; user is redirected to `#/orders/:id` of the new order; status is `paid`; cart is empty
**Business Rule**: `POST /checkout` creates the order and removes the cart rows; `checkout` function in `app/main.py`
**Suggested Layer**: E2E

---

### TC-005: Navigate back to orders list from detail page
**Category**: Happy Path
**Priority**: P2
**Preconditions**: User is on an order detail page
**Steps**:
1. Click "Back to orders" link at bottom of detail page
**Expected Results**: User is navigated to `#/orders`
**Business Rule**: UI navigation flow
**Suggested Layer**: E2E

---

### TC-006: Navigate to orders via "Orders" link in the header after completing an order
**Category**: Happy Path
**Priority**: P1
**Preconditions**: User just completed an order (order detail page shown)
**Steps**:
1. After the order is placed, click "Orders" link in the header
2. Observe the orders page
**Expected Results**: User lands on `#/orders` and the newly created order appears as the first row
**Business Rule**: Flow 3 → Flow 4 navigation; orders are listed newest first
**Suggested Layer**: E2E

---

### TC-007: Lookup order by ID via API
**Category**: Happy Path
**Priority**: P1
**Preconditions**: User is authenticated; user has an order with known `id`
**Steps**:
1. Send `GET /orders/:id` with valid bearer token and own order ID
**Expected Results**: 200 response with full order data including nested `items` and `shipping`
**Business Rule**: `GET /orders/{order_id}` endpoint
**Suggested Layer**: API

---

## Business Rules

### TC-100: Stock reduces at checkout by the ordered quantity
**Category**: Business Rule
**Priority**: P0
**Preconditions**: User has a product in the cart with known stock; user has bearer token
**Steps**:
1. Note the product's `stock` via `GET /products/:id`
2. Place the order via `POST /checkout`
3. Retrieve the product again
**Expected Results**: `stock` is lower by exactly the ordered quantity; the order is present in `GET /orders`
**Business Rule**: Guarded stock UPDATE in `checkout`; stock never goes below zero
**Suggested Layer**: API

---

### TC-101: Cancelling an order restores stock for every item
**Category**: Business Rule
**Priority**: P0
**Preconditions**: User has a `paid` order with two different products
**Steps**:
1. Note the stock of both products
2. Cancel the order via `POST /orders/:id/cancel`
3. Retrieve both products
**Expected Results**: Each product's `stock` increases by that item's quantity; order `status` is `cancelled`
**Business Rule**: `cancel_order` adds `quantity` back to `Product.stock` for each order item
**Suggested Layer**: API

---

### TC-102: Order total equals subtotal minus discount
**Category**: Business Rule
**Priority**: P0
**Preconditions**: User is logged in; cart has products with known prices; coupon `WELCOME10` exists
**Steps**:
1. Place the order with `coupon_code: "WELCOME10"`
2. Read `subtotal`, `discount` and `total` from the order detail page or API response
**Expected Results**: `discount` is 10% of `subtotal` rounded down to a whole rupee; `total = subtotal - discount`; `coupon_code` is `WELCOME10`
**Business Rule**: `compute_discount`: percent coupon = `subtotal * value // 100`
**Suggested Layer**: E2E / API

---

### TC-103: Flat coupon — order at or above the minimum gets 200 off
**Category**: Business Rule
**Priority**: P0
**Preconditions**: User has a cart with subtotal of 1500 or more
**Steps**:
1. Place the order with `coupon_code: "FLAT200"`
2. Read the order totals
**Expected Results**: `discount` is 200; `total = subtotal - 200`
**Business Rule**: `FLAT200` — 200 off, minimum order 1500
**Suggested Layer**: API

---

### TC-104: Flat coupon — order below the minimum is NOT accepted
**Category**: Business Rule
**Priority**: P0
**Preconditions**: User has a cart with subtotal below 1500
**Steps**:
1. Send `POST /checkout` with `coupon_code: "FLAT200"`
2. Retrieve the cart and the orders list
**Expected Results**: HTTP 400 "Coupon needs a minimum order of 1500"; no order is created; cart is unchanged
**Business Rule**: `compute_discount` — `subtotal < coupon.min_order` → rejected
**Suggested Layer**: API

---

### TC-105: Line total is calculated as unit price × quantity
**Category**: Business Rule
**Priority**: P0
**Preconditions**: User orders a product with known price
**Steps**:
1. Order a product with quantity 3
2. View the order detail page
**Expected Results**: Items table "Total" column shows `unit_price × 3`; `line_total` in API response equals `unit_price × quantity`; `subtotal` equals the sum of all `line_total` values
**Business Rule**: `order_out` — `line_total = unit_price × quantity`
**Suggested Layer**: E2E / API

---

### TC-106: Orders list is sorted newest first
**Category**: Business Rule
**Priority**: P1
**Preconditions**: User has at least two orders
**Steps**:
1. Send `GET /orders`
**Expected Results**: Response is an array ordered by `id` descending; the most recent order is first
**Business Rule**: `list_orders` — `order_by(Order.id.desc())`
**Suggested Layer**: API

---

### TC-107: An order can be cancelled only once
**Category**: Business Rule
**Priority**: P0
**Preconditions**: User has a `paid` order
**Steps**:
1. Cancel the order via `POST /orders/:id/cancel`
2. Note the product stock
3. Cancel the same order again
4. Re-fetch the product
**Expected Results**: Second request returns HTTP 409 "Order is already cancelled"; stock does not increase a second time
**Business Rule**: Guarded UPDATE in `cancel_order` — only a `paid` order changes
**Suggested Layer**: API

---

### TC-108: Checkout empties the cart
**Category**: Business Rule
**Priority**: P1
**Preconditions**: User has products in the cart
**Steps**:
1. Place the order
2. Send `GET /cart`
**Expected Results**: Cart has no items and `subtotal` is 0; the header cart badge shows no count
**Business Rule**: `checkout` claims (deletes) the cart rows before creating the order
**Suggested Layer**: API / E2E

---

### TC-109: Order detail shows "Cancel order" button only while the order is paid
**Category**: Business Rule
**Priority**: P2
**Preconditions**: User has one `paid` order and one `cancelled` order
**Steps**:
1. Navigate to `#/orders/:id` of the paid order
2. Navigate to `#/orders/:id` of the cancelled order
**Expected Results**: "Cancel order" button is visible for the paid order and absent for the cancelled order
**Business Rule**: Flow 4 — UI shows the cancel option only when `status === 'paid'`
**Suggested Layer**: E2E

---

## Security

### TC-200: Cross-user order access shows "Order not found" (UI)
**Category**: Security
**Priority**: P0
**Preconditions**: Two test accounts exist (alice@example.com and bob@example.com); User A has an order
**Steps**:
1. Log in as User A, place an order, note the order ID
2. Log out
3. Log in as User B
4. Navigate to `#/orders/:userA_order_id`
**Expected Results**: Page shows the message "Order not found" and none of User A's order details
**Business Rule**: Cross-user access returns 404, the same as a missing order, so order IDs of other users are not revealed
**Suggested Layer**: E2E

---

### TC-201: Cross-user order access returns 404 via API
**Category**: Security
**Priority**: P0
**Preconditions**: User A has an order; User B has a valid bearer token
**Steps**:
1. Send `GET /orders/:userA_order_id` with User B's token
**Expected Results**: HTTP 404; response body contains "Order not found"
**Business Rule**: `_own_order` — `order.user_id != user.id` → 404
**Suggested Layer**: API

---

### TC-202: Cross-user order cancellation returns 404 via API
**Category**: Security
**Priority**: P0
**Preconditions**: User A has a `paid` order; User B has a valid bearer token
**Steps**:
1. Send `POST /orders/:userA_order_id/cancel` with User B's token
2. As User A, fetch the order
**Expected Results**: HTTP 404; order status is still `paid`; product stock is unchanged
**Business Rule**: `cancel_order` uses `_own_order` — ownership check before any change
**Suggested Layer**: API

---

### TC-203: Unauthenticated access to orders list returns 401
**Category**: Security
**Priority**: P0
**Preconditions**: No bearer token
**Steps**:
1. Send `GET /orders` without Authorization header
**Expected Results**: HTTP 401; "Missing bearer token" error message
**Business Rule**: `current_user` dependency on all `/orders` routes
**Suggested Layer**: API

---

### TC-204: Unauthenticated access to order detail returns 401
**Category**: Security
**Priority**: P0
**Preconditions**: No bearer token
**Steps**:
1. Send `GET /orders/:id` without Authorization header
**Expected Results**: HTTP 401; "Missing bearer token" error message
**Business Rule**: `current_user` dependency
**Suggested Layer**: API

---

### TC-205: Unauthenticated POST /orders/:id/cancel returns 401
**Category**: Security
**Priority**: P0
**Preconditions**: No bearer token
**Steps**:
1. Send `POST /orders/:id/cancel` without Authorization header
**Expected Results**: HTTP 401; order status is unchanged
**Business Rule**: `current_user` dependency; `cancel_order` requires authenticated user
**Suggested Layer**: API

---

### TC-206: Token is rejected after logout
**Category**: Security
**Priority**: P1
**Preconditions**: User A is logged in with a known token
**Steps**:
1. Send `POST /auth/logout` with the token
2. Send `GET /orders` with the same token
**Expected Results**: HTTP 401; "Invalid token"
**Business Rule**: `POST /auth/logout` ends the current session
**Suggested Layer**: API

---

## Negative / Error

### TC-300: Navigate to non-existent order ID shows "Order not found"
**Category**: Negative
**Priority**: P1
**Preconditions**: User is logged in
**Steps**:
1. Navigate to `#/orders/99999` (ID that does not exist)
**Expected Results**: Page shows the message "Order not found" and no order content
**Business Rule**: `_own_order` raises 404; the UI shows the message from the API
**Suggested Layer**: E2E

---

### TC-301: GET /orders/:id with non-existent ID returns 404
**Category**: Negative
**Priority**: P1
**Preconditions**: User is authenticated
**Steps**:
1. Send `GET /orders/99999` with valid bearer token
**Expected Results**: HTTP 404; error message "Order not found"
**Business Rule**: `_own_order` — 404
**Suggested Layer**: API

---

### TC-302: Checkout with insufficient stock returns 409
**Category**: Negative
**Priority**: P0
**Preconditions**: Product 10 has 2 units; User A and User B each have 2 units of product 10 in the cart
**Steps**:
1. User B sends `POST /checkout` (succeeds, stock becomes 0)
2. User A sends `POST /checkout`
**Expected Results**: User A gets HTTP 409 "Not enough stock for <product name>"; no order is created for User A; User A's cart is unchanged; stock stays 0
**Business Rule**: `checkout` — guarded stock UPDATE fails → rollback
**Suggested Layer**: API

---

### TC-303: Checkout with an empty cart returns 400
**Category**: Negative
**Priority**: P1
**Preconditions**: User is authenticated; cart is empty
**Steps**:
1. Send `POST /checkout` with a valid card and shipping address
**Expected Results**: HTTP 400; "Cart is empty"
**Business Rule**: `checkout` — no cart items → 400
**Suggested Layer**: API

---

### TC-304: Checkout with missing required fields returns 422
**Category**: Negative
**Priority**: P1
**Preconditions**: User is authenticated; cart has a product
**Steps**:
1. Send `POST /checkout` with missing `shipping`, or with `shipping` missing `full_name`, `line1`, `city`, `state` or `postal_code`
**Expected Results**: HTTP 422; validation error naming the missing field; no order is created
**Business Rule**: `CheckoutIn` input validation
**Suggested Layer**: API

---

### TC-305: Order ID that is not a number returns 422
**Category**: Negative
**Priority**: P1
**Preconditions**: User is authenticated
**Steps**:
1. Send `GET /orders/abc`
2. Send `GET /orders/2147483648`
**Expected Results**: HTTP 422 validation error for both cases; never HTTP 500
**Business Rule**: order ID must be an integer no larger than 2147483647
**Suggested Layer**: API

---

### TC-306: Checkout with the declined card returns 402
**Category**: Negative
**Priority**: P1
**Preconditions**: User is authenticated; cart has a product
**Steps**:
1. Send `POST /checkout` with `card_number: "4000000000000002"`
**Expected Results**: HTTP 402 "Payment declined"; no order is created; cart and stock are unchanged
**Business Rule**: card `4000000000000002` is always declined
**Suggested Layer**: API

---

### TC-307: Cancel an order that has already been cancelled returns 409
**Category**: Negative
**Priority**: P1
**Preconditions**: User is authenticated; a `paid` order exists
**Steps**:
1. Cancel the order via `POST /orders/:id/cancel`
2. Attempt to cancel the same order again
**Expected Results**: HTTP 409; "Order is already cancelled"
**Business Rule**: `cancel_order` updates only where `status == "paid"`
**Suggested Layer**: API

---

### TC-308: Orders page shows an error when the server is unreachable
**Category**: Negative
**Priority**: P2
**Preconditions**: Backend server is down
**Steps**:
1. Navigate to `#/orders` with backend unavailable
**Expected Results**: A plain-language error message is shown and no stale order data is displayed. Current behaviour is not verified; a raw browser message such as "Failed to fetch" would be a defect to report
**Business Rule**: Error text shown to users must be plain language
**Suggested Layer**: E2E

---

## Edge Cases

### TC-400: Two cancel requests at the same moment — only one succeeds
**Category**: Edge Case
**Priority**: P0
**Preconditions**: User has a `paid` order
**Steps**:
1. Note the product stock
2. Send two `POST /orders/:id/cancel` requests in parallel
3. Check both responses and the product stock
**Expected Results**: One response is 200 and the other is 409; stock increases by the order quantity exactly once
**Business Rule**: Guarded UPDATE in `cancel_order`
**Suggested Layer**: API

---

### TC-401: Two checkout requests at the same moment — one cart becomes one order
**Category**: Edge Case
**Priority**: P0
**Preconditions**: User has products in the cart
**Steps**:
1. Send two `POST /checkout` requests in parallel
2. Send `GET /orders`
**Expected Results**: Exactly one order is created; the other request returns HTTP 409 "This cart is already being checked out" or HTTP 400 "Cart is empty"; stock is reduced once
**Business Rule**: cart "claim" DELETE before order creation in `checkout`
**Suggested Layer**: API

---

### TC-402: Order with quantity = 1 (minimum) — full happy path
**Category**: Edge Case
**Priority**: P1
**Preconditions**: User is logged in; product is in stock
**Steps**:
1. Navigate to a product detail page
2. Add 1 unit to the cart
3. Complete checkout
**Expected Results**: Order created with `quantity: 1`; `line_total = unit_price × 1`; order ID generated
**Business Rule**: quantity boundary: 1 is minimum
**Suggested Layer**: E2E

---

### TC-403: Order for all remaining stock (maximum)
**Category**: Edge Case
**Priority**: P1
**Preconditions**: User is logged in; product 10 has 2 units
**Steps**:
1. Add 2 units of product 10 to the cart
2. Complete checkout
3. Try to add product 10 to the cart again
**Expected Results**: Order created with `quantity: 2`; product stock is 0; the further add returns HTTP 409 "Only 0 in stock"
**Business Rule**: quantity boundary: cart quantity cannot exceed stock
**Suggested Layer**: E2E / API

---

### TC-404: Flat coupon boundary — subtotal exactly 1500 IS accepted
**Category**: Edge Case
**Priority**: P1
**Preconditions**: User has a cart whose subtotal is exactly 1500 (if seed prices cannot make 1500, test the nearest values on both sides)
**Steps**:
1. Send `POST /coupons/validate` with `code: "FLAT200"`
**Expected Results**: 200 response with `discount: 200` and `total: 1300`
**Business Rule**: threshold is `subtotal < min_order` → rejected; 1500 is the first accepted value
**Suggested Layer**: API

---

### TC-405: Order ID 0 and negative order ID
**Category**: Edge Case
**Priority**: P2
**Preconditions**: User is authenticated
**Steps**:
1. Send `GET /orders/0`
2. Send `GET /orders/-1`
**Expected Results**: HTTP 404 "Order not found" for both; never HTTP 500
**Business Rule**: `_own_order` — no order with that ID
**Suggested Layer**: API

---

### TC-406: Cancel when only one order exists
**Category**: Edge Case
**Priority**: P2
**Preconditions**: User has exactly 1 order
**Steps**:
1. Navigate to `#/orders/:id`
2. Click "Cancel order"
3. Navigate to `#/orders`
**Expected Results**: The list still shows 1 order with status `cancelled`; the empty state is NOT shown
**Business Rule**: cancellation never deletes the order record
**Suggested Layer**: E2E / API

---

### TC-407: Coupon code typed in lower case with spaces
**Category**: Edge Case
**Priority**: P2
**Preconditions**: User has products in the cart
**Steps**:
1. Send `POST /checkout` with `coupon_code: " welcome10 "`
**Expected Results**: Order is created with the discount applied; `coupon_code` in the response is `WELCOME10`
**Business Rule**: coupon codes are trimmed and upper-cased in `compute_discount` and `checkout`
**Suggested Layer**: API

---

### TC-408: Order placed time on MySQL — checkout response versus later reads
**Category**: Edge Case
**Priority**: P2
**Preconditions**: Shop is running on MySQL
**Steps**:
1. Place an order and note `created_at` from the `POST /checkout` response
2. Send `GET /orders/:id` and compare `created_at`
**Expected Results**: Both values should be equal. Known open defect: the checkout response includes fractions of a second and later reads do not
**Business Rule**: `orders.created_at` is `DATETIME` without fractional seconds on MySQL
**Suggested Layer**: API

---

## UI State

### TC-500: Logged-out visit to orders redirects to login
**Category**: UI State
**Priority**: P1
**Preconditions**: User is not logged in
**Steps**:
1. Navigate to `#/orders`
2. Observe the page
**Expected Results**: User is sent to `#/login` and the message "Please log in first." is shown; no order data is requested
**Business Rule**: `needLogin` check in `showOrders`
**Suggested Layer**: E2E

---

### TC-501: Orders list shows empty state when user has no orders
**Category**: UI State
**Priority**: P1
**Preconditions**: User is logged in with zero orders
**Steps**:
1. Navigate to `#/orders`
**Expected Results**: Empty state (`orders-empty`) renders with "You have no orders yet." and "Start shopping" button linking to `#/`; no orders table and no count chip
**Business Rule**: `orders.length === 0` branch in `showOrders`
**Suggested Layer**: E2E

---

### TC-502: Status pill shows the order status with the matching style
**Category**: UI State
**Priority**: P2
**Preconditions**: User has one `paid` and one `cancelled` order
**Steps**:
1. Navigate to `#/orders`
2. Observe the status pill of each row
**Expected Results**: `order-status` shows text `paid` with class `paid` (green) and text `cancelled` with class `cancelled` (red)
**Business Rule**: `.pill.paid` and `.pill.cancelled` styles
**Suggested Layer**: E2E

---

### TC-503: Cancel order acts immediately with no confirmation dialog
**Category**: UI State
**Priority**: P0
**Preconditions**: User is on the detail page of a `paid` order
**Steps**:
1. Click "Cancel order" button
2. Observe the page
**Expected Results**: No dialog appears; the order is cancelled on the first click. Report as a usability risk if a confirmation step is expected
**Business Rule**: `cancel` action calls `POST /orders/:id/cancel` directly
**Suggested Layer**: E2E

---

### TC-504: Leaving the detail page without clicking cancel does NOT cancel
**Category**: UI State
**Priority**: P1
**Preconditions**: User is on the detail page of a `paid` order
**Steps**:
1. Click "Back to orders"
2. Observe order status in the list
**Expected Results**: Order remains `paid`; no cancel API call made
**Business Rule**: cancellation happens only through the `order-cancel` button
**Suggested Layer**: E2E

---

### TC-505: Order detail title and browser tab display the order number
**Category**: UI State
**Priority**: P2
**Preconditions**: User navigates to a valid order detail page
**Steps**:
1. Navigate to `#/orders/:id`
2. Observe the page title and the browser tab title
**Expected Results**: `order-title` shows "Order #{id}" and the tab title contains "Order #{id}"
**Business Rule**: `showOrder` uses `o.id` for title and `setTitle`
**Suggested Layer**: E2E

---

### TC-506: Cancel order success — message and updated page
**Category**: UI State
**Priority**: P0
**Preconditions**: User clicks "Cancel order" on a `paid` order
**Steps**:
1. Click "Cancel order"
2. Observe page and notifications
**Expected Results**: Success message "Order cancelled." appears; status pill shows `cancelled`; "Cancel order" button is gone
**Business Rule**: `cancel` action sets the flash message and re-renders
**Suggested Layer**: E2E

---

### TC-507: Discount row shows the coupon code when a coupon was used
**Category**: UI State
**Priority**: P2
**Preconditions**: User has one order placed with `WELCOME10` and one without a coupon
**Steps**:
1. Open the order placed with the coupon
2. Open the order placed without a coupon
**Expected Results**: First order shows "Discount (WELCOME10)" with the discount amount; second shows "Discount" with −₹0
**Business Rule**: `o.coupon_code` in `showOrder`
**Suggested Layer**: E2E

---

### TC-508: Amounts are shown in rupees with Indian digit grouping
**Category**: UI State
**Priority**: P2
**Preconditions**: User has an order with total of 100000 or more
**Steps**:
1. Navigate to `#/orders` and to the order detail page
2. Read the total
**Expected Results**: Amounts start with ₹ and use Indian grouping (for example ₹1,24,999)
**Business Rule**: `rupee` helper: `toLocaleString('en-IN')`
**Suggested Layer**: E2E

---

### TC-509: Order detail shows "Order not found" state for another user's order
**Category**: UI State
**Priority**: P0
**Preconditions**: Another user's order ID is known
**Steps**:
1. Log in as User B
2. Navigate to `#/orders/:userA_order_id`
3. Observe the rendered state
**Expected Results**: Message "Order not found" renders and the page body is empty (no items, totals or address of User A)
**Business Rule**: API returns 404 for orders of other users; the UI shows the API message
**Suggested Layer**: E2E

---

### TC-510: Ended session on the orders page sends the user to login
**Category**: UI State
**Priority**: P2
**Preconditions**: User is logged in in the browser; the session has been ended on the server (for example by `POST /auth/logout` with the same token)
**Steps**:
1. Navigate to `#/orders`
2. Observe the page
**Expected Results**: User is sent to `#/login` with the message "Your session has ended. Please log in again."
**Business Rule**: 401 with a stored token is treated as an ended session
**Suggested Layer**: E2E
