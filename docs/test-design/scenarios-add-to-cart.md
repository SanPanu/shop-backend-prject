# Practice Shop — Add to Cart Test Scenarios

Generated: 2026-10-25
Scope: Add to Cart (Flow 2 — Add from Product Card, Add from Product Detail, Quantity, Stock Limit, Cart Badge)

---

## Happy Path

### TC-001: Add a product to the cart from a product card
**Category**: Happy Path
**Priority**: P0
**Preconditions**: User is logged in; cart is empty
**Steps**:
1. Navigate to `#/` (or `#/list`)
2. Click "Add to cart" (`add-to-cart`) on the card of product 5 (Cotton T-Shirt)
3. Observe the message and the header cart badge
**Expected Results**: Success message "Added to cart." appears; `cart-count` badge shows 1; user stays on the same page
**Business Rule**: Card button sends `POST /cart/items` with `quantity: 1`; `refreshNav` recounts the badge
**Suggested Layer**: E2E

---

### TC-002: Add a chosen quantity from the product detail page
**Category**: Happy Path
**Priority**: P0
**Preconditions**: User is logged in; cart is empty
**Steps**:
1. Navigate to `#/p/5`
2. Enter 3 in the Quantity field (`detail-qty`)
3. Click "Add to cart" (`detail-add`)
4. Navigate to `#/cart`
**Expected Results**: Message "Added to cart." appears; badge shows 3; cart row `cart-row-5` shows quantity 3, price ₹499 and line total ₹1,497; `cart-units` chip shows "3 item(s)"
**Business Rule**: `add-detail` action sends `{ product_id, quantity }` from `detail-qty`
**Suggested Layer**: E2E

---

### TC-003: Add a product via API
**Category**: Happy Path
**Priority**: P0
**Preconditions**: User has a valid bearer token; cart is empty
**Steps**:
1. Send `POST /cart/items` with `{ "product_id": 5, "quantity": 2 }`
**Expected Results**: HTTP 200; body is the cart: `items` holds one line with `product_id: 5`, `name: "Cotton T-Shirt"`, `unit_price: 499`, `quantity: 2`, `line_total: 998`; `subtotal: 998`
**Business Rule**: `add_to_cart` → `_set_quantity(add=True)` → returns `cart_out`
**Suggested Layer**: API

---

### TC-004: Quantity defaults to 1 when it is not sent
**Category**: Happy Path
**Priority**: P1
**Preconditions**: User has a valid bearer token; cart is empty
**Steps**:
1. Send `POST /cart/items` with `{ "product_id": 9 }`
**Expected Results**: HTTP 200; the line for product 9 has `quantity: 1` and `line_total: 299`
**Business Rule**: `CartAddIn.quantity` — `Field(default=1, ge=1)`
**Suggested Layer**: API

---

### TC-005: Add several different products
**Category**: Happy Path
**Priority**: P1
**Preconditions**: User is logged in; cart is empty
**Steps**:
1. Add product 5 (quantity 1), then product 9 (quantity 2), then product 7 (quantity 1)
2. Send `GET /cart` (or open `#/cart`)
**Expected Results**: Three lines, listed in the order they were added (5, 9, 7); `subtotal` = 499 + 598 + 1999 = 3096; badge shows 4
**Business Rule**: `cart_out` orders lines by `CartItem.id`; `subtotal` is the sum of `line_total`
**Suggested Layer**: API / E2E

---

### TC-006: Cart is kept after logging out and back in
**Category**: Happy Path
**Priority**: P1
**Preconditions**: User is logged in; cart is empty
**Steps**:
1. Add product 5 to the cart
2. Click "Log out", then log in again with the same account
3. Navigate to `#/cart`
**Expected Results**: Product 5 is still in the cart with the same quantity; badge shows the same count
**Business Rule**: Cart rows are stored per user in `cart_items`, not in the browser ("Your Cart, Saved")
**Suggested Layer**: E2E

---

## Business Rules

### TC-100: Adding a product already in the cart increases its quantity
**Category**: Business Rule
**Priority**: P0
**Preconditions**: User has a valid bearer token; cart is empty
**Steps**:
1. Send `POST /cart/items` with `{ "product_id": 5, "quantity": 2 }`
2. Send `POST /cart/items` with `{ "product_id": 5, "quantity": 3 }`
**Expected Results**: Cart still has one line for product 5, now with `quantity: 5` and `line_total: 2495`
**Business Rule**: `_set_quantity(add=True)` — `wanted = quantity + item.quantity`; one row per user and product (`UniqueConstraint("user_id", "product_id")`)
**Suggested Layer**: API

---

### TC-101: Cart quantity cannot exceed the product's stock
**Category**: Business Rule
**Priority**: P0
**Preconditions**: User has a valid bearer token; product 10 has 2 units
**Steps**:
1. Send `POST /cart/items` with `{ "product_id": 10, "quantity": 3 }`
2. Send `GET /cart`
**Expected Results**: HTTP 409 "Only 2 in stock"; cart is unchanged (no line for product 10)
**Business Rule**: `_set_quantity` — `wanted > product.stock` → 409 `Only {stock} in stock`
**Suggested Layer**: API

---

### TC-102: Stock limit counts what is already in the cart
**Category**: Business Rule
**Priority**: P0
**Preconditions**: User has a valid bearer token; product 10 has 2 units
**Steps**:
1. Send `POST /cart/items` with `{ "product_id": 10, "quantity": 2 }`
2. Send `POST /cart/items` with `{ "product_id": 10, "quantity": 1 }`
3. Send `GET /cart`
**Expected Results**: Step 1 returns 200; step 2 returns HTTP 409 "Only 2 in stock"; cart still shows `quantity: 2` for product 10
**Business Rule**: The check uses `wanted` (existing + new quantity), not the new quantity alone
**Suggested Layer**: API

---

### TC-103: Adding to the cart does not reduce stock
**Category**: Business Rule
**Priority**: P0
**Preconditions**: User has a valid bearer token
**Steps**:
1. Note `stock` from `GET /products/10` (2)
2. Send `POST /cart/items` with `{ "product_id": 10, "quantity": 2 }`
3. Send `GET /products/10`
**Expected Results**: `stock` is still 2 and `in_stock` is true; stock only drops at checkout
**Business Rule**: `_set_quantity` writes only `cart_items`; stock changes only in `checkout` and `cancel_order`
**Suggested Layer**: API

---

### TC-104: Two users can each add the same last units
**Category**: Business Rule
**Priority**: P1
**Preconditions**: Product 10 has 2 units; alice and bob each have a valid token and an empty cart
**Steps**:
1. As alice, send `POST /cart/items` with `{ "product_id": 10, "quantity": 2 }`
2. As bob, send the same request
**Expected Results**: Both return HTTP 200; each cart holds 2 units of product 10 (the stock limit is checked again at checkout)
**Business Rule**: Stock is not reserved by the cart; the limit is per cart against current stock
**Suggested Layer**: API

---

### TC-105: Cart line uses the product's current price
**Category**: Business Rule
**Priority**: P1
**Preconditions**: User has a valid bearer token
**Steps**:
1. Send `GET /products/7` and note `price` (1999)
2. Send `POST /cart/items` with `{ "product_id": 7, "quantity": 2 }`
**Expected Results**: Line `unit_price` equals the product `price` (1999), not `mrp`; `line_total` = 3998
**Business Rule**: `cart_out` — `unit_price = product.price`, `line_total = price × quantity`
**Suggested Layer**: API

---

### TC-106: Header badge shows total units, not number of lines
**Category**: Business Rule
**Priority**: P2
**Preconditions**: User is logged in; cart is empty
**Steps**:
1. Add product 5 with quantity 3 from `#/p/5`
2. Add product 9 from its card
3. Observe `cart-count`
**Expected Results**: Badge shows 4
**Business Rule**: `refreshNav` — `items.reduce((n, i) => n + i.quantity, 0)`
**Suggested Layer**: E2E

---

## Security

### TC-200: Add to cart without a token returns 401
**Category**: Security
**Priority**: P0
**Preconditions**: No bearer token
**Steps**:
1. Send `POST /cart/items` with `{ "product_id": 5 }` and no Authorization header
**Expected Results**: HTTP 401 "Missing bearer token"; no cart row is created
**Business Rule**: `current_user` dependency on `add_to_cart`
**Suggested Layer**: API

---

### TC-201: Add to cart with an invalid or logged-out token returns 401
**Category**: Security
**Priority**: P0
**Preconditions**: User has a token
**Steps**:
1. Send `POST /auth/logout` with the token
2. Send `POST /cart/items` with the same token
3. Send `POST /cart/items` with `Authorization: Bearer not-a-real-token`
**Expected Results**: HTTP 401 "Invalid token" for both requests
**Business Rule**: `current_user` — token not found → 401 "Invalid token"
**Suggested Layer**: API

---

### TC-202: Adding as one user does not change another user's cart
**Category**: Security
**Priority**: P0
**Preconditions**: alice and bob each have a valid token and an empty cart
**Steps**:
1. As alice, send `POST /cart/items` with `{ "product_id": 5, "quantity": 2 }`
2. As bob, send `GET /cart`
**Expected Results**: bob's cart has no items and `subtotal: 0`; alice's cart has product 5
**Business Rule**: Cart rows are keyed by `user_id` from the token; the request body has no user field
**Suggested Layer**: API

---

### TC-203: Authorization header without the "Bearer " prefix is rejected
**Category**: Security
**Priority**: P2
**Preconditions**: User has a valid token
**Steps**:
1. Send `POST /cart/items` with `Authorization: <token>` (no "Bearer " prefix)
**Expected Results**: HTTP 401 "Missing bearer token"
**Business Rule**: `current_user` — header must start with `Bearer `
**Suggested Layer**: API

---

## Negative / Error

### TC-300: Add a product that does not exist returns 404
**Category**: Negative
**Priority**: P1
**Preconditions**: User has a valid bearer token
**Steps**:
1. Send `POST /cart/items` with `{ "product_id": 99999 }`
**Expected Results**: HTTP 404 "Product not found"; cart is unchanged
**Business Rule**: `_set_quantity` — `db.get(Product, id)` is None → 404
**Suggested Layer**: API

---

### TC-301: Add the out-of-stock product via API returns 409
**Category**: Negative
**Priority**: P0
**Preconditions**: User has a valid bearer token; product 8 has 0 units
**Steps**:
1. Send `POST /cart/items` with `{ "product_id": 8 }`
**Expected Results**: HTTP 409 "Only 0 in stock"; cart is unchanged
**Business Rule**: `wanted (1) > product.stock (0)` → 409
**Suggested Layer**: API

---

### TC-302: Quantity 0 or negative returns 422
**Category**: Negative
**Priority**: P1
**Preconditions**: User has a valid bearer token
**Steps**:
1. Send `POST /cart/items` with `{ "product_id": 5, "quantity": 0 }`
2. Send `POST /cart/items` with `{ "product_id": 5, "quantity": -1 }`
**Expected Results**: HTTP 422 validation error on `quantity` for both; cart is unchanged
**Business Rule**: `CartAddIn.quantity` — `ge=1`
**Suggested Layer**: API

---

### TC-303: Missing or non-integer product ID returns 422
**Category**: Negative
**Priority**: P1
**Preconditions**: User has a valid bearer token
**Steps**:
1. Send `POST /cart/items` with `{ "quantity": 1 }`
2. Send `POST /cart/items` with `{ "product_id": "abc" }`
3. Send `POST /cart/items` with `{ "product_id": 5, "quantity": 1.5 }`
**Expected Results**: HTTP 422 for all three; never HTTP 500; cart is unchanged
**Business Rule**: `CartAddIn` — `product_id: int` is required; `quantity: int`
**Suggested Layer**: API

---

### TC-304: Detail page — empty, decimal or zero quantity shows a field error
**Category**: Negative
**Priority**: P1
**Preconditions**: User is logged in; on `#/p/5`
**Steps**:
1. Clear `detail-qty` and click `detail-add`
2. Enter 1.5 and click `detail-add`
3. Enter 0 and click `detail-add`
**Expected Results**: Under the field (`error-detail-qty`) the messages are "Enter a quantity", "Quantity must be a whole number" and "Quantity must be at least 1"; no request is sent; badge is unchanged; no page-level message
**Business Rule**: `qtyMessage` + `fieldError` before the API call
**Suggested Layer**: E2E

---

### TC-305: Detail page — quantity above stock shows the API message under the field
**Category**: Negative
**Priority**: P0
**Preconditions**: User is logged in; product 10 has 2 units; cart is empty
**Steps**:
1. Navigate to `#/p/10`
2. Enter 3 in `detail-qty` and click `detail-add`
**Expected Results**: "Only 2 in stock" appears under the Quantity field (`error-detail-qty`); "Added to cart." is NOT shown; badge stays 0
**Business Rule**: `add-detail` — a 409 is shown with `fieldError` and returns `'handled'`
**Suggested Layer**: E2E

---

### TC-306: Product card — adding past stock shows the API message at the top of the page
**Category**: Negative
**Priority**: P1
**Preconditions**: User is logged in; cart already holds 2 units of product 10
**Steps**:
1. Navigate to a page listing product 10 (for example `#/list?category=home`)
2. Click `add-to-cart` on product 10
**Expected Results**: Message "Only 2 in stock" appears in the page message area; badge stays 2
**Business Rule**: Card has no quantity field, so `act` shows the error with `say(e.message)`
**Suggested Layer**: E2E

---

### TC-307: Add to cart when the server is unreachable
**Category**: Negative
**Priority**: P2
**Preconditions**: User is logged in; backend server is stopped after the page loads
**Steps**:
1. Click `add-to-cart` on any in-stock product
**Expected Results**: A plain-language error message is shown and "Added to cart." is not. Current behaviour is not verified; `act` shows the raw error text, so a browser message such as "Failed to fetch" would be a defect to report
**Business Rule**: Error text shown to users must be plain language
**Suggested Layer**: E2E

---

## Edge Cases

### TC-400: Add exactly all remaining stock (maximum)
**Category**: Edge Case
**Priority**: P1
**Preconditions**: User has a valid bearer token; product 10 has 2 units
**Steps**:
1. Send `POST /cart/items` with `{ "product_id": 10, "quantity": 2 }`
**Expected Results**: HTTP 200; line has `quantity: 2`, `line_total: 1298`
**Business Rule**: Check is `wanted > stock`, so `wanted == stock` is allowed
**Suggested Layer**: API

---

### TC-401: Quantity at the integer limit
**Category**: Edge Case
**Priority**: P2
**Preconditions**: User has a valid bearer token
**Steps**:
1. Send `POST /cart/items` with `{ "product_id": 5, "quantity": 2147483647 }`
2. Send `POST /cart/items` with `{ "product_id": 5, "quantity": 2147483648 }`
3. Send `POST /cart/items` with `{ "product_id": 2147483648 }`
**Expected Results**: Step 1: HTTP 409 "Only 50 in stock". Steps 2 and 3: HTTP 422. Never HTTP 500
**Business Rule**: `CartAddIn` — `le=MAX_INT` (2147483647) on `product_id` and `quantity`
**Suggested Layer**: API

---

### TC-402: Product ID 0 and negative product ID
**Category**: Edge Case
**Priority**: P2
**Preconditions**: User has a valid bearer token
**Steps**:
1. Send `POST /cart/items` with `{ "product_id": 0 }`
2. Send `POST /cart/items` with `{ "product_id": -1 }`
**Expected Results**: HTTP 404 "Product not found" for both; never HTTP 500
**Business Rule**: `product_id` has only an upper limit; no product has that ID
**Suggested Layer**: API

---

### TC-403: Two adds of a new product at the same moment
**Category**: Edge Case
**Priority**: P1
**Preconditions**: User has a valid bearer token; product 5 is not in the cart
**Steps**:
1. Send two `POST /cart/items` with `{ "product_id": 5, "quantity": 1 }` in parallel
2. Send `GET /cart`
**Expected Results**: Cart has exactly one line for product 5. Either both succeed with `quantity: 2`, or one returns HTTP 409 "The cart was changed by another request. Please try again" and the line has `quantity: 1`; never HTTP 500
**Business Rule**: `IntegrityError` on the unique (`user_id`, `product_id`) row → rollback and 409
**Suggested Layer**: API

---

### TC-404: Two adds of a product already in the cart at the same moment
**Category**: Edge Case
**Priority**: P2
**Preconditions**: User has a valid bearer token; cart holds product 5 with quantity 1
**Steps**:
1. Send two `POST /cart/items` with `{ "product_id": 5, "quantity": 1 }` in parallel
2. Send `GET /cart`
**Expected Results**: Final quantity matches the successful responses (3 if both return 200). Current behaviour is not verified: the existing row is read and rewritten without a lock, so a final quantity of 2 after two 200 responses would be a lost update to report
**Business Rule**: `_set_quantity` — `item.quantity = wanted` read-then-write
**Suggested Layer**: API

---

### TC-405: Very large quantity typed on the detail page
**Category**: Edge Case
**Priority**: P2
**Preconditions**: User is logged in; on `#/p/5`
**Steps**:
1. Enter 3000000000 in `detail-qty` and click `detail-add`
**Expected Results**: A plain-language message is shown under the Quantity field. Current behaviour is not verified: the value passes `qtyMessage`, the API returns 422, and the code shows it at page level as raw validation text (for example "body.quantity: Input should be less than or equal to 2147483647"), which would be a defect to report
**Business Rule**: Field errors under the field; error text must be plain language, never raw validation output
**Suggested Layer**: E2E

---

### TC-406: Field error clears after a valid add
**Category**: Edge Case
**Priority**: P2
**Preconditions**: User is logged in; on `#/p/5`
**Steps**:
1. Enter 0 and click `detail-add` (error shown)
2. Enter 1 and click `detail-add`
**Expected Results**: `error-detail-qty` disappears; "Added to cart." appears; badge increases by 1
**Business Rule**: `fieldError(qty, '')` removes the error when `qtyMessage` returns empty
**Suggested Layer**: E2E

---

## UI State

### TC-500: Logged-out add redirects to login and returns afterwards
**Category**: UI State
**Priority**: P0
**Preconditions**: User is not logged in
**Steps**:
1. Navigate to `#/p/5`
2. Click `detail-add`
3. Log in as alice
4. Observe the page and the cart badge
**Expected Results**: Step 2 sends the user to `#/login` with "Please log in first."; after login the user is back on `#/p/5`; the product was NOT added (badge 0)
**Business Rule**: `needLogin` stores `returnTo` and stops before the API call
**Suggested Layer**: E2E

---

### TC-501: Add buttons are disabled for an out-of-stock product
**Category**: UI State
**Priority**: P0
**Preconditions**: Product 8 has 0 units
**Steps**:
1. Find product 8 on a listing page (for example `#/list?category=electronics`)
2. Navigate to `#/p/8`
**Expected Results**: Card `add-to-cart` is disabled and `product-stock` shows "Out of stock"; on the detail page `detail-qty` and `detail-add` are disabled and `detail-stock` shows "Out of stock"
**Business Rule**: Buttons get `disabled` when `p.in_stock` is false
**Suggested Layer**: E2E

---

### TC-502: Detail page quantity starts at 1
**Category**: UI State
**Priority**: P2
**Preconditions**: Product is in stock
**Steps**:
1. Navigate to `#/p/5`
**Expected Results**: `detail-qty` has value 1 and minimum 1; `detail-stock` shows "50 in stock"
**Business Rule**: `<input type="number" min="1" value="1">`; `stock` helper text
**Suggested Layer**: E2E

---

### TC-503: Shown stock does not change after adding
**Category**: UI State
**Priority**: P2
**Preconditions**: User is logged in; on `#/p/10`
**Steps**:
1. Add 1 unit
2. Reload the page
**Expected Results**: `detail-stock` still shows "2 in stock"
**Business Rule**: Adding to the cart does not reserve stock
**Suggested Layer**: E2E

---

### TC-504: Ended session on add sends the user to login
**Category**: UI State
**Priority**: P2
**Preconditions**: User is logged in in the browser; the session has been ended on the server (for example by `POST /auth/logout` with the same token)
**Steps**:
1. Click `add-to-cart` on any in-stock product (and separately `detail-add` on a detail page)
2. Observe the page
**Expected Results**: User is sent to `#/login` with "Your session has ended. Please log in again."; "Added to cart." is not shown
**Business Rule**: `act` — `e.expired` (401 with a stored token) → flash and `go('#/login')`
**Suggested Layer**: E2E

---

### TC-505: Added product appears on the cart page with a link back
**Category**: UI State
**Priority**: P1
**Preconditions**: User is logged in; product 7 was added from its card
**Steps**:
1. Navigate to `#/cart`
2. Click the product name in `cart-row-7`
**Expected Results**: Row shows name "Wireless Earbuds", price ₹1,999, quantity 1, line total ₹1,999, and a Remove button; `cart-subtotal` shows ₹1,999; the name link opens `#/p/7`
**Business Rule**: `showCart` renders each line with a link to `#/p/:id`
**Suggested Layer**: E2E

---

### TC-506: Empty cart before any add
**Category**: UI State
**Priority**: P2
**Preconditions**: User is logged in with an empty cart
**Steps**:
1. Navigate to `#/cart`
2. Observe the header badge
**Expected Results**: `cart-empty` shows "Your cart is empty." with a "Browse products" button to `#/`; badge shows 0
**Business Rule**: `cart.items.length === 0` branch in `showCart`
**Suggested Layer**: E2E
