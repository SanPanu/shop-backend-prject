"""Documented browser test cases, run with Playwright against a live copy of the shop.
They are skipped when Playwright or its Chromium browser is not installed."""
import re

import pytest

from helpers import PASSWORD, case

expect = None  # set when Playwright is available


@pytest.fixture(autouse=True)
def _playwright_expect(page):
    global expect
    from playwright.sync_api import expect as e

    expect = e
    yield
    assert page.js_errors == [], "JavaScript errors on the page: %s" % page.js_errors


def t(page, test_id):
    return page.get_by_test_id(test_id)


def ui_login(page, email="alice@example.com", name="Alice"):
    page.goto("/#/login")
    t(page, "login-email").fill(email)
    t(page, "login-password").fill(PASSWORD)
    t(page, "login-submit").click()
    expect(t(page, "user-name")).to_have_text(name)


ADDRESS = {"ship-name": "Asha Rao", "ship-line1": "12 MG Road", "ship-line2": "Flat 4B", "ship-city": "Bengaluru", "ship-zip": "560001"}


def fill_shipping(page, state="Karnataka", **over):
    for field, value in dict(ADDRESS, **over).items():
        t(page, field).fill(value)
    t(page, "ship-state").select_option(state)


def place_order(page, card="4111111111111111"):
    """From a filled shipping form: continue, enter the card, continue to review and place the order."""
    t(page, "to-payment").click()
    t(page, "card-number").fill(card)
    t(page, "to-review").click()
    t(page, "place-order").click()


def pay(page, card="4111111111111111"):
    """From the cart page: go through shipping, payment and review, then place the order."""
    t(page, "checkout-start").click()
    fill_shipping(page)
    place_order(page, card)


def card_button(page, product_id):
    return page.locator('[data-testid="product-%d"] [data-testid="add-to-cart"]' % product_id).first


def add_from_list(page, product_id, count_after):
    page.goto("/#/list")
    card_button(page, product_id).click()
    expect(t(page, "cart-count")).to_have_text(str(count_after))


# ---------------------------------------------------------------- browsing
@case("TC-UI-001", "Home page shows banners, product strips and all categories", "Open the home page",
      "4 banners, 3 product strips with 8 products each, 11 category tabs with 'For You' active", "P1")
def test_ui_001(page):
    page.goto("/")
    expect(page.locator('[data-testid^="banner-"].banner')).to_have_count(4)
    for section in ["section-tech", "section-style", "section-living"]:
        expect(t(page, section).locator(".pcard")).to_have_count(8)
    expect(t(page, "category-bar").locator("a")).to_have_count(11)
    expect(t(page, "cat-for-you")).to_have_class("active")
    expect(t(page, "category-bar").locator("a.active")).to_have_count(1)


@case("TC-UI-002", "Banner carousel controls", "On the home page: click next, click previous, click the third dot",
      "The highlighted dot follows: 2nd, then 1st; the third dot becomes active after clicking it (on a wide screen it may stop at the last scroll position)")
def test_ui_002(page):
    page.goto("/")
    dots = t(page, "banner-dot")
    expect(dots.nth(0)).to_have_class("on")
    t(page, "banner-next").click()
    expect(dots.nth(1)).to_have_class("on")
    t(page, "banner-prev").click()
    expect(dots.nth(0)).to_have_class("on")
    page.set_viewport_size({"width": 600, "height": 800})  # one banner per view, so every dot is reachable
    dots.nth(2).click()
    expect(dots.nth(2)).to_have_class("on")


@case("TC-UI-003", "Category tab filters the catalogue", "Click the Books tab, then the Toys tab",
      "Title and results match the category (2 products each) and only that tab is highlighted", "P1")
def test_ui_003(page):
    page.goto("/")
    for slug, title, ids in [("books", "Books", [29, 30]), ("toys", "Toys", [23, 24])]:
        t(page, "cat-" + slug).click()
        expect(t(page, "list-title")).to_have_text(title)
        expect(t(page, "result-count")).to_have_text("2 products")
        for i in ids:
            expect(t(page, "product-%d" % i)).to_be_visible()
        expect(t(page, "cat-" + slug)).to_have_class("active")
        expect(t(page, "category-bar").locator("a.active")).to_have_count(1)


@case("TC-UI-004", "Header search", "1. Search for 'running'\n2. Search for 'zzzz'\n3. Search for spaces only",
      "1: 3 products and a 'Results for' title. 2: '0 products' and a no-results message. 3: all 30 products", "P1")
def test_ui_004(page):
    page.goto("/")
    box = t(page, "header-search")
    box.fill("running")
    box.press("Enter")
    expect(t(page, "result-count")).to_have_text("3 products")
    expect(t(page, "list-title")).to_contain_text("running")
    box.fill("zzzz")
    box.press("Enter")
    expect(t(page, "result-count")).to_have_text("0 products")
    expect(t(page, "no-results")).to_be_visible()
    box.fill("   ")
    box.press("Enter")
    expect(t(page, "result-count")).to_have_text("30 products")


@case("TC-UI-005", "Filters work, are kept in the address, and can be cleared",
      "1. On All products set Category Sports, Max price 2000, Sort low to high, Apply\n2. Reload the page\n3. Click Clear",
      "1: 3 products, cheapest first, address contains the filters. 2: same results and the filter fields still show the values. 3: 30 products", "P1")
def test_ui_005(page):
    page.goto("/#/list")
    t(page, "filter-category").select_option("sports")
    t(page, "filter-max-price").fill("2000")
    t(page, "filter-sort").select_option("price_asc")
    t(page, "filter-apply").click()
    expect(t(page, "result-count")).to_have_text("3 products")
    for param in ["category=sports", "max_price=2000", "sort=price_asc"]:
        expect(page).to_have_url(re.compile(param))
    page.reload()
    expect(t(page, "result-count")).to_have_text("3 products")
    expect(t(page, "filter-category")).to_have_value("sports")
    expect(t(page, "filter-max-price")).to_have_value("2000")
    expect(t(page, "filter-sort")).to_have_value("price_asc")
    prices = t(page, "product-grid").get_by_test_id("product-price").all_inner_texts()
    assert prices == ["₹799", "₹1,499", "₹1,899"], prices
    t(page, "filter-clear").click()
    expect(t(page, "result-count")).to_have_text("30 products")


@case("TC-UI-006", "Product card shows price, list price, discount and stock",
      "On All products look at Smartphone X1 (id 11) and Bluetooth Speaker (id 8)",
      "X1: ₹49,999, struck-through ₹55,999, '11% OFF', '9 in stock', button enabled. Speaker: 'Out of stock', button disabled", "P1")
def test_ui_006(page):
    page.goto("/#/list")
    x1 = t(page, "product-11")
    expect(x1.get_by_test_id("product-price")).to_have_text("₹49,999")
    expect(x1.get_by_test_id("product-mrp")).to_have_text("₹55,999")
    expect(x1.get_by_test_id("product-mrp")).to_have_css("text-decoration-line", "line-through")
    expect(x1.get_by_test_id("product-discount")).to_have_text("11% OFF")
    expect(x1.get_by_test_id("product-stock")).to_have_text("9 in stock")
    expect(x1.get_by_test_id("add-to-cart")).to_be_enabled()
    sp = t(page, "product-8")
    expect(sp.get_by_test_id("product-stock")).to_have_text("Out of stock")
    expect(sp.get_by_test_id("add-to-cart")).to_be_disabled()


@case("TC-UI-007", "Product page", "1. Click 'Smartphone X1' in the list\n2. Open /#/p/8 (out of stock)\n3. Open /#/p/999",
      "1: name, ₹49,999, 11% OFF, 9 in stock, Mobiles link. 2: Out of stock, quantity and button disabled. 3: 'Product not found' message", "P1")
def test_ui_007(page):
    page.goto("/#/list")
    t(page, "product-11").get_by_test_id("product-name").click()
    expect(t(page, "detail-name")).to_have_text("Smartphone X1")
    expect(t(page, "detail-price")).to_have_text("₹49,999")
    expect(t(page, "detail-discount")).to_have_text("11% OFF")
    expect(t(page, "detail-stock")).to_have_text("9 in stock")
    expect(t(page, "detail-category")).to_have_text("Mobiles")
    page.goto("/#/p/8")
    expect(t(page, "detail-stock")).to_have_text("Out of stock")
    expect(t(page, "detail-add")).to_be_disabled()
    expect(t(page, "detail-qty")).to_be_disabled()
    page.goto("/#/p/999")
    expect(t(page, "message")).to_have_text("Product not found")


# ---------------------------------------------------------------- account
@case("TC-UI-008", "Adding to cart while logged out asks for login, then returns",
      "Logged out, open product 10, set quantity 2, click Add to cart; log in",
      "Login page with 'Please log in first.'; after login the same product page is shown again", "P1")
def test_ui_008(page):
    page.goto("/#/p/10")
    t(page, "detail-qty").fill("2")
    t(page, "detail-add").click()
    expect(t(page, "login-page")).to_be_visible()
    expect(t(page, "message")).to_have_text("Please log in first.")
    t(page, "login-email").fill("alice@example.com")
    t(page, "login-password").fill(PASSWORD)
    t(page, "login-submit").click()
    expect(t(page, "detail-name")).to_have_text("Steel Water Bottle")
    expect(t(page, "user-name")).to_have_text("Alice")


@case("TC-UI-009", "Login and logout", "1. Log in with a wrong password\n2. Log in correctly\n3. Log out",
      "1: 'Wrong email or password' under the password field, still on the login page. 2: header shows Alice. 3: header shows Login / Sign Up", "P1")
def test_ui_009(page):
    page.goto("/#/login")
    t(page, "login-email").fill("alice@example.com")
    t(page, "login-password").fill("wrong")
    t(page, "login-submit").click()
    expect(t(page, "error-login-password")).to_have_text("Wrong email or password")
    expect(t(page, "message")).to_be_hidden()
    expect(t(page, "login-page")).to_be_visible()
    t(page, "login-password").fill(PASSWORD)
    t(page, "login-submit").click()
    expect(t(page, "user-name")).to_have_text("Alice")
    token = page.evaluate("localStorage.getItem('token')")
    with page.expect_response("**/auth/logout"):  # the server-side logout is sent in the background
        t(page, "logout").click()
    expect(t(page, "nav-login")).to_be_visible()
    status = page.request.get("/me", headers={"Authorization": "Bearer " + token}).status
    assert status == 401, "The old session still works on the server after logging out"


@case("TC-UI-010", "Show and hide password", "On the login page type a password and click the eye button twice",
      "The password becomes readable, then hidden again")
def test_ui_010(page):
    page.goto("/#/login")
    t(page, "login-password").fill("Secret123")
    expect(t(page, "login-password")).to_have_attribute("type", "password")
    t(page, "toggle-password").click()
    expect(t(page, "login-password")).to_have_attribute("type", "text")
    expect(t(page, "login-password")).to_have_value("Secret123")
    t(page, "toggle-password").click()
    expect(t(page, "login-password")).to_have_attribute("type", "password")


@case("TC-UI-011", "Remember me", "1. Log in with Remember me unticked and open the shop in a new tab\n2. Log out, log in with it ticked, open a new tab",
      "1: the new tab is logged out. 2: the new tab is logged in as Alice")
def test_ui_011(page):
    page.goto("/#/login")
    t(page, "login-email").fill("alice@example.com")
    t(page, "login-password").fill(PASSWORD)
    t(page, "login-remember").uncheck()
    t(page, "login-submit").click()
    expect(t(page, "user-name")).to_have_text("Alice")
    tab = page.context.new_page()
    tab.goto("/")
    expect(tab.get_by_test_id("nav-login")).to_be_visible()
    tab.close()
    t(page, "logout").click()
    ui_login(page)
    tab = page.context.new_page()
    tab.goto("/")
    expect(tab.get_by_test_id("user-name")).to_have_text("Alice")
    tab.close()


@case("TC-UI-012", "Sign up", "1. Type passwords 'abc', 'Abcdef12', 'Abcdef12!xyz' and watch the meter\n2. Enter a different confirm password and submit\n3. Fix it and submit\n4. Log out and sign up again with the same email",
      "1: Weak, Medium, Strong. 2: 'Passwords do not match' under the confirm field. 3: logged in under the new name. 4: 'This email is already registered. Log in instead' under the email field", "P1")
def test_ui_012(page):
    page.goto("/#/signup")
    t(page, "register-name").fill("Test User")
    t(page, "register-email").fill("tester@example.com")
    for pw, label in [("abc", "Weak"), ("Abcdef12", "Medium"), ("Abcdef12!xyz", "Strong")]:
        t(page, "register-password").fill(pw)
        expect(t(page, "password-strength")).to_have_text(label)
    t(page, "register-confirm").fill("something else")
    t(page, "register-submit").click()
    expect(t(page, "error-register-confirm")).to_have_text("Passwords do not match")
    t(page, "register-confirm").fill("Abcdef12!xyz")
    t(page, "register-submit").click()
    expect(t(page, "user-name")).to_have_text("Test User")
    t(page, "logout").click()
    page.goto("/#/signup")
    t(page, "register-name").fill("Again")
    t(page, "register-email").fill("tester@example.com")
    t(page, "register-password").fill("Abcdef12")
    t(page, "register-confirm").fill("Abcdef12")
    t(page, "register-submit").click()
    expect(t(page, "error-register-email")).to_have_text("This email is already registered. Log in instead")


@case("TC-UI-013", "Sign-up shows a plain message under every field that is wrong",
      "Open Sign Up and click Create Account with every field empty. Then type 'ab' as the password",
      "Four messages at once, each under its own field: 'Enter your full name', 'Enter your email address', 'Create a password', 'Enter your password again'. "
      "The cursor moves to the first wrong field. No technical text anywhere and nothing in the top banner. The password message changes to "
      "'Password must be at least 8 characters' while typing", "P1")
def test_ui_013(page):
    page.goto("/#/signup")
    t(page, "register-submit").click()
    expected = {"error-register-name": "Enter your full name", "error-register-email": "Enter your email address",
                "error-register-password": "Create a password", "error-register-confirm": "Enter your password again"}
    for test_id, text in expected.items():
        expect(t(page, test_id)).to_have_text(text)
    expect(t(page, "register-name")).to_be_focused()
    expect(t(page, "register-name")).to_have_attribute("aria-invalid", "true")
    expect(t(page, "message")).to_be_hidden()
    shown = " ".join(page.locator(".ferr").all_inner_texts())
    assert not re.search(r"pattern|\^|\\s|String should|loc|body", shown), "Technical text shown to the shopper: %r" % shown
    t(page, "register-password").fill("ab")
    expect(t(page, "error-register-password")).to_have_text("Password must be at least 8 characters")


@case("TC-UI-014", "A name containing HTML is shown as text, not run", "Sign up with the name <img src=x onerror=window.__xss=1> and look at the header",
      "The header shows the name as typed; no image element is created and no script runs", "P1")
def test_ui_014(page):
    name = "<img src=x onerror=window.__xss=1>"
    page.goto("/#/signup")
    t(page, "register-name").fill(name)
    t(page, "register-email").fill("xss@example.com")
    t(page, "register-password").fill("Abcdef12")
    t(page, "register-confirm").fill("Abcdef12")
    t(page, "register-submit").click()
    expect(t(page, "user-name")).to_have_text(name)
    page.wait_for_timeout(300)  # give an injected onerror handler time to run, so its absence means something
    assert page.evaluate("window.__xss") is None and page.locator("#account img").count() == 0


@case("TC-UI-015", "Cart and Orders need a login", "Logged out, open /#/cart, then /#/orders; log in",
      "Each time the login page with 'Please log in first.'; after login the Orders page opens")
def test_ui_015(page):
    for url in ["/#/cart", "/#/orders"]:
        page.goto(url)
        expect(t(page, "login-page")).to_be_visible()
        expect(t(page, "message")).to_have_text("Please log in first.")
    t(page, "login-email").fill("alice@example.com")
    t(page, "login-password").fill(PASSWORD)
    t(page, "login-submit").click()
    expect(t(page, "orders-empty")).to_be_visible()


@case("TC-UI-016", "Expired session is handled", "Log in, end the session on the server (POST /auth/logout with the same token), then open the Cart",
      "Login page with 'Your session has ended. Please log in again.'; header shows Login / Sign Up")
def test_ui_016(page):
    ui_login(page)
    token = page.evaluate("localStorage.getItem('token')")
    assert page.request.post("/auth/logout", headers={"Authorization": "Bearer " + token}).status == 200
    t(page, "nav-cart").click()
    expect(t(page, "login-page")).to_be_visible()
    expect(t(page, "message")).to_have_text("Your session has ended. Please log in again.")
    expect(t(page, "nav-login")).to_be_visible()


# ---------------------------------------------------------------- cart, coupon, checkout, orders
@case("TC-UI-017", "Cart badge counts units, on every page", "Log in. Add product 5 from the list twice and product 9 once. Visit home, a product page and the cart",
      "Badge shows 1, 2, then 3 and stays 3 on every page; 'Added to cart.' is shown after each add", "P1")
def test_ui_017(page):
    ui_login(page)
    page.goto("/#/list")
    for product, count in [(5, 1), (5, 2), (9, 3)]:
        card_button(page, product).click()
        expect(t(page, "cart-count")).to_have_text(str(count))
        expect(t(page, "message")).to_have_text("Added to cart.")
    for url in ["/", "/#/p/1", "/#/cart"]:
        page.goto(url)
        expect(t(page, "cart-count")).to_have_text("3")


@case("TC-UI-018", "Cart page: change quantity and remove",
      "Cart has product 5 x1 and product 10 x1. 1. Set product 5 to 3\n2. Set product 10 to 5\n3. Set product 5 to 0\n4. Remove product 10\n5. Remove product 5",
      "1: line ₹1,497, subtotal ₹2,146. 2: 'Only 2 in stock' under that row's quantity, which goes back to 1. 3: 'Quantity must be at least 1' under that row's quantity, which goes back to 3; totals unchanged. 4: subtotal ₹1,497. 5: empty-cart message, badge 0", "P1")
def test_ui_018(page):
    ui_login(page)
    add_from_list(page, 5, 1)
    add_from_list(page, 10, 2)
    page.goto("/#/cart")
    q5 = page.locator('[data-testid="cart-row-5"] [data-testid="cart-qty"]')
    q10 = page.locator('[data-testid="cart-row-10"] [data-testid="cart-qty"]')
    q5.fill("3")
    q5.press("Tab")
    expect(page.locator('[data-testid="cart-row-5"] [data-testid="cart-line-total"]')).to_have_text("₹1,497")
    expect(t(page, "cart-subtotal")).to_have_text("₹2,146")
    q10.fill("5")
    q10.press("Tab")
    expect(t(page, "cart-row-10").get_by_test_id("error-cart-qty")).to_have_text("Only 2 in stock")
    expect(q10).to_have_value("1")
    expect(t(page, "cart-row-5").get_by_test_id("error-cart-qty")).to_have_count(0)  # only the row that is wrong
    q5.fill("0")
    q5.press("Tab")
    expect(t(page, "cart-row-5").get_by_test_id("error-cart-qty")).to_have_text("Quantity must be at least 1")
    expect(q5).to_have_value("3")
    expect(t(page, "message")).to_be_hidden()
    expect(t(page, "cart-subtotal")).to_have_text("₹2,146")
    page.locator('[data-testid="cart-row-10"] [data-testid="cart-remove"]').click()
    expect(t(page, "cart-subtotal")).to_have_text("₹1,497")
    page.locator('[data-testid="cart-row-5"] [data-testid="cart-remove"]').click()
    expect(t(page, "cart-empty")).to_be_visible()
    expect(t(page, "cart-count")).to_have_text("0")


@case("TC-UI-019", "Coupons on the cart page",
      "Cart: product 3 (₹1,499). 1. Apply EXPIRED50\n2. Apply FLAT200\n3. Apply welcome10\n4. Click Remove on the coupon",
      "1: 'Coupon has expired' under the code field. 2: a message about the ₹1,500 minimum under the code field (and 'Enter a coupon code' if it is empty). 3: discount −₹149, total ₹1,350, 'Coupon WELCOME10 applied.' 4: discount −₹0, total ₹1,499", "P1")
def test_ui_019(page):
    ui_login(page)
    add_from_list(page, 3, 1)
    page.goto("/#/cart")
    t(page, "coupon-code").fill("EXPIRED50")
    t(page, "coupon-apply").click()
    expect(t(page, "error-coupon-code")).to_have_text("Coupon has expired")
    t(page, "coupon-code").fill("FLAT200")
    t(page, "coupon-apply").click()
    expect(t(page, "error-coupon-code")).to_have_text("Coupon needs a minimum order of 1500")
    expect(t(page, "cart-total")).to_have_text("₹1,499")
    t(page, "coupon-code").fill("")
    t(page, "coupon-apply").click()
    expect(t(page, "error-coupon-code")).to_have_text("Enter a coupon code")
    t(page, "coupon-code").fill("welcome10")
    t(page, "coupon-apply").click()
    expect(t(page, "message")).to_have_text("Coupon WELCOME10 applied.")
    expect(t(page, "cart-discount")).to_have_text("−₹149")
    expect(t(page, "cart-total")).to_have_text("₹1,350")
    t(page, "coupon-remove").click()
    expect(t(page, "cart-discount")).to_have_text("−₹0")
    expect(t(page, "cart-total")).to_have_text("₹1,499")


@case("TC-UI-020", "An applied coupon is dropped when the cart falls below its minimum",
      "Cart: products 3 and 9 (₹1,798). Apply FLAT200 (total ₹1,598). Remove product 9",
      "The coupon is removed with a message saying why; total is ₹1,499 with no discount")
def test_ui_020(page):
    ui_login(page)
    add_from_list(page, 3, 1)
    add_from_list(page, 9, 2)
    page.goto("/#/cart")
    t(page, "coupon-code").fill("FLAT200")
    t(page, "coupon-apply").click()
    expect(t(page, "cart-total")).to_have_text("₹1,598")
    page.locator('[data-testid="cart-row-9"] [data-testid="cart-remove"]').click()
    expect(t(page, "message")).to_have_text("Coupon FLAT200 removed: Coupon needs a minimum order of 1500")
    expect(t(page, "cart-total")).to_have_text("₹1,499")
    expect(t(page, "cart-discount")).to_have_text("−₹0")


@case("TC-UI-021", "An applied coupon survives a page refresh", "Cart: product 3. Apply WELCOME10 (total ₹1,350). Reload the page",
      "The coupon is still applied and the total is still ₹1,350")
def test_ui_021(page):
    ui_login(page)
    add_from_list(page, 3, 1)
    page.goto("/#/cart")
    t(page, "coupon-code").fill("WELCOME10")
    t(page, "coupon-apply").click()
    expect(t(page, "cart-total")).to_have_text("₹1,350")
    page.reload()
    expect(t(page, "cart-subtotal")).to_have_text("₹1,499")
    total = t(page, "cart-total").inner_text()
    assert total == "₹1,350", "Actual: after reload the total is %s and the coupon is gone, with no message to the shopper" % total


@case("TC-UI-022", "Checkout: payment step and placing the order",
      "Cart: product 7 with WELCOME10. Proceed to checkout, fill shipping, continue. 1. Continue with card '123'\n2. Use 4000000000000002, continue, place order\n3. Use '4111 1111 1111 1111', continue, place order",
      "1: 'Card number must be 16 digits (you entered 3)' under the card field, still on Payment. 2: back on Payment with 'Payment declined. Try another card' under the card field; cart unchanged. 3: order page 'Order #1', paid, total ₹1,800, 'Order placed.', badge 0", "P1")
def test_ui_022(page):
    ui_login(page)
    add_from_list(page, 7, 1)
    page.goto("/#/cart")
    t(page, "coupon-code").fill("WELCOME10")
    t(page, "coupon-apply").click()
    expect(t(page, "cart-total")).to_have_text("₹1,800")
    t(page, "checkout-start").click()
    expect(t(page, "summary-total")).to_have_text("₹1,800")
    fill_shipping(page)
    t(page, "to-payment").click()
    expect(t(page, "step-payment")).to_have_class("active")
    t(page, "card-number").fill("123")
    t(page, "to-review").click()
    expect(t(page, "error-card-number")).to_have_text("Card number must be 16 digits (you entered 3)")
    expect(t(page, "step-payment")).to_have_class("active")
    t(page, "card-number").fill("4111-1111-1111-111x")
    expect(t(page, "error-card-number")).to_have_text("Card number can contain digits only")
    t(page, "card-number").fill("4000000000000002")
    t(page, "to-review").click()
    expect(t(page, "review-card")).to_have_text("Card ending 0002")
    t(page, "place-order").click()
    expect(t(page, "error-card-number")).to_have_text("Payment declined. Try another card")
    expect(t(page, "step-payment")).to_have_class("active")
    expect(t(page, "cart-count")).to_have_text("1")
    t(page, "card-number").fill("4111 1111 1111 1111")
    t(page, "to-review").click()
    t(page, "place-order").click()
    expect(t(page, "order-title")).to_have_text("Order #1")
    expect(t(page, "order-status")).to_have_text("paid")
    expect(t(page, "order-discount")).to_have_text("−₹199")
    expect(t(page, "order-total")).to_have_text("₹1,800")
    expect(t(page, "message")).to_have_text("Order placed.")
    expect(t(page, "cart-count")).to_have_text("0")


@case("TC-UI-023", "Orders list and cancelling an order",
      "Place an order for product 10 x2, open Orders, open the order, click Cancel order, then open product 10",
      "List shows the order as paid; after cancel the status is cancelled, the Cancel button is gone, and product 10 shows '2 in stock' again", "P1")
def test_ui_023(page):
    ui_login(page)
    page.goto("/#/p/10")
    t(page, "detail-qty").fill("2")
    t(page, "detail-add").click()
    expect(t(page, "cart-count")).to_have_text("2")
    page.goto("/#/cart")
    pay(page)
    expect(t(page, "order-title")).to_have_text("Order #1")
    page.goto("/#/p/10")
    expect(t(page, "detail-stock")).to_have_text("Out of stock")
    t(page, "nav-orders").click()
    row = t(page, "order-row-1")
    expect(row.get_by_test_id("order-status")).to_have_text("paid")
    expect(row.get_by_test_id("order-total")).to_have_text("₹1,298")
    row.get_by_test_id("order-link").click()
    t(page, "order-cancel").click()
    expect(t(page, "order-status")).to_have_text("cancelled")
    expect(t(page, "message")).to_have_text("Order cancelled.")
    expect(t(page, "order-cancel")).to_have_count(0)
    page.goto("/#/p/10")
    expect(t(page, "detail-stock")).to_have_text("2 in stock")


@case("TC-UI-024", "Opening an order that does not exist", "Log in and open /#/orders/999", "'Order not found' message")
def test_ui_024(page):
    ui_login(page)
    page.goto("/#/orders/999")
    expect(t(page, "message")).to_have_text("Order not found")


# ---------------------------------------------------------------- general
@case("TC-UI-025", "Browser Back and Forward buttons", "Home, click Books, click the first product, press Back twice, press Forward",
      "Back: Books list, then home. Forward: Books list again")
def test_ui_025(page):
    page.goto("/")
    t(page, "cat-books").click()
    expect(t(page, "list-title")).to_have_text("Books")
    t(page, "product-29").get_by_test_id("product-name").click()
    expect(t(page, "detail-name")).to_have_text("Mystery Novel")
    page.go_back()
    expect(t(page, "list-title")).to_have_text("Books")
    page.go_back()
    expect(t(page, "banners")).to_be_visible()
    page.go_forward()
    expect(t(page, "list-title")).to_have_text("Books")


@case("TC-UI-026", "Pages fit a phone screen", "At 375 px width open home, All products, a product page, (logged in) the cart, checkout and orders, then login and sign up",
      "No page scrolls sideways")
def test_ui_026(page):
    ui_login(page)
    add_from_list(page, 5, 1)
    page.set_viewport_size({"width": 375, "height": 740})
    pages = {"/": "banners", "/#/list": "result-count", "/#/p/14": "detail-name", "/#/cart": "cart-table",
             "/#/checkout": "checkout-page", "/#/orders": "orders-empty", "/#/login": "login-page", "/#/signup": "signup-page"}
    for url, marker in pages.items():
        page.goto(url)
        expect(t(page, marker)).to_be_visible()   # measure only once the page is drawn
        over = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert over <= 0, "%s is %d px wider than the screen" % (url, over)


@case("TC-UI-027", "Browser tab title names the current page", "Open home, then a product page, then the cart",
      "The tab title changes with the page: 'Practice Shop', 'Smartphone X1 – Practice Shop', 'Cart – Practice Shop'", "P3")
def test_ui_027(page):
    ui_login(page)
    for url, marker, title in [("/", "banners", "Practice Shop"), ("/#/p/11", "detail-name", "Smartphone X1 – Practice Shop"),
                               ("/#/cart", "cart-empty", "Cart – Practice Shop")]:
        page.goto(url)
        expect(t(page, marker)).to_be_visible()
        expect(page).to_have_title(title)


@case("TC-UI-028", "The chat assistant is hidden while it is switched off", "Open the home page (server started without AGENT_ENABLED)",
      "No 'Shopping assistant' button and no chat panel are visible")
def test_ui_028(page):
    page.goto("/")
    expect(t(page, "banners")).to_be_visible()
    page.wait_for_timeout(400)  # the agent status check is asynchronous: rule out the button appearing late
    expect(t(page, "chat-open")).to_be_hidden()
    expect(t(page, "chat-panel")).to_be_hidden()


@case("TC-UI-029", "Automation ids are unique on each page", "On home, All products, a product page, login and sign up, collect every data-testid outside repeated product cards, table rows and banner controls",
      "No id appears twice, so a test can address each control without ambiguity")
def test_ui_029(page):
    problems = []
    pages = {"/": "banners", "/#/list": "result-count", "/#/p/11": "detail-name", "/#/login": "login-page", "/#/signup": "signup-page"}
    for url, marker in pages.items():
        page.goto(url)
        expect(t(page, marker)).to_be_visible()   # collect ids only once the page is drawn
        dupes = page.evaluate("""() => {
            const seen = {};
            document.querySelectorAll('[data-testid]').forEach(el => {
                if (el.closest('.pcard, tr, .banner, .dots, .strip-head, .carousel > button, .field')) return;
                seen[el.dataset.testid] = (seen[el.dataset.testid] || 0) + 1;
            });
            return Object.keys(seen).filter(k => seen[k] > 1);
        }""")
        if dupes:
            problems.append("%s: %s" % (url, ", ".join(sorted(dupes))))
    assert not problems, "Actual: duplicated ids found. " + "; ".join(problems)


# ---------------------------------------------------------------- checkout steps
@case("TC-UI-030", "Checkout page layout and order summary",
      "Cart: product 5 x2 and product 9 x1 with WELCOME10. Click Proceed to checkout",
      "Step 1 Shipping is active. Email is pre-filled with the account email, country is India. Summary lists both items, subtotal ₹1,297, shipping ₹0, discount −₹129, total ₹1,168", "P1")
def test_ui_030(page):
    ui_login(page)
    page.goto("/#/list")
    for product, count in [(5, 1), (5, 2), (9, 3)]:
        card_button(page, product).click()
        expect(t(page, "cart-count")).to_have_text(str(count))
    page.goto("/#/cart")
    t(page, "coupon-code").fill("WELCOME10")
    t(page, "coupon-apply").click()
    expect(t(page, "cart-total")).to_have_text("₹1,168")
    t(page, "checkout-start").click()
    expect(t(page, "step-shipping")).to_have_class("active")
    expect(t(page, "ship-email")).to_have_value("alice@example.com")
    expect(t(page, "ship-country")).to_have_value("India")
    expect(t(page, "summary-item-5").get_by_test_id("summary-line-total")).to_have_text("₹998")
    expect(t(page, "summary-item-9").get_by_test_id("summary-line-total")).to_have_text("₹299")
    expect(t(page, "summary-subtotal")).to_have_text("₹1,297")
    expect(t(page, "summary-shipping")).to_have_text("₹0")
    expect(t(page, "summary-discount")).to_have_text("−₹129")
    expect(t(page, "summary-total")).to_have_text("₹1,168")


@case("TC-UI-031", "Shipping form shows a message under every field that is wrong",
      "On the Shipping step: 1. Clear the email and click Continue with everything empty\n2. Type a bad email\n3. Try PIN codes '12a', '1234' and '012345'\n4. Fill everything correctly and continue",
      "1: six messages at once, each under its own field (email, name, address, city, state, PIN); address line 2 has none; cursor in the email field. "
      "2: 'Enter a valid email address, like name@example.com'. 3: 'PIN code can contain digits only', then 'Enter a valid 6-digit PIN code' twice. "
      "4: each message disappears as its field is corrected, and the form moves to Payment", "P1")
def test_ui_031(page):
    ui_login(page)
    add_from_list(page, 5, 1)
    page.goto("/#/checkout")
    t(page, "ship-email").fill("")
    t(page, "to-payment").click()
    expected = {"error-ship-email": "Enter your email address", "error-ship-name": "Enter your full name",
                "error-ship-line1": "Enter your house number and street", "error-ship-city": "Enter your city",
                "error-ship-state": "Select your state", "error-ship-zip": "Enter your PIN code"}
    for test_id, text in expected.items():
        expect(t(page, test_id)).to_have_text(text)
    expect(t(page, "error-ship-line2")).to_have_count(0)
    expect(t(page, "ship-email")).to_be_focused()
    expect(t(page, "step-shipping")).to_have_class("active")
    expect(t(page, "message")).to_be_hidden()
    t(page, "ship-email").fill("not-an-email")
    expect(t(page, "error-ship-email")).to_have_text("Enter a valid email address, like name@example.com")
    t(page, "ship-email").fill("asha@example.com")
    expect(t(page, "error-ship-email")).to_have_count(0)
    for pin, text in [("12a", "PIN code can contain digits only"), ("1234", "Enter a valid 6-digit PIN code"), ("012345", "Enter a valid 6-digit PIN code")]:
        t(page, "ship-zip").fill(pin)
        expect(t(page, "error-ship-zip")).to_have_text(text)
    fill_shipping(page)
    for test_id in expected:
        expect(t(page, test_id)).to_have_count(0)
    expect(t(page, "ship-name")).not_to_have_attribute("aria-invalid", "true")
    t(page, "to-payment").click()
    expect(t(page, "step-payment")).to_have_class("active")
    expect(t(page, "step-shipping")).to_have_class("done")


@case("TC-UI-032", "Review step shows what was entered, and Edit goes back without losing it",
      "Fill shipping and card 4111111111111111 and reach Review. Click Edit on the address, change the city to Mysuru, continue to Review again",
      "Review shows name, both address lines, city, state, PIN, country, email and 'Card ending 1111'. After the edit the form still holds the other values, the card is still filled, and Review shows Mysuru", "P1")
def test_ui_032(page):
    ui_login(page)
    add_from_list(page, 5, 1)
    page.goto("/#/checkout")
    fill_shipping(page)
    t(page, "to-payment").click()
    t(page, "card-number").fill("4111111111111111")
    t(page, "to-review").click()
    expect(t(page, "step-review")).to_have_class("active")
    for text in ["Asha Rao", "12 MG Road", "Flat 4B", "Bengaluru, Karnataka 560001", "India"]:
        expect(t(page, "review-address")).to_contain_text(text)
    expect(t(page, "review-email")).to_have_text("alice@example.com")
    expect(t(page, "review-card")).to_have_text("Card ending 1111")
    t(page, "edit-shipping").click()
    expect(t(page, "ship-line2")).to_have_value("Flat 4B")
    expect(t(page, "ship-state")).to_have_value("Karnataka")
    t(page, "ship-city").fill("Mysuru")
    t(page, "to-payment").click()
    expect(t(page, "card-number")).to_have_value("4111111111111111")
    t(page, "to-review").click()
    expect(t(page, "review-address")).to_contain_text("Mysuru, Karnataka 560001")


@case("TC-UI-033", "The order keeps the delivery address", "Place an order through checkout and open the order page",
      "The order page shows a 'Deliver to' block with the name, address, PIN and email that were entered", "P1")
def test_ui_033(page):
    ui_login(page)
    add_from_list(page, 5, 1)
    page.goto("/#/cart")
    pay(page)
    expect(t(page, "order-title")).to_have_text("Order #1")
    for text in ["Asha Rao", "12 MG Road", "Flat 4B", "Bengaluru, Karnataka 560001", "alice@example.com"]:
        expect(t(page, "order-shipping")).to_contain_text(text)


@case("TC-UI-034", "Save this information for next time",
      "1. Order with the box ticked, add another item and open checkout\n2. Order again with the box unticked, add another item and open checkout",
      "1: the shipping form is pre-filled with the saved address. 2: the form is empty again (email shows the account email)")
def test_ui_034(page):
    ui_login(page)
    add_from_list(page, 5, 1)
    page.goto("/#/cart")
    pay(page)
    expect(t(page, "order-title")).to_have_text("Order #1")
    add_from_list(page, 9, 1)
    page.goto("/#/checkout")
    expect(t(page, "ship-name")).to_have_value("Asha Rao")
    expect(t(page, "ship-zip")).to_have_value("560001")
    expect(t(page, "ship-state")).to_have_value("Karnataka")
    t(page, "ship-save").uncheck()
    place_order(page)
    expect(t(page, "order-title")).to_have_text("Order #2")
    add_from_list(page, 9, 1)
    page.goto("/#/checkout")
    expect(t(page, "ship-name")).to_have_value("")
    expect(t(page, "ship-email")).to_have_value("alice@example.com")


@case("TC-UI-035", "Checkout needs a login and a non-empty cart", "1. Logged out, open /#/checkout\n2. Log in with an empty cart and open /#/checkout",
      "1: login page. 2: sent to the cart with 'Your cart is empty.'")
def test_ui_035(page):
    page.goto("/#/checkout")
    expect(t(page, "login-page")).to_be_visible()
    t(page, "login-email").fill("alice@example.com")
    t(page, "login-password").fill(PASSWORD)
    t(page, "login-submit").click()
    expect(t(page, "cart-empty")).to_be_visible()
    expect(t(page, "message")).to_have_text("Your cart is empty.")


@case("TC-UI-036", "Checkout total follows the cart", "At the Payment step, go Back to Cart, change product 5 from 1 to 3, and proceed to checkout again",
      "Summary total is ₹1,497 and the shipping details typed earlier are still filled in")
def test_ui_036(page):
    ui_login(page)
    add_from_list(page, 5, 1)
    page.goto("/#/checkout")
    fill_shipping(page)
    t(page, "to-payment").click()
    expect(t(page, "summary-total")).to_have_text("₹499")
    t(page, "back-to-cart").click()
    q = page.locator('[data-testid="cart-row-5"] [data-testid="cart-qty"]')
    q.fill("3")
    q.press("Tab")
    expect(t(page, "cart-subtotal")).to_have_text("₹1,497")
    t(page, "checkout-start").click()
    expect(t(page, "summary-total")).to_have_text("₹1,497")
    t(page, "back-to-shipping").click()
    expect(t(page, "ship-name")).to_have_value("Asha Rao")


@case("TC-UI-053", "Placing an order lands on its order page and empties the cart",
      "Cart: product 9 x1. Open /#/checkout, fill shipping, continue, card 4111111111111111, continue, place order, then open the cart",
      "Page URL is /#/orders/1 with 'Order placed.', 'Order #1', status paid, total ₹299, badge 0. The cart page shows 'Your cart is empty.'", "P0")
def test_ui_053(page):
    # -- Step 1: Log in and put one product in the cart --
    ui_login(page)
    add_from_list(page, 9, 1)

    # -- Step 2: Shipping, Payment and Review --
    page.goto("/#/checkout")
    expect(t(page, "step-shipping")).to_have_class("active")
    fill_shipping(page)
    place_order(page)

    # -- Step 3: The new order's page is shown --
    expect(page).to_have_url(re.compile(r"#/orders/1$"))
    expect(t(page, "message")).to_have_text("Order placed.")
    expect(t(page, "order-title")).to_have_text("Order #1")
    expect(t(page, "order-status")).to_have_text("paid")
    expect(t(page, "order-total")).to_have_text("₹299")
    expect(t(page, "cart-count")).to_have_text("0")

    # -- Step 4: The cart is empty --
    page.goto("/#/cart")
    expect(t(page, "cart-empty")).to_be_visible()


@case("TC-UI-054", "After a second order the Orders link shows it first",
      "Order product 5 x1, then product 9 x1. On the second order's page click Orders in the header",
      "Orders page shows '2 order(s)'; the first row is order #2 (₹299, paid), the second row is order #1 (₹499, paid)", "P1")
def test_ui_054(page):
    # -- Step 1: Place two orders --
    ui_login(page)
    add_from_list(page, 5, 1)
    page.goto("/#/cart")
    pay(page)
    expect(t(page, "order-title")).to_have_text("Order #1")
    add_from_list(page, 9, 1)
    page.goto("/#/cart")
    pay(page)
    expect(t(page, "order-title")).to_have_text("Order #2")

    # -- Step 2: Open Orders from the header --
    t(page, "nav-orders").click()
    expect(page).to_have_url(re.compile(r"#/orders$"))
    expect(t(page, "orders-count")).to_have_text("2 order(s)")

    # -- Step 3: Newest order is the first row --
    rows = t(page, "orders-table").get_by_role("row")   # row 0 is the header
    expect(rows).to_have_count(3)
    expect(rows.nth(1)).to_have_attribute("data-testid", "order-row-2")
    expect(rows.nth(2)).to_have_attribute("data-testid", "order-row-1")
    expect(t(page, "order-row-2").get_by_test_id("order-total")).to_have_text("₹299")
    expect(t(page, "order-row-1").get_by_test_id("order-total")).to_have_text("₹499")
    for row_id in ["order-row-1", "order-row-2"]:
        expect(t(page, row_id).get_by_test_id("order-status")).to_have_text("paid")


@case("TC-UI-055", "Quantity 1 carries through from the product page to the order",
      "Open product 5 (Cotton T-Shirt, ₹499), add it with quantity 1, open the cart, check out with card 4111111111111111, then open product 5 again",
      "Product 5 starts at '50 in stock'. Cart row, checkout summary and order page all show quantity 1 and ₹499; order subtotal ₹499, discount −₹0, total ₹499; product 5 shows '49 in stock'", "P1")
def test_ui_055(page):
    # -- Step 1: Add one unit from the product page --
    ui_login(page)
    page.goto("/#/p/5")
    expect(t(page, "detail-price")).to_have_text("₹499")
    expect(t(page, "detail-stock")).to_have_text("50 in stock")
    expect(t(page, "detail-qty")).to_have_value("1")
    t(page, "detail-add").click()
    expect(t(page, "cart-count")).to_have_text("1")

    # -- Step 2: Cart and checkout summary --
    page.goto("/#/cart")
    expect(page.locator('[data-testid="cart-row-5"] [data-testid="cart-qty"]')).to_have_value("1")
    expect(t(page, "cart-row-5").get_by_test_id("cart-line-total")).to_have_text("₹499")
    t(page, "checkout-start").click()
    expect(t(page, "summary-item-5")).to_contain_text("Qty: 1 × ₹499")
    expect(t(page, "summary-item-5").get_by_test_id("summary-line-total")).to_have_text("₹499")
    expect(t(page, "summary-total")).to_have_text("₹499")

    # -- Step 3: Place the order --
    fill_shipping(page)
    place_order(page)
    expect(t(page, "order-title")).to_have_text("Order #1")

    # -- Step 4: Order page shows one line with quantity 1 --
    rows = t(page, "order-items").get_by_role("row")   # row 0 is the header
    expect(rows).to_have_count(2)
    expect(rows.nth(1).get_by_role("cell")).to_have_text(["Cotton T-Shirt", "₹499", "1", "₹499"])
    expect(t(page, "order-subtotal")).to_have_text("₹499")
    expect(t(page, "order-discount")).to_have_text("−₹0")
    expect(t(page, "order-total")).to_have_text("₹499")

    # -- Step 5: Stock went down by one --
    page.goto("/#/p/5")
    expect(t(page, "detail-stock")).to_have_text("49 in stock")


@case("TC-UI-056", "A quantity chosen on the product page reaches the cart",
      "Log in, open product 5 (Cotton T-Shirt, ₹499), set quantity 3, click Add to cart, then open the cart",
      "'Added to cart.' appears, the page stays on product 5 and the badge shows 3. The cart has one row for product 5 with price ₹499, "
      "quantity 3 and line total ₹1,497; subtotal ₹1,497; header shows '3 item(s)'", "P0")
def test_ui_056(page):
    # -- Step 1: Add three units from the product page --
    ui_login(page)
    page.goto("/#/p/5")
    t(page, "detail-qty").fill("3")
    t(page, "detail-add").click()
    expect(t(page, "message")).to_have_text("Added to cart.")
    expect(t(page, "cart-count")).to_have_text("3")
    expect(page).to_have_url(re.compile(r"#/p/5$"))

    # -- Step 2: The cart shows the same quantity and totals --
    page.goto("/#/cart")
    row = t(page, "cart-row-5")
    expect(row.get_by_role("cell")).to_have_text(["Cotton T-Shirt", "₹499", "", "₹1,497", "Remove"])   # quantity is an input
    expect(row.get_by_test_id("cart-qty")).to_have_value("3")
    expect(t(page, "cart-table").get_by_role("row")).to_have_count(2)   # header row + product 5
    expect(t(page, "cart-subtotal")).to_have_text("₹1,497")
    expect(t(page, "cart-units")).to_have_text("3 item(s)")


@case("TC-UI-057", "Adding to the cart does not change the stock shown",
      "Log in, open product 10 (2 in stock), add 1 to the cart, then reload the page",
      "Before and after the reload the page shows '2 in stock' and Add to cart stays enabled; the badge shows 1", "P2")
def test_ui_057(page):
    # -- Step 1: Open product 10 --
    ui_login(page)
    page.goto("/#/p/10")
    expect(t(page, "detail-stock")).to_have_text("2 in stock")

    # -- Step 2: Add one unit; the stock shown stays the same --
    t(page, "detail-add").click()
    expect(t(page, "cart-count")).to_have_text("1")
    expect(t(page, "detail-stock")).to_have_text("2 in stock")
    expect(t(page, "detail-add")).to_be_enabled()

    # -- Step 3: Reload and check again --
    page.reload()
    expect(t(page, "detail-name")).to_have_text("Steel Water Bottle")
    expect(t(page, "detail-stock")).to_have_text("2 in stock")
    expect(t(page, "detail-add")).to_be_enabled()
    expect(t(page, "cart-count")).to_have_text("1")


@case("TC-UI-058", "A product added from its card shows on the cart page and links back",
      "Log in, add Wireless Earbuds (product 7, ₹1,999) from All products, open the cart, click the product name",
      "Cart row shows 'Wireless Earbuds', ₹1,999, quantity 1, line total ₹1,999 and a Remove button; subtotal ₹1,999. "
      "The name opens the Wireless Earbuds product page", "P1")
def test_ui_058(page):
    # -- Step 1: Add from the product card --
    ui_login(page)
    add_from_list(page, 7, 1)

    # -- Step 2: Check the cart row --
    page.goto("/#/cart")
    row = t(page, "cart-row-7")
    expect(row.get_by_role("cell")).to_have_text(["Wireless Earbuds", "₹1,999", "", "₹1,999", "Remove"])   # quantity is an input
    expect(row.get_by_test_id("cart-qty")).to_have_value("1")
    expect(row.get_by_test_id("cart-remove")).to_be_visible()
    expect(t(page, "cart-subtotal")).to_have_text("₹1,999")

    # -- Step 3: The name links back to the product page --
    row.get_by_test_id("cart-name").click()
    expect(page).to_have_url(re.compile(r"#/p/7$"))
    expect(t(page, "detail-name")).to_have_text("Wireless Earbuds")


# ---------------------------------------------------------------- page styling round
@case("TC-UI-037", "Product page: breadcrumb and 'More in this category'",
      "Open Smart Watch (id 13). Read the breadcrumb and the 'More in Electronics' strip. Click Laptop Pro 15 in the strip. Then open Mystery Novel (id 29)",
      "Breadcrumb reads Home > Electronics > Smart Watch. The strip lists the 4 other electronics products, not the Smart Watch itself. Clicking opens that product. Mystery Novel shows exactly 1 related book")
def test_ui_037(page):
    page.goto("/#/p/13")
    for part in ["Home", "Electronics", "Smart Watch"]:
        expect(t(page, "crumbs")).to_contain_text(part)
    strip = t(page, "section-related")
    expect(strip).to_contain_text("More in Electronics")
    expect(strip.locator(".pcard")).to_have_count(4)
    expect(strip.get_by_test_id("product-13")).to_have_count(0)
    strip.get_by_test_id("product-12").get_by_test_id("product-name").click()
    expect(t(page, "detail-name")).to_have_text("Laptop Pro 15")
    expect(t(page, "section-related").get_by_test_id("product-13")).to_have_count(1)
    page.goto("/#/p/29")
    expect(t(page, "section-related").locator(".pcard")).to_have_count(1)
    expect(t(page, "section-related").get_by_test_id("product-30")).to_be_visible()


@case("TC-UI-038", "Page headers and empty states on the inner pages",
      "Logged in with nothing in the cart: open Cart, then Orders. Add product 5 x2 and product 9, open Cart. Open the Sports category",
      "Empty cart and empty orders each show a message with a button that leads to the home page. The cart header shows '3 item(s)'. The Sports header has an 'All products' button that shows all 30 products")
def test_ui_038(page):
    ui_login(page)
    page.goto("/#/cart")
    expect(t(page, "cart-empty")).to_contain_text("Your cart is empty.")
    t(page, "cart-empty").get_by_role("link").click()
    expect(t(page, "banners")).to_be_visible()
    page.goto("/#/orders")
    expect(t(page, "orders-empty")).to_contain_text("You have no orders yet.")
    page.goto("/#/list")
    for product, count in [(5, 1), (5, 2), (9, 3)]:
        card_button(page, product).click()
        expect(t(page, "cart-count")).to_have_text(str(count))
    page.goto("/#/cart")
    expect(t(page, "cart-units")).to_have_text("3 item(s)")
    t(page, "cat-sports").click()
    expect(t(page, "result-count")).to_have_text("5 products")
    t(page, "hero-all").click()
    expect(t(page, "result-count")).to_have_text("30 products")
    expect(t(page, "list-title")).to_have_text("All products")


# ---------------------------------------------------------------- search suggestions
@case("TC-UI-039", "Suggestions appear while typing in the search box",
      "On the home page type 'm', then 'mob'. Read the list. Then type 'zzzz'. Then clear the box",
      "One letter: no list. 'mob': a Categories row 'Mobiles' (3 products), product rows Phone Case, Smartphone X1 and Budget Phone M2 with prices, "
      "and 'See all 3 results'. 'zzzz': 'No products match'. Empty box: the list closes", "P1")
def test_ui_039(page):
    page.goto("/")
    box = t(page, "header-search")
    box.fill("m")
    page.wait_for_timeout(500)  # one character: rule out the suggestion list opening late
    expect(t(page, "search-suggestions")).to_be_hidden()
    box.fill("mob")
    expect(t(page, "search-suggestions")).to_be_visible()
    expect(t(page, "suggest-category")).to_have_count(1)
    expect(t(page, "suggest-category")).to_contain_text("Mobiles")
    expect(t(page, "suggest-category")).to_contain_text("3 products")
    expect(t(page, "suggest-product")).to_have_count(3)
    for i, (name, price) in enumerate([("Phone Case", "₹299"), ("Smartphone X1", "₹49,999"), ("Budget Phone M2", "₹9,999")]):
        expect(t(page, "suggest-product").nth(i)).to_contain_text(name)
        expect(t(page, "suggest-product").nth(i)).to_contain_text(price)
    expect(t(page, "suggest-all")).to_contain_text("See all 3 results")
    expect(box).to_have_attribute("aria-expanded", "true")
    box.fill("zzzz")
    expect(t(page, "suggest-empty")).to_contain_text("No products match")
    box.fill("")
    expect(t(page, "search-suggestions")).to_be_hidden()


@case("TC-UI-040", "Choosing a suggestion with the mouse",
      "Type 'mob' and click the Mobiles category row. Type 'sma' and click Smartphone X1. Type 'mob' and click 'See all'",
      "Category row: the Mobiles page with 3 products. Product row: the Smartphone X1 page. See all: results page for 'mob' with 3 products. "
      "Each time the list closes and the search box is emptied", "P1")
def test_ui_040(page):
    page.goto("/")
    box = t(page, "header-search")
    box.fill("mob")
    t(page, "suggest-category").click()
    expect(t(page, "list-title")).to_have_text("Mobiles")
    expect(t(page, "result-count")).to_have_text("3 products")
    expect(t(page, "search-suggestions")).to_be_hidden()
    expect(box).to_have_value("")
    box.fill("sma")
    t(page, "suggest-product").filter(has_text="Smartphone X1").click()
    expect(t(page, "detail-name")).to_have_text("Smartphone X1")
    box.fill("mob")
    t(page, "suggest-all").click()
    expect(t(page, "result-count")).to_have_text("3 products")
    expect(t(page, "list-title")).to_contain_text("mob")
    expect(t(page, "search-suggestions")).to_be_hidden()


@case("TC-UI-041", "Using suggestions with the keyboard",
      "Type 'mob'. Press Down twice, then Enter. Type 'mob' and press Enter without choosing. Type 'mob', press Escape. Type 'mob' and click elsewhere on the page",
      "Down twice highlights the first product (Phone Case) and Enter opens it. Enter without a choice runs the search (3 products). "
      "Escape closes the list and keeps the text. Clicking elsewhere closes the list")
def test_ui_041(page):
    page.goto("/")
    box = t(page, "header-search")
    box.fill("mob")
    expect(t(page, "suggest-product")).to_have_count(3)
    box.press("ArrowDown")
    expect(t(page, "suggest-category")).to_have_class(re.compile(r"\bon\b"))
    box.press("ArrowDown")
    expect(t(page, "suggest-product").first).to_have_class(re.compile(r"\bon\b"))
    box.press("Enter")
    expect(t(page, "detail-name")).to_have_text("Phone Case")
    box.fill("mob")
    expect(t(page, "suggest-product")).to_have_count(3)
    box.press("Enter")
    expect(t(page, "result-count")).to_have_text("3 products")
    expect(t(page, "search-suggestions")).to_be_hidden()
    box.fill("mob")
    expect(t(page, "search-suggestions")).to_be_visible()
    box.press("Escape")
    expect(t(page, "search-suggestions")).to_be_hidden()
    expect(box).to_have_value("mob")
    box.fill("mobi")
    expect(t(page, "search-suggestions")).to_be_visible()
    # plain footer text: outside the search box and never covered by the open list
    page.get_by_role("contentinfo").get_by_text("Practice Shop is a test target").click()
    expect(t(page, "search-suggestions")).to_be_hidden()


@case("TC-UI-042", "Suggestions keep up with fast typing and fit a phone screen",
      "Type 'mobiles' one letter at a time without pausing. Then at 375 px width type 'sho'",
      "The list ends up showing matches for 'mobiles' only (no leftovers from 'mo' or 'mob'). On the phone the list stays inside the screen")
def test_ui_042(page):
    page.goto("/")
    box = t(page, "header-search")
    box.press_sequentially("mobiles", delay=30)
    expect(t(page, "suggest-all")).to_contain_text("“mobiles”")
    expect(t(page, "suggest-product")).to_have_count(3)
    page.set_viewport_size({"width": 375, "height": 740})
    box.fill("sho")
    expect(t(page, "suggest-product")).to_have_count(5)
    edges = page.evaluate("(() => { const r = document.getElementById('suggest').getBoundingClientRect(); return [r.left, r.right, window.innerWidth]; })()")
    assert edges[0] >= 0 and edges[1] <= edges[2], "Suggestion list runs off the screen: %s" % edges
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0


# ---------------------------------------------------------------- filter panel
@case("TC-UI-043", "Filter fields are aligned",
      "Open All products at 1366 px. Measure every field in the filter panel (search, category, min price, max price, availability) and the Apply button",
      "All fields are the same height. Search, category, availability and Apply share the same left and right edges. "
      "Min and max price sit on one row, are the same width, and together span the same edges")
def test_ui_043(page):
    page.goto("/#/list")
    expect(t(page, "result-count")).to_have_text("30 products")
    box = lambda test_id: t(page, test_id).bounding_box()
    full = [box(x) for x in ["filter-search", "filter-category", "filter-stock", "filter-apply"]]
    lo, hi = box("filter-min-price"), box("filter-max-price")
    heights = {round(b["height"]) for b in full[:3] + [lo, hi]}
    assert len(heights) == 1, "Field heights differ: %s" % heights
    lefts = {round(b["x"]) for b in full}
    rights = {round(b["x"] + b["width"]) for b in full}
    assert len(lefts) == 1 and len(rights) == 1, "Fields are not aligned: left edges %s, right edges %s" % (lefts, rights)
    assert round(lo["y"]) == round(hi["y"]) and abs(lo["width"] - hi["width"]) <= 1, "Min and max price are not a matching pair"
    assert round(lo["x"]) in lefts and round(hi["x"] + hi["width"]) in rights, "The price row does not line up with the other fields"


@case("TC-UI-044", "Price range filter and quick price buttons",
      "1. Min 500, Max 1000, Apply\n2. Min 2000, Max 100, Apply\n3. Clear, click 'Under ₹500'\n4. Click 'Under ₹500' again\n5. Click '₹10,000 +'",
      "1: 6 products, all priced ₹500 to ₹1,000, address has both values. 2: 'Maximum price cannot be less than the minimum price' under the price fields and results unchanged. "
      "3: 6 products, the button is highlighted, Max shows 499. 4: all 30 products, nothing highlighted. 5: 4 products, Min shows 10000", "P1")
def test_ui_044(page):
    page.goto("/#/list")
    t(page, "filter-min-price").fill("500")
    t(page, "filter-max-price").fill("1000")
    t(page, "filter-apply").click()
    expect(t(page, "result-count")).to_have_text("6 products")
    for param in ["min_price=500", "max_price=1000"]:
        expect(page).to_have_url(re.compile(param))
    prices = [int(x.replace("₹", "").replace(",", "")) for x in t(page, "product-grid").get_by_test_id("product-price").all_inner_texts()]
    assert prices and all(500 <= x <= 1000 for x in prices), prices
    t(page, "filter-min-price").fill("2000")
    t(page, "filter-max-price").fill("100")
    t(page, "filter-apply").click()
    expect(t(page, "error-filter-max-price")).to_have_text("Maximum price cannot be less than the minimum price")
    expect(t(page, "result-count")).to_have_text("6 products")
    t(page, "filter-clear").click()
    expect(t(page, "result-count")).to_have_text("30 products")
    t(page, "price-chip-1").click()
    expect(t(page, "result-count")).to_have_text("6 products")
    expect(t(page, "price-chip-1")).to_have_class("on")
    expect(t(page, "filter-max-price")).to_have_value("499")
    t(page, "price-chip-1").click()
    expect(t(page, "result-count")).to_have_text("30 products")
    expect(t(page, "price-chip-1")).not_to_have_class("on")
    t(page, "price-chip-4").click()
    expect(t(page, "result-count")).to_have_text("4 products")
    expect(t(page, "filter-min-price")).to_have_value("10000")


@case("TC-UI-045", "Dropdown filters apply at once, and active filters can be removed one at a time",
      "On All products choose Category Sports (no Apply click), then Sort 'Price: low to high', then set Max 2000 and Apply. Remove the price tag, then the category tag",
      "Choosing Sports shows 5 products straight away and a 'Sports' tag. Sorting reorders at once and keeps the category. With Max 2000: 3 products and tags "
      "'Sports' and 'Up to ₹2,000'. Removing the price tag: 5 products, still sorted. Removing the category tag: 30 products and no tags; 'Clear all' is hidden", "P1")
def test_ui_045(page):
    page.goto("/#/list")
    expect(t(page, "filter-clear")).to_be_hidden()
    expect(t(page, "active-filters")).to_have_count(0)
    t(page, "filter-category").select_option("sports")
    expect(t(page, "result-count")).to_have_text("5 products")
    expect(t(page, "active-chip-category")).to_contain_text("Sports")
    expect(t(page, "list-title")).to_have_text("Sports")
    t(page, "filter-sort").select_option("price_asc")
    expect(t(page, "product-grid").locator(".pcard").first).to_have_attribute("data-testid", "product-28")
    for param in ["category=sports", "sort=price_asc"]:
        expect(page).to_have_url(re.compile(param))
    t(page, "filter-max-price").fill("2000")
    t(page, "filter-apply").click()
    expect(t(page, "result-count")).to_have_text("3 products")
    expect(t(page, "active-chip-price")).to_contain_text("Up to ₹2,000")
    t(page, "active-chip-price").click()
    expect(t(page, "result-count")).to_have_text("5 products")
    expect(t(page, "filter-max-price")).to_have_value("")
    expect(t(page, "filter-sort")).to_have_value("price_asc")
    t(page, "active-chip-category").click()
    expect(t(page, "result-count")).to_have_text("30 products")
    expect(t(page, "active-filters")).to_have_count(0)
    expect(t(page, "filter-clear")).to_be_hidden()


@case("TC-UI-046", "Filters on a phone",
      "At 375 px width open All products, tap 'Show / hide', choose Availability 'Out of stock'",
      "The panel starts collapsed so products are visible first; the button opens it; choosing a filter shows 1 product with an 'Out of stock' tag, "
      "and the panel stays open. Nothing scrolls sideways")
def test_ui_046(page):
    page.set_viewport_size({"width": 375, "height": 740})
    page.goto("/#/list")
    expect(t(page, "result-count")).to_have_text("30 products")
    expect(t(page, "filter-category")).to_be_hidden()
    t(page, "filters-toggle").click()
    expect(t(page, "filter-category")).to_be_visible()
    t(page, "filter-stock").select_option("false")
    expect(t(page, "result-count")).to_have_text("1 product")
    expect(t(page, "active-chip-in_stock")).to_contain_text("Out of stock")
    expect(t(page, "filter-category")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0


# ---------------------------------------------------------------- field-level validation
@case("TC-UI-047", "A field is checked as soon as the customer leaves it",
      "On Login: type 'alice@' in the email and press Tab. Correct it to 'alice@example.com'. Click into the password field and out again without typing. Click Login with both fields empty",
      "Leaving the email shows 'Enter a valid email address, like name@example.com' under it with a red border; the message disappears while the address is corrected. "
      "An untouched empty field shows nothing until Login is clicked; then 'Enter your email address' and 'Enter your password' appear under their fields", "P1")
def test_ui_047(page):
    page.goto("/#/login")
    t(page, "login-email").fill("alice@")
    t(page, "login-email").press("Tab")
    expect(t(page, "error-login-email")).to_have_text("Enter a valid email address, like name@example.com")
    expect(t(page, "login-email")).to_have_attribute("aria-invalid", "true")
    described_by = t(page, "login-email").get_attribute("aria-describedby")
    assert page.locator("#" + described_by).inner_text() == "Enter a valid email address, like name@example.com"  # read out by screen readers
    t(page, "login-email").fill("alice@example.com")
    expect(t(page, "error-login-email")).to_have_count(0)
    t(page, "login-password").click()
    t(page, "login-email").click()
    expect(t(page, "error-login-password")).to_have_count(0)
    t(page, "login-email").fill("")
    t(page, "login-submit").click()
    expect(t(page, "error-login-email")).to_have_text("Enter your email address")
    expect(t(page, "error-login-password")).to_have_text("Enter your password")
    expect(t(page, "message")).to_be_hidden()
    expect(t(page, "login-page")).to_be_visible()


@case("TC-UI-048", "Quantity on the product page is checked at the field",
      "Logged in, open product 10 (2 in stock). Add with quantity 0, then empty, then 1.5, then 5, then 2",
      "'Quantity must be at least 1', 'Enter a quantity', 'Quantity must be a whole number', then 'Only 2 in stock', each under the quantity field with nothing added to the cart. "
      "Quantity 2 is added: badge shows 2, 'Added to cart.' appears and the field message is gone")
def test_ui_048(page):
    ui_login(page)
    page.goto("/#/p/10")
    for value, text in [("0", "Quantity must be at least 1"), ("", "Enter a quantity"), ("1.5", "Quantity must be a whole number"), ("5", "Only 2 in stock")]:
        t(page, "detail-qty").fill(value)
        t(page, "detail-add").click()
        expect(t(page, "error-detail-qty")).to_have_text(text)
        expect(t(page, "cart-count")).to_have_text("0")
    expect(t(page, "message")).to_be_hidden()
    t(page, "detail-qty").fill("2")
    expect(t(page, "error-detail-qty")).to_have_count(0)
    t(page, "detail-add").click()
    expect(t(page, "cart-count")).to_have_text("2")
    expect(t(page, "message")).to_have_text("Added to cart.")


@case("TC-UI-049", "Sign-up rules are reported one field at a time with the right wording",
      "On Sign Up enter, leaving each field with Tab: name of spaces only; email 'a@b'; password of 8 spaces; confirm 'different'. Then change the password to 'Abcdef12' and the confirm to 'Abcdef12'",
      "Name: 'Enter your full name'. Email: 'Enter a valid email address, like name@example.com'. Password: 'Password cannot be only spaces'. Confirm: 'Passwords do not match'. "
      "After the password and confirm are corrected both messages disappear")
def test_ui_049(page):
    page.goto("/#/signup")
    for field, value, error, text in [
        ("register-name", "   ", "error-register-name", "Enter your full name"),
        ("register-email", "a@b", "error-register-email", "Enter a valid email address, like name@example.com"),
        ("register-password", " " * 8, "error-register-password", "Password cannot be only spaces"),
        ("register-confirm", "different", "error-register-confirm", "Passwords do not match"),
    ]:
        t(page, field).fill(value)
        t(page, field).press("Tab")
        expect(t(page, error)).to_have_text(text)
    t(page, "register-password").fill("Abcdef12")
    expect(t(page, "error-register-password")).to_have_count(0)
    expect(t(page, "error-register-confirm")).to_have_text("Passwords do not match")
    t(page, "register-confirm").fill("Abcdef12")
    expect(t(page, "error-register-confirm")).to_have_count(0)


@case("TC-UI-050", "Filter price fields are checked at the field",
      "On All products: Min 800, Max 300, Apply. Then change Min to 100",
      "'Maximum price cannot be less than the minimum price' under the price fields and results stay at 30. After Min becomes 100 the message disappears; Apply then shows the 2 products priced ₹100 to ₹300")
def test_ui_050(page):
    page.goto("/#/list")
    t(page, "filter-min-price").fill("800")
    t(page, "filter-max-price").fill("300")
    t(page, "filter-apply").click()
    expect(t(page, "error-filter-max-price")).to_have_text("Maximum price cannot be less than the minimum price")
    expect(t(page, "result-count")).to_have_text("30 products")
    expect(t(page, "message")).to_be_hidden()
    t(page, "filter-min-price").fill("100")
    expect(t(page, "error-filter-max-price")).to_have_count(0)
    t(page, "filter-apply").click()
    expect(t(page, "result-count")).to_have_text("2 products")


@case("TC-UI-051", "The first click on a submit button is never lost",
      "On Sign Up type 'sangamesh@' as the email and 'abc' as the password, then click Create Account with the mouse while the cursor is still in the password field. "
      "On Login type 'alice@' and click Login the same way",
      "The single click submits the form: all four sign-up fields show their messages (name, email, password, confirm). On Login both fields show a message. "
      "A message appearing under the field being left must not move the button away from the click", "P1")
def test_ui_051(page):
    page.goto("/#/signup")
    t(page, "register-email").fill("sangamesh@")
    t(page, "register-password").fill("abc")
    t(page, "register-submit").click()
    for test_id, text in [("error-register-name", "Enter your full name"), ("error-register-email", "Enter a valid email address, like name@example.com"),
                          ("error-register-password", "Password must be at least 8 characters"), ("error-register-confirm", "Enter your password again")]:
        expect(t(page, test_id)).to_have_text(text)
    page.goto("/#/login")
    t(page, "login-email").fill("alice@")
    t(page, "login-submit").click()
    expect(t(page, "error-login-email")).to_have_text("Enter a valid email address, like name@example.com")
    expect(t(page, "error-login-password")).to_have_text("Enter your password")


@case("TC-UI-052", "Pages load without console errors or failed requests",
      "Open the home page, a category page, a product page, the login page and the sign-up page, watching the browser console and network",
      "No console errors and no failed requests on any of them. The tab shows the shop's icon and GET /favicon.ico returns 200")
def test_ui_052(page):
    problems = []
    page.on("console", lambda m: problems.append("console: " + m.text) if m.type == "error" else None)
    page.on("response", lambda r: problems.append("%s %s" % (r.status, r.url)) if r.status >= 400 else None)
    for url in ["/", "/#/list?category=sports", "/#/p/11", "/#/login", "/#/signup"]:
        page.goto(url)
        page.wait_for_timeout(500)  # rule out late console errors and failed requests from this page
    assert not problems, "Actual: " + "; ".join(problems)
    assert page.locator('link[rel="icon"]').count() == 1
    icon = page.request.get("/favicon.ico")
    assert icon.status == 200 and "svg" in icon.headers["content-type"]
