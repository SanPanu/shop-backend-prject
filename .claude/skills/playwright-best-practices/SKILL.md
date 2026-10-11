---
name: playwright-best-practices
description: Playwright (Python, pytest) browser test standards for Practice Shop — locator strategy, assertion patterns, test structure, helper functions, API mocking, login and test data, wait strategies, and anti-patterns. Use when writing, reviewing, or debugging tests in tests/test_cases_ui.py.
user-invocable: false
---

# Playwright Test Automation Best Practices for Practice Shop

## Overview
This document defines the testing standards, patterns, and best practices for writing Playwright browser tests in the Practice Shop project. All test automation agents and code reviewers MUST follow these guidelines. The tests are Python (sync API) run by pytest. Do not write JavaScript tests, `.spec.js` files or a `playwright.config`.

---

## 1. Project Test Setup

### Config Reference
There is no Playwright config file. Everything is set by fixtures in `tests/conftest.py`:
- **Test file**: `tests/test_cases_ui.py`
- **Base URL**: supplied by the `live_server` fixture. It starts its own copy of the shop on a free port with a temporary SQLite database, so tests never touch the shop on port 8000 or the MySQL data. Always use relative paths: `page.goto("/#/cart")`
- **Timeout**: 7s per action (`set_default_timeout(7000)`), 5s per `expect` assertion (Playwright default)
- **Browser**: Chromium only, headless, viewport 1366 × 850
- **Parallel execution**: None (pytest runs tests one after another)
- **Reporter**: `test-report/test_cases.csv` and `test-report/results.json`, written by `conftest.py`
- **Screenshots / Video**: Not recorded
- **Data reset**: the `page` fixture calls `POST /test/reset` before every test
- **JavaScript errors**: collected in `page.js_errors`; any error fails the test automatically
- **Not installed**: if Playwright or Chromium is missing, browser tests are reported as Skipped, not failed

### File Naming Convention
- Browser tests go in `tests/test_cases_ui.py`
- Test functions: `test_ui_<number>`, for example `test_ui_053`
- Every test has `@case("TC-UI-<number>", title, steps, expected, priority)` from `tests/helpers.py`. Use the next free number; never reuse an ID
- Group related tests under the existing `# ---- section` comment lines (browsing, account, cart, checkout, orders, general)

---

## 2. Locator Strategy (Priority Order)

Always choose locators in this priority order for reliability and readability:

### Priority 1: data-testid (Most Preferred)
```python
t(page, "order-title")              # helper: page.get_by_test_id("order-title")
t(page, "add-to-cart")
```
Use for: Every interactive element. The project rule is that each one has a unique `data-testid` in `app/static/index.html`. If one is missing, add it there instead of using a weaker locator.

### Priority 2: Accessibility Roles
```python
t(page, "cart-empty").get_by_role("link")
page.get_by_role("button", name="Cancel order")
```
Use for: Links, buttons, headings inside an area already found by test id.

### Priority 3: Labels and Placeholders
```python
page.get_by_label("Category")
page.get_by_placeholder("Search for products")
```
Use for: Form inputs, only when no test id exists. Check the real label or placeholder text in `index.html` first; do not guess it.

### Priority 4: Element IDs
```python
page.locator("#account")
page.locator("#suggest")
```
Use for: Containers with explicit, stable IDs. Prefer `get_by_test_id` over raw IDs.

### Priority 5: CSS Classes (Last Resort)
```python
t(page, "section-tech").locator(".pcard")      # counting cards inside a section
page.locator(".ferr")                          # all field error messages
```
Use for: Only counting or collecting repeated elements inside a test-id scope. Classes can change with styling.

### NEVER Use
- XPath selectors (fragile, hard to read)
- Complex CSS chains (`.parent > .child:nth-child(3)`)
- Index-based selectors without filtering

---

## 3. Filtering and Scoping Patterns

### Find one row or card by its own test id
Rows and cards carry the record id in their test id, so no text filter is needed:
```python
row = t(page, "order-row-1")
card = t(page, "product-10")
```

### Scope actions to a parent
```python
row.get_by_test_id("order-link").click()
expect(row.get_by_test_id("order-status")).to_have_text("paid")
```

### Repeated controls inside a row
```python
qty = page.locator('[data-testid="cart-row-5"] [data-testid="cart-qty"]')
page.locator('[data-testid="product-%d"] [data-testid="add-to-cart"]' % product_id).first
```

### Filter by content (only when there is no id to use)
```python
t(page, "product-grid").locator(".pcard").filter(has_text="Mystery Novel").first
```

---

## 4. Assertion Patterns

### Visibility Checks
```python
expect(t(page, "banners")).to_be_visible()
expect(t(page, "search-suggestions")).to_be_hidden()
expect(t(page, "order-cancel")).to_have_count(0)     # element removed from the page
```

### URL Assertions
The shop uses hash routes, so match the end of the URL:
```python
expect(page).to_have_url(re.compile(r"#/orders$"))
expect(page).to_have_url(re.compile(r"#/orders/\d+$"))   # Regex for dynamic IDs
```

### Content Assertions
```python
expect(t(page, "message")).to_have_text("Order cancelled.")
expect(t(page, "order-total")).to_have_text("₹1,298")
expect(t(page, "list-title")).to_contain_text("Books")
```

### Numeric/Value Assertions
```python
expect(t(page, "cart-count")).to_have_text("2")
expect(t(page, "section-tech").locator(".pcard")).to_have_count(8)
```
Prefer `expect(...)` over `assert locator.count() == n`: `expect` waits, a plain `assert` does not.

### Custom Timeout for Slow Operations
```python
expect(t(page, "order-title")).to_be_visible(timeout=10000)
```

---

## 5. Test Structure Patterns

### Standard Test Structure
```python
from helpers import PASSWORD, RESET, case

@case("TC-UI-053", "Short title of what is validated",
      "Log in, add product 5 to the cart, open the cart",
      "Cart shows one row for product 5 and the badge shows 1", "P2")
def test_ui_053(page):
    # Step 1: Setup (login, navigate)
    ui_login(page)

    # Step 2: Action (interact with UI)
    add_from_list(page, 5, 1)
    page.goto("/#/cart")

    # Step 3: Assert (verify outcomes)
    expect(t(page, "cart-row-5")).to_be_visible()
```
Rules:
- The `page` fixture gives a fresh browser context and freshly reset data. Do not reset or create a browser yourself
- `expect` is provided at the top of `test_cases_ui.py`; do not import it again
- The `@case` steps and expected result are what a manual tester would read. Keep them in plain language and in step with the code

### Multi-Step Test with Comments
Use `# -- Step N: Description --` comment blocks to separate logical steps:
```python
def test_ui_054(page):
    # -- Step 1: Log in --
    ui_login(page)

    # -- Step 2: Put product 10 in the cart --
    add_from_list(page, 10, 1)

    # -- Step 3: Place the order --
    page.goto("/#/cart")
    pay(page)

    # -- Step 4: Verify the order page --
    expect(t(page, "order-title")).to_have_text("Order #1")
```

### Helper Functions (used here instead of Page Objects)

This project does not use page classes. Shared steps are plain functions at the top of `tests/test_cases_ui.py`. Reuse them before writing new steps:

| Helper | What it does |
|---|---|
| `t(page, test_id)` | Short form of `page.get_by_test_id(test_id)` |
| `ui_login(page, email="alice@example.com", name="Alice")` | Logs in through the login page and waits for the name in the header |
| `fill_shipping(page, state="Karnataka", **over)` | Fills the shipping form; pass a field to override it, e.g. `**{"ship-zip": "012345"}` |
| `pay(page, card="4111111111111111")` | From the cart page: shipping, payment, review, place order |
| `card_button(page, product_id)` | The "add to cart" button on a product card |
| `add_from_list(page, product_id, count_after)` | Adds a product from the list page and waits for the cart badge |

**Helper Rules:**
- One helper per repeated user action, not per low-level step
- Helpers take `page` as the first argument
- A helper may wait for the action to finish (as `ui_login` does); keep the test's own assertions in the test
- Add new helpers next to the existing ones in `tests/test_cases_ui.py`. Do not introduce a `pages/` folder or page classes unless asked

---

## 6. API Mocking (Route Interception)

### When to Mock
- Testing UI behavior for specific data states (e.g., empty list, an order worth ₹1,24,999, a cancelled order)
- Testing error handling (server error, server unreachable, ended session)
- Isolating frontend logic from backend state

Do not mock when the real state is easy to create: after a reset, alice already has no orders and an empty cart.

### Pattern
```python
page.route("**/orders", lambda route: route.fulfill(status=200, json=MOCK_ORDERS))
page.route("**/orders/1", lambda route: route.fulfill(status=404, json={"detail": "Order not found"}))
page.route("**/orders", lambda route: route.abort())          # server unreachable
```
Register the route before `page.goto(...)`. The API has no `/api` prefix: paths are `/orders`, `/cart`, `/products`, and errors use the shape `{"detail": "..."}`.

No existing test uses route interception yet, so check the first one you write carefully.

### Mock Data
Define mock responses as constants above the test, with the same fields the real API returns (see `order_out` in `app/main.py`):
```python
MOCK_ORDERS = [{"id": 1, "status": "paid", "subtotal": 124999, "discount": 0, "total": 124999,
                "coupon_code": None, "created_at": "2026-10-11T04:00:05", "shipping": None, "items": []}]
```

---

## 7. Test Data and Users

Data is reset to the seed state before every test, so IDs are predictable: the first order in a test is always order #1.

### Test Users
| User  | Email             | Password    | Purpose          |
|-------|-------------------|-------------|------------------|
| Alice | alice@example.com | Password123 | Primary tester   |
| Bob   | bob@example.com   | Password123 | Cross-user tests |

Use `PASSWORD` from `tests/helpers.py`; do not type the password into tests.

### Useful seed data
| Item | Use |
|---|---|
| Product 8 | Out of stock |
| Product 10 | Only 2 units |
| Card `4111111111111111` | Payment succeeds |
| Card `4000000000000002` | Payment declined |
| `WELCOME10`, `FLAT200` (min 1500) | Valid coupons |
| `EXPIRED50`, `DISABLED20` | Always rejected |

### Two users in one test
```python
ui_login(page)                                   # Alice
# ... place an order, note its id ...
t(page, "logout").click()
ui_login(page, "bob@example.com", "Bob")
page.goto("/#/orders/1")
expect(t(page, "message")).to_have_text("Order not found")
```
A second tab in the same session: `tab = page.context.new_page()`.

---

## 8. Dynamic Data Handling

### Unique Test Data
Because every test starts from a reset, fixed data is safe and preferred. Generate unique values only for data the test itself creates more than once, such as sign-up emails:
```python
email = "user%d@example.com" % int(time.time() * 1000)   # needs "import time" at the top of the file
```
Never depend on data left behind by another test.

---

## 9. Wait Strategies

### DO: Use auto-waiting with expect
```python
expect(t(page, "user-name")).to_have_text("Alice")     # Auto-waits
```

### DO: Wait for the page content after navigation
The shop is a single page with hash routes, so `page.goto("/#/orders")` returns before the view is drawn. Wait for an element of the new view:
```python
page.goto("/#/orders")
expect(t(page, "orders-table")).to_be_visible()
```

### DON'T: Use arbitrary sleeps
```python
# BAD - Never do this
page.wait_for_timeout(2000)
time.sleep(2)
```

### Exception: Proving that something does NOT happen
A short fixed wait is acceptable only before asserting an absence, where there is nothing to wait for:
```python
box.fill("m")                          # one character: suggestions must stay closed
page.wait_for_timeout(500)
expect(t(page, "search-suggestions")).to_be_hidden()
```
The existing tests do this in a few places (for example the suggestion and phone-width checks). Keep such waits at 500 ms or less and add a comment saying what is being ruled out.

---

## 10. Debugging Tips

### Messages in Assertions
```python
assert status == 401, "The old session still works on the server after logging out"
assert not problems, "Actual: " + "; ".join(problems)
```
The text after the comma becomes the "Actual result" in the report, so write it for a tester to read.

### Run Single Test
```bash
pytest tests/test_cases_ui.py -k test_ui_023
```

### Run and Stop at the First Failure, Showing Prints
```bash
pytest tests/test_cases_ui.py -x -s
```

### Watch the Browser
The `browser` fixture launches headless. To watch a run, temporarily change `pw.chromium.launch()` in `tests/conftest.py` to `pw.chromium.launch(headless=False, slow_mo=300)` and change it back before finishing.

### View the Report
Open `test-report/test_cases.csv`. A partial run only updates the cases that ran.

### Before running pytest
Run `unset DATABASE_URL` first. The API tests in the same suite reset whatever database that variable points to.

---

## 11. Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | Do Instead |
|-------------|-------------|-----------|
| `page.wait_for_timeout(N)` to wait for something to appear | Flaky, wastes time | Use `expect(...).to_be_visible()` |
| `page.locator('div > span:nth-child(2)')` | Fragile CSS path | Use `data-testid` |
| `page.goto("http://127.0.0.1:8000/...")` | Hits the developer's shop and MySQL data, not the test server | Use relative paths: `page.goto("/#/orders")` |
| `assert locator.count() == 3` or `assert locator.inner_text() == "..."` right after an action | Does not wait; fails on a slow render | `expect(locator).to_have_count(3)` / `.to_have_text(...)` |
| Test without `@case(...)` or with a reused ID | Missing or overwritten in the report | Add `@case` with the next free `TC-UI` number |
| `@pytest.mark.skip` or a filter such as `-k` left in | Skips other tests | Remove before finishing |
| No assertions after action | Test passes but proves nothing | Always assert outcomes |
| Shared state between tests | Order-dependent failures | Each test self-contained: login → action → assert |
| Weakening an assertion to make a failing case pass | Hides a defect in the shop | Report the defect; a failing documented case is a finding |
| Testing implementation details | Breaks on refactor | Test user-visible behavior |
