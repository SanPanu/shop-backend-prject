"""Documented API test cases. Each test asserts the behaviour a shopper or the business would expect.
A failing test here is a defect in the shop, not a broken test: read the "Actual result" in the report."""
import threading
from datetime import datetime, timedelta

import httpx

from helpers import CARD, DECLINED, PASSWORD, RESET, SHIP, add, case, login, stock

ALICE = "alice@example.com"
BOB = "bob@example.com"


def register(client, **over):
    body = {"email": "new@example.com", "name": "New User", "password": "Secret123"}
    body.update(over)
    return client.post("/auth/register", json=body)


# ====================================================================== authentication
@case("TC-AUTH-001", "Login with valid credentials", "POST /auth/login with alice@example.com / Password123",
      "200. Response has a token and the user's id, email and name, and no password data", "P1")
def test_auth_001(client):
    r = client.post("/auth/login", json={"email": ALICE, "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token"] and body["user"] == {"id": 1, "email": ALICE, "name": "Alice"}
    assert "password" not in r.text.lower()


@case("TC-AUTH-002", "Login failure does not reveal whether the email exists",
      "1. Login with a wrong password for a real user\n2. Login with an email that is not registered",
      "Both return 401 with the same message", "P1")
def test_auth_002(client):
    a = client.post("/auth/login", json={"email": ALICE, "password": "wrong-pass"})
    b = client.post("/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json() == {"detail": "Wrong email or password"}


@case("TC-AUTH-003", "Email is not case-sensitive at login", "Login as ALICE@EXAMPLE.COM", "200")
def test_auth_003(client):
    assert client.post("/auth/login", json={"email": ALICE.upper(), "password": PASSWORD}).status_code == 200


@case("TC-AUTH-004", "Register a new user", "1. POST /auth/register with a new email\n2. Call GET /me with the returned token\n3. Log in with the new credentials",
      "201 with a token; /me returns the new user; login works", "P1")
def test_auth_004(client):
    r = register(client)
    assert r.status_code == 201
    me = client.get("/me", headers={"Authorization": "Bearer " + r.json()["token"]})
    assert me.status_code == 200 and me.json()["email"] == "new@example.com" and me.json()["name"] == "New User"
    assert client.post("/auth/login", json={"email": "new@example.com", "password": "Secret123"}).status_code == 200


@case("TC-AUTH-005", "Duplicate email is rejected, ignoring letter case", "Register with Alice@Example.com (already registered as alice@example.com)",
      "409 Email already registered", "P1")
def test_auth_005(client):
    r = register(client, email="Alice@Example.com")
    assert r.status_code == 409 and r.json()["detail"] == "Email already registered"


@case("TC-AUTH-006", "Invalid email formats are rejected", "Register with: 'plain', 'a@b', '@b.com', 'a b@c.com', '' ", "422 for each")
def test_auth_006(client):
    for email in ["plain", "a@b", "@b.com", "a b@c.com", ""]:
        assert register(client, email=email).status_code == 422, "accepted invalid email %r" % email


@case("TC-AUTH-007", "Password length boundary", "1. Register with a 7-character password\n2. Register with an 8-character password",
      "7 characters: 422. 8 characters: 201")
def test_auth_007(client):
    assert register(client, password="Abcdef1").status_code == 422
    assert register(client, password="Abcdef12").status_code == 201


@case("TC-AUTH-008", "Name cannot be blank", "Register with a name made only of spaces", "422, no account created")
def test_auth_008(client):
    r = register(client, name="   ")
    assert r.status_code == 422, "Actual: %s. An account was created with a blank name" % r.status_code


@case("TC-AUTH-009", "Protected endpoints reject missing, malformed and unknown tokens",
      "Call GET /me, GET /cart, GET /orders and POST /checkout with: no header, 'Token abc', 'Bearer' and 'Bearer not-a-token'",
      "401 every time", "P1")
def test_auth_009(client):
    for headers in [{}, {"Authorization": "Token abc"}, {"Authorization": "Bearer"}, {"Authorization": "Bearer not-a-token"}]:
        for method, path in [("GET", "/me"), ("GET", "/cart"), ("GET", "/orders"), ("POST", "/checkout")]:
            r = client.request(method, path, headers=headers, json={"card_number": CARD, "shipping": SHIP} if method == "POST" else None)
            assert r.status_code == 401, "%s %s with %r returned %s" % (method, path, headers, r.status_code)


@case("TC-AUTH-010", "Name length boundary", "1. Register with a 101-character name\n2. Register with a 100-character name", "101: 422. 100: 201")
def test_auth_010(client):
    assert register(client, name="x" * 101).status_code == 422
    assert register(client, name="x" * 100).status_code == 201


@case("TC-AUTH-011", "Logging out ends the session on the server",
      "1. Log in\n2. POST /auth/logout with the token\n3. Call GET /me with the same token",
      "Logout succeeds and the old token is then rejected with 401", "P1")
def test_auth_011(client):
    h = login(client)
    r = client.post("/auth/logout", headers=h)
    assert r.status_code in (200, 204), (
        "Actual: POST /auth/logout returned %s. There is no way to end a session; a token stays valid forever" % r.status_code
    )
    assert client.get("/me", headers=h).status_code == 401
    assert client.post("/auth/logout", headers=h).status_code == 401  # already ended
    other = login(client)
    client.post("/auth/logout", headers=login(client))
    assert client.get("/me", headers=other).status_code == 200  # only that one session ends


@case("TC-AUTH-012", "Password made only of spaces is rejected", "Register with a password of 8 spaces", "422")
def test_auth_012(client):
    r = register(client, password=" " * 8)
    assert r.status_code == 422, "Actual: %s. An account was created with a blank password" % r.status_code


# ====================================================================== products
@case("TC-PROD-001", "Catalogue lists all products with complete data", "GET /products",
      "200 with 30 products; each has id, name, category, price, mrp, discount_percent, rating, reviews, stock, in_stock", "P1")
def test_prod_001(client):
    products = client.get("/products").json()
    assert len(products) == 30 and [p["id"] for p in products] == list(range(1, 31))
    need = {"id", "name", "category", "specs", "description", "price", "mrp", "discount_percent", "rating", "reviews", "image", "stock", "in_stock"}
    assert all(need <= set(p) for p in products)


@case("TC-PROD-002", "Search matches part of the name in any letter case", "GET /products?q=RUNNING and ?q=shoe",
      "RUNNING: products 1, 2, 3. shoe: products 1, 2, 3, 4", "P1")
def test_prod_002(client):
    ids = lambda q: [p["id"] for p in client.get("/products", params={"q": q}).json()]
    assert ids("RUNNING") == [1, 2, 3] and ids("shoe") == [1, 2, 3, 4]


@case("TC-PROD-003", "Category filter agrees with the category counts",
      "1. GET /categories\n2. For each category GET /products?category=<slug>\n3. GET /products?category=nonsense",
      "Each list has exactly the count from /categories and only that category; unknown category returns an empty list")
def test_prod_003(client):
    cats = client.get("/categories").json()
    assert len(cats) == 10 and sum(c["count"] for c in cats) == 30
    for c in cats:
        items = client.get("/products", params={"category": c["slug"]}).json()
        assert len(items) == c["count"] and all(p["category"] == c["slug"] for p in items), c["slug"]
    assert client.get("/products", params={"category": "nonsense"}).json() == []


@case("TC-PROD-004", "Price range limits are inclusive", "GET /products?min_price=1499&max_price=1499, then min_price=1500&max_price=1898",
      "First: only product 3 (₹1,499). Second: empty", "P1")
def test_prod_004(client):
    ids = lambda lo, hi: [p["id"] for p in client.get("/products", params={"min_price": lo, "max_price": hi}).json()]
    assert ids(1499, 1499) == [3] and ids(1500, 1898) == [] and ids(1500, 1899) == [27]


@case("TC-PROD-005", "Minimum price above maximum price", "GET /products?min_price=5000&max_price=100", "200 with an empty list")
def test_prod_005(client):
    r = client.get("/products", params={"min_price": 5000, "max_price": 100})
    assert r.status_code == 200 and r.json() == []


@case("TC-PROD-006", "Every sort option orders the list correctly", "GET /products with sort = price_asc, price_desc, name, rating, discount",
      "Lists are ordered by that field; all 30 products are still present")
def test_prod_006(client):
    get = lambda s: client.get("/products", params={"sort": s}).json()
    assert [p["price"] for p in get("price_asc")] == sorted(p["price"] for p in get("price_asc"))
    assert [p["price"] for p in get("price_desc")] == sorted((p["price"] for p in get("price_desc")), reverse=True)
    assert [p["name"] for p in get("name")] == sorted(p["name"] for p in get("name"))
    assert [p["rating"] for p in get("rating")] == sorted((p["rating"] for p in get("rating")), reverse=True)
    exact = [(p["mrp"] - p["price"]) / p["mrp"] for p in get("discount")]
    assert exact == sorted(exact, reverse=True)
    assert all(len(get(s)) == 30 for s in ["price_asc", "price_desc", "name", "rating", "discount"])


@case("TC-PROD-007", "Availability filter", "GET /products?in_stock=false, then in_stock=true",
      "false: only product 8. true: 29 products, none with stock 0")
def test_prod_007(client):
    assert [p["id"] for p in client.get("/products", params={"in_stock": False}).json()] == [8]
    live = client.get("/products", params={"in_stock": True}).json()
    assert len(live) == 29 and all(p["stock"] > 0 and p["in_stock"] for p in live)


@case("TC-PROD-008", "Invalid query parameters are rejected", "GET /products with sort=bogus, min_price=-1, max_price=abc, limit=0, limit=101, in_stock=maybe",
      "422 for each")
def test_prod_008(client):
    for params in [{"sort": "bogus"}, {"min_price": -1}, {"max_price": "abc"}, {"limit": 0}, {"limit": 101}, {"in_stock": "maybe"}]:
        assert client.get("/products", params=params).status_code == 422, params


@case("TC-PROD-009", "Discount shown matches list price and selling price", "For every product compare discount_percent with (mrp - price) / mrp",
      "discount_percent is the percentage rounded to the nearest whole number, for all 30 products", "P1")
def test_prod_009(client):
    for p in client.get("/products").json():
        assert p["discount_percent"] == round((p["mrp"] - p["price"]) * 100 / p["mrp"]), p["name"]
        assert client.get("/products/%d" % p["id"]).json() == p


@case("TC-PROD-010", "Unknown and malformed product ids", "GET /products/999, /products/0, /products/abc", "999 and 0: 404. abc: 422")
def test_prod_010(client):
    assert client.get("/products/999").status_code == 404 and client.get("/products/0").status_code == 404
    assert client.get("/products/abc").status_code == 422


@case("TC-PROD-011", "Search treats % and _ as ordinary characters", "GET /products?q=% and GET /products?q=_",
      "%: only the two products whose specs really contain a % sign (5 '100% cotton' and 26 '70% cocoa'). _: nothing. Neither acts as a wildcard")
def test_prod_011(client):
    pct = [p["id"] for p in client.get("/products", params={"q": "%"}).json()]
    und = client.get("/products", params={"q": "_"}).json()
    assert pct == [5, 26] and und == [], "Actual: q='%%' returned %s and q='_' returned %d products. They act as wildcards" % (pct, len(und))


@case("TC-PROD-012", "Search is safe against SQL injection", "GET /products?q=' OR '1'='1 and q=\"; DROP TABLE products;--",
      "200 with an empty list; the catalogue is intact afterwards", "P1")
def test_prod_012(client):
    for q in ["' OR '1'='1", '"; DROP TABLE products;--']:
        r = client.get("/products", params={"q": q})
        assert r.status_code == 200 and r.json() == []
    assert len(client.get("/products").json()) == 30


@case("TC-PROD-013", "Search ignores spaces around the search text", "GET /products?q=%20shoes%20 (a space before and after)", "Products 1, 2, 3, 4", "P3")
def test_prod_013(client):
    found = [p["id"] for p in client.get("/products", params={"q": " shoes "}).json()]
    assert found == [1, 2, 3, 4], "Actual: %r. The API does not trim the search text (the web page does)" % found


@case("TC-PROD-014", "Filters combine, and limit caps the list",
      "GET /products?category=sports&max_price=2000&sort=price_asc, then add limit=2", "Products 28, 3, 27 in that order; with limit=2: 28, 3")
def test_prod_014(client):
    params = {"category": "sports", "max_price": 2000, "sort": "price_asc"}
    assert [p["id"] for p in client.get("/products", params=params).json()] == [28, 3, 27]
    assert [p["id"] for p in client.get("/products", params=dict(params, limit=2)).json()] == [28, 3]


@case("TC-PROD-015", "Catalogue data is sane", "Check every product", "price > 0, price <= mrp, stock >= 0, rating between 0 and 5, in_stock matches stock")
def test_prod_015(client):
    for p in client.get("/products").json():
        assert 0 < p["price"] <= p["mrp"] and p["stock"] >= 0 and 0 <= p["rating"] <= 5, p
        assert p["in_stock"] == (p["stock"] > 0)


# ====================================================================== cart
@case("TC-CART-001", "Add a product to the cart", "Log in, POST /cart/items {product_id: 5, quantity: 2}, GET /cart",
      "Cart has one line: Cotton T-Shirt, unit price 499, quantity 2, line total 998; subtotal 998", "P1")
def test_cart_001(client):
    h = login(client)
    assert add(client, h, 5, 2).status_code == 200
    assert client.get("/cart", headers=h).json() == {
        "items": [{"product_id": 5, "name": "Cotton T-Shirt", "unit_price": 499, "quantity": 2, "line_total": 998}], "subtotal": 998}


@case("TC-CART-002", "Adding the same product again increases its quantity", "Add product 5 x2, then product 5 x3", "One line with quantity 5, subtotal 2495", "P1")
def test_cart_002(client):
    h = login(client)
    add(client, h, 5, 2)
    cart = add(client, h, 5, 3).json()
    assert len(cart["items"]) == 1 and cart["items"][0]["quantity"] == 5 and cart["subtotal"] == 2495


@case("TC-CART-003", "Out-of-stock product cannot be added", "Add product 8 (stock 0)", "409, cart stays empty", "P1")
def test_cart_003(client):
    h = login(client)
    r = add(client, h, 8)
    assert r.status_code == 409 and r.json()["detail"] == "Only 0 in stock"
    assert client.get("/cart", headers=h).json()["items"] == []


@case("TC-CART-004", "Cart quantity cannot exceed stock, counting what is already in the cart",
      "Product 10 has 2 units. 1. Add 3\n2. Add 2\n3. Add 1 more", "Step 1: 409. Step 2: 200. Step 3: 409 and quantity stays 2", "P1")
def test_cart_004(client):
    h = login(client)
    assert add(client, h, 10, 3).status_code == 409
    assert add(client, h, 10, 2).status_code == 200
    assert add(client, h, 10, 1).status_code == 409
    assert client.get("/cart", headers=h).json()["items"][0]["quantity"] == 2


@case("TC-CART-005", "Invalid quantities are rejected", "Add product 5 with quantity 0, -1, 1.5, 'abc' and null", "422 for each; cart stays empty")
def test_cart_005(client):
    h = login(client)
    for q in [0, -1, 1.5, "abc", None]:
        r = client.post("/cart/items", json={"product_id": 5, "quantity": q}, headers=h)
        assert r.status_code == 422, "quantity %r returned %s" % (q, r.status_code)
    assert client.get("/cart", headers=h).json()["items"] == []


@case("TC-CART-006", "Change the quantity of a cart line",
      "With product 10 x1 in the cart: 1. PUT quantity 2\n2. PUT quantity 3\n3. PUT quantity 0\n4. PUT quantity for product 1 (not in cart)",
      "1: subtotal 1298. 2: 409. 3: 422. 4: 404. Quantity stays 2", "P1")
def test_cart_006(client):
    h = login(client)
    add(client, h, 10, 1)
    put = lambda pid, q: client.put("/cart/items/%d" % pid, json={"quantity": q}, headers=h)
    assert put(10, 2).json()["subtotal"] == 1298
    assert put(10, 3).status_code == 409 and put(10, 0).status_code == 422 and put(1, 1).status_code == 404
    assert client.get("/cart", headers=h).json()["items"][0]["quantity"] == 2


@case("TC-CART-007", "Remove lines and clear the cart",
      "With products 5 and 9 in the cart: 1. DELETE product 5\n2. DELETE product 5 again\n3. DELETE /cart",
      "1: only product 9 left. 2: 404. 3: empty cart, subtotal 0", "P1")
def test_cart_007(client):
    h = login(client)
    add(client, h, 5)
    add(client, h, 9)
    assert [i["product_id"] for i in client.delete("/cart/items/5", headers=h).json()["items"]] == [9]
    assert client.delete("/cart/items/5", headers=h).status_code == 404
    assert client.delete("/cart", headers=h).json() == {"items": [], "subtotal": 0}


@case("TC-CART-008", "Each user has a separate cart", "Alice adds product 5. Bob views his cart, then tries to remove product 5",
      "Bob's cart is empty and his delete returns 404; Alice's cart is unchanged", "P1")
def test_cart_008(client):
    alice, bob = login(client), login(client, BOB)
    add(client, alice, 5)
    assert client.get("/cart", headers=bob).json()["items"] == []
    assert client.delete("/cart/items/5", headers=bob).status_code == 404
    assert len(client.get("/cart", headers=alice).json()["items"]) == 1


@case("TC-CART-009", "Unknown product cannot be added", "Add product 999, and product 'abc'", "999: 404. abc: 422")
def test_cart_009(client):
    h = login(client)
    assert add(client, h, 999).status_code == 404
    assert client.post("/cart/items", json={"product_id": "abc", "quantity": 1}, headers=h).status_code == 422


@case("TC-CART-010", "Cart is kept between logins", "Alice adds product 5, then logs in again and views the cart with the new token", "The cart still has product 5")
def test_cart_010(client):
    add(client, login(client), 5)
    assert client.get("/cart", headers=login(client)).json()["items"][0]["product_id"] == 5


# ====================================================================== coupons
@case("TC-COUP-001", "Percentage coupon", "Cart: Laptop Pro 15 (₹42,990). Validate WELCOME10", "Discount 4299, total 38691", "P1")
def test_coup_001(client):
    h = login(client)
    add(client, h, 12)
    r = client.post("/coupons/validate", json={"code": "WELCOME10"}, headers=h).json()
    assert r == {"code": "WELCOME10", "subtotal": 42990, "discount": 4299, "total": 38691}


@case("TC-COUP-002", "Coupon code ignores letter case and surrounding spaces", "Validate '  welcome10 ' with product 12 in the cart", "Accepted as WELCOME10")
def test_coup_002(client):
    h = login(client)
    add(client, h, 12)
    r = client.post("/coupons/validate", json={"code": "  welcome10 "}, headers=h)
    assert r.status_code == 200 and r.json()["code"] == "WELCOME10"


@case("TC-COUP-003", "Flat coupon needs its minimum order value",
      "1. Cart ₹1,499 (product 3): validate FLAT200\n2. Add product 9 (cart ₹1,798): validate FLAT200",
      "1: 400 with the minimum stated. 2: discount 200, total 1598. (Exactly ₹1,500 cannot be reached with the seed prices)", "P1")
def test_coup_003(client):
    h = login(client)
    add(client, h, 3)
    r = client.post("/coupons/validate", json={"code": "FLAT200"}, headers=h)
    assert r.status_code == 400 and "1500" in r.json()["detail"]
    add(client, h, 9)
    ok = client.post("/coupons/validate", json={"code": "FLAT200"}, headers=h).json()
    assert (ok["discount"], ok["total"]) == (200, 1598)


@case("TC-COUP-004", "Expired, disabled and unknown coupons are rejected with a clear reason", "Validate EXPIRED50, DISABLED20 and NOSUCH",
      "400 each, with messages: Coupon has expired / Coupon is not active / Coupon not found", "P1")
def test_coup_004(client):
    h = login(client)
    add(client, h, 12)
    for code, msg in [("EXPIRED50", "Coupon has expired"), ("DISABLED20", "Coupon is not active"), ("NOSUCH", "Coupon not found")]:
        r = client.post("/coupons/validate", json={"code": code}, headers=h)
        assert r.status_code == 400 and r.json()["detail"] == msg


@case("TC-COUP-005", "Percentage discount is a whole number of rupees and never more than the stated percentage",
      "Cart ₹499 (product 5). Validate WELCOME10 (10% = ₹49.90)", "Discount is 49 or 50 and subtotal - discount = total")
def test_coup_005(client):
    h = login(client)
    add(client, h, 5)
    r = client.post("/coupons/validate", json={"code": "WELCOME10"}, headers=h).json()
    assert r["discount"] in (49, 50) and r["subtotal"] - r["discount"] == r["total"]


@case("TC-COUP-006", "Coupon cannot be applied to an empty cart", "With an empty cart, validate WELCOME10", "400, since there is nothing to discount", "P3")
def test_coup_006(client):
    r = client.post("/coupons/validate", json={"code": "WELCOME10"}, headers=login(client))
    assert r.status_code == 400, "Actual: %s %s. The coupon is reported as valid on an empty cart" % (r.status_code, r.json())


# ====================================================================== checkout
@case("TC-CHK-001", "Successful checkout", "Cart: product 1 x2. POST /checkout with a valid card",
      "201. Order is paid with subtotal 5598, discount 0, total 5598. Stock of product 1 drops from 12 to 10. Cart is empty", "P1")
def test_chk_001(client):
    h = login(client)
    add(client, h, 1, 2)
    r = client.post("/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=h)
    assert r.status_code == 201
    o = r.json()
    assert (o["status"], o["subtotal"], o["discount"], o["total"], o["coupon_code"]) == ("paid", 5598, 0, 5598, None)
    assert stock(client, 1) == 10 and client.get("/cart", headers=h).json()["items"] == []


@case("TC-CHK-002", "Checkout with a coupon", "Cart: product 12. Checkout with coupon 'welcome10'",
      "Order has discount 4299, total 38691 and coupon_code WELCOME10", "P1")
def test_chk_002(client):
    h = login(client)
    add(client, h, 12)
    o = client.post("/checkout", json={"card_number": CARD, "coupon_code": "welcome10", "shipping": SHIP}, headers=h).json()
    assert (o["discount"], o["total"], o["coupon_code"]) == (4299, 38691, "WELCOME10")


@case("TC-CHK-003", "Checkout with an empty cart", "POST /checkout with nothing in the cart", "400 Cart is empty; no order is created", "P1")
def test_chk_003(client):
    h = login(client)
    r = client.post("/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=h)
    assert r.status_code == 400 and r.json()["detail"] == "Cart is empty" and client.get("/orders", headers=h).json() == []


@case("TC-CHK-004", "Declined card changes nothing", "Cart: product 7. Checkout with card 4000000000000002",
      "402 Payment declined. No order, stock still 15, cart still has the item", "P1")
def test_chk_004(client):
    h = login(client)
    add(client, h, 7)
    r = client.post("/checkout", json={"card_number": DECLINED, "shipping": SHIP}, headers=h)
    assert r.status_code == 402 and r.json()["detail"] == "Payment declined"
    assert client.get("/orders", headers=h).json() == [] and stock(client, 7) == 15
    assert len(client.get("/cart", headers=h).json()["items"]) == 1


@case("TC-CHK-005", "Card number format is validated", "Checkout with: 15 digits, 17 digits, letters, empty, digits with spaces, and no card field",
      "422 for each; no order is created")
def test_chk_005(client):
    h = login(client)
    add(client, h, 7)
    for card in ["4" * 15, "4" * 17, "abcdabcdabcdabcd", "", "4111 1111 1111 1111"]:
        assert client.post("/checkout", json={"card_number": card, "shipping": SHIP}, headers=h).status_code == 422, card
    assert client.post("/checkout", json={}, headers=h).status_code == 422
    assert client.get("/orders", headers=h).json() == []


@case("TC-CHK-006", "Invalid coupon at checkout stops the order", "Cart: product 7. Checkout with EXPIRED50, then with NOSUCH",
      "400 each time. No order, stock and cart unchanged", "P1")
def test_chk_006(client):
    h = login(client)
    add(client, h, 7)
    for code in ["EXPIRED50", "NOSUCH"]:
        assert client.post("/checkout", json={"card_number": CARD, "coupon_code": code, "shipping": SHIP}, headers=h).status_code == 400
    assert client.get("/orders", headers=h).json() == [] and stock(client, 7) == 15
    assert len(client.get("/cart", headers=h).json()["items"]) == 1


@case("TC-CHK-007", "Coupon minimum is checked again at checkout",
      "1. Cart ₹1,798 (products 3 and 9); FLAT200 validates\n2. Remove product 9 (cart ₹1,499)\n3. Checkout with FLAT200",
      "Checkout returns 400; the discount is not given below the minimum", "P1")
def test_chk_007(client):
    h = login(client)
    add(client, h, 3)
    add(client, h, 9)
    assert client.post("/coupons/validate", json={"code": "FLAT200"}, headers=h).status_code == 200
    client.delete("/cart/items/9", headers=h)
    assert client.post("/checkout", json={"card_number": CARD, "coupon_code": "FLAT200", "shipping": SHIP}, headers=h).status_code == 400
    assert client.get("/orders", headers=h).json() == []


@case("TC-CHK-008", "A failed checkout does not take stock for the other items",
      "1. Bob puts product 10 x2 in his cart\n2. Alice puts product 5 x1 and product 10 x2 in hers\n3. Bob checks out\n4. Alice checks out",
      "Alice gets 409. Product 5 stock is still 50 and her cart still has both lines", "P1")
def test_chk_008(client):
    alice, bob = login(client), login(client, BOB)
    add(client, bob, 10, 2)
    add(client, alice, 5, 1)
    add(client, alice, 10, 2)
    assert client.post("/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=bob).status_code == 201
    r = client.post("/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=alice)
    assert r.status_code == 409 and "Steel Water Bottle" in r.json()["detail"]
    assert stock(client, 5) == 50 and stock(client, 10) == 0
    assert len(client.get("/cart", headers=alice).json()["items"]) == 2 and client.get("/orders", headers=alice).json() == []


@case("TC-CHK-009", "Simultaneous checkouts never oversell",
      "Product 10 has 2 units. Six users each put 1 in their cart, then all six check out at the same moment",
      "Exactly 2 orders succeed (201); the other 4 get 409; stock ends at 0, not negative; no server errors", "P1")
def test_chk_009(live_server):
    httpx.post(live_server + "/test/reset", headers=RESET, timeout=10)
    tokens = []
    for i in range(6):
        r = httpx.post(live_server + "/auth/register", json={"email": "u%d@example.com" % i, "name": "U%d" % i, "password": "Secret123"}, timeout=10)
        h = {"Authorization": "Bearer " + r.json()["token"]}
        assert httpx.post(live_server + "/cart/items", json={"product_id": 10, "quantity": 1}, headers=h, timeout=10).status_code == 200
        tokens.append(h)
    codes, gate = [], threading.Barrier(6)

    def buy(h):
        gate.wait()
        codes.append(httpx.post(live_server + "/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=h, timeout=30).status_code)

    threads = [threading.Thread(target=buy, args=(h,)) for h in tokens]
    [t.start() for t in threads]
    [t.join() for t in threads]
    left = httpx.get(live_server + "/products/10", timeout=10).json()["stock"]
    assert sorted(codes) == [201, 201, 409, 409, 409, 409] and left == 0, "Actual: responses %s, stock left %s" % (sorted(codes), left)


@case("TC-CHK-010", "Submitting checkout twice creates one order", "Cart: product 7. POST /checkout twice in a row", "First: 201. Second: 400 Cart is empty. One order; stock 14")
def test_chk_010(client):
    h = login(client)
    add(client, h, 7)
    first = client.post("/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=h)
    second = client.post("/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=h)
    assert (first.status_code, second.status_code) == (201, 400)
    assert len(client.get("/orders", headers=h).json()) == 1 and stock(client, 7) == 14


# ====================================================================== orders
def place(client, h, product_id=5, quantity=1, coupon=None):
    add(client, h, product_id, quantity)
    body = {"card_number": CARD, "shipping": SHIP}
    if coupon:
        body["coupon_code"] = coupon
    r = client.post("/checkout", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


@case("TC-ORD-001", "Order list shows only my orders, newest first", "Alice places two orders, Bob places one. Each calls GET /orders",
      "Alice sees her two with the newer first; Bob sees only his", "P1")
def test_ord_001(client):
    alice, bob = login(client), login(client, BOB)
    a1, a2, b1 = place(client, alice, 5), place(client, alice, 9), place(client, bob, 7)
    assert [o["id"] for o in client.get("/orders", headers=alice).json()] == [a2["id"], a1["id"]]
    assert [o["id"] for o in client.get("/orders", headers=bob).json()] == [b1["id"]]


@case("TC-ORD-002", "Order detail adds up", "Place an order for product 6 x3 with WELCOME10, then GET /orders/{id}",
      "One line: Denim Jacket, 2199 x 3 = 6597. Subtotal 6597, discount 659, total 5938; total = subtotal - discount", "P1")
def test_ord_002(client):
    h = login(client)
    oid = place(client, h, 6, 3, "WELCOME10")["id"]
    o = client.get("/orders/%d" % oid, headers=h).json()
    assert o["items"] == [{"product_id": 6, "name": "Denim Jacket", "unit_price": 2199, "quantity": 3, "line_total": 6597}]
    assert (o["subtotal"], o["discount"], o["total"]) == (6597, 659, 5938) and o["subtotal"] - o["discount"] == o["total"]


@case("TC-ORD-003", "Another user's order cannot be seen or cancelled", "Alice places an order. Bob calls GET and POST cancel on its id",
      "404 for both; the order stays paid", "P1")
def test_ord_003(client):
    alice, bob = login(client), login(client, BOB)
    oid = place(client, alice)["id"]
    assert client.get("/orders/%d" % oid, headers=bob).status_code == 404
    assert client.post("/orders/%d/cancel" % oid, headers=bob).status_code == 404
    assert client.get("/orders/%d" % oid, headers=alice).json()["status"] == "paid"


@case("TC-ORD-004", "Cancelling an order returns the stock, once", "Order product 1 x3 (stock 12 to 9). Cancel it. Cancel it again",
      "First cancel: status cancelled, stock back to 12. Second cancel: 409 and stock stays 12", "P1")
def test_ord_004(client):
    h = login(client)
    oid = place(client, h, 1, 3)["id"]
    assert stock(client, 1) == 9
    assert client.post("/orders/%d/cancel" % oid, headers=h).json()["status"] == "cancelled" and stock(client, 1) == 12
    assert client.post("/orders/%d/cancel" % oid, headers=h).status_code == 409 and stock(client, 1) == 12


@case("TC-ORD-005", "Unknown and malformed order ids", "GET /orders/999 and /orders/abc; POST /orders/999/cancel", "999: 404. abc: 422")
def test_ord_005(client):
    h = login(client)
    assert client.get("/orders/999", headers=h).status_code == 404 and client.post("/orders/999/cancel", headers=h).status_code == 404
    assert client.get("/orders/abc", headers=h).status_code == 422


@case("TC-ORD-006", "Order records when it was placed", "Place an order and read created_at", "A UTC timestamp within the last minute")
def test_ord_006(client):
    created = datetime.fromisoformat(place(client, login(client))["created_at"])
    assert abs(datetime.utcnow() - created) < timedelta(minutes=1)


@case("TC-ORD-007", "A cancelled order's stock can be bought again", "Order all 2 units of product 10, cancel, then order 2 again", "The second order succeeds")
def test_ord_007(client):
    h = login(client)
    oid = place(client, h, 10, 2)["id"]
    client.post("/orders/%d/cancel" % oid, headers=h)
    assert place(client, h, 10, 2)["status"] == "paid" and stock(client, 10) == 0


# ====================================================================== system and security
@case("TC-SYS-001", "Reset returns everything to the seed state",
      "Register a user, place an order, leave an item in a cart, then POST /test/reset",
      "Stock is back to seed values; the new user, all orders, carts and old tokens are gone; seed users can log in", "P1")
def test_sys_001(client):
    h = login(client)
    place(client, h, 1, 3)
    add(client, h, 5)
    register(client)
    assert client.post("/test/reset", headers=RESET).json() == {"status": "reset"}
    assert stock(client, 1) == 12 and client.get("/me", headers=h).status_code == 401
    assert client.post("/auth/login", json={"email": "new@example.com", "password": "Secret123"}).status_code == 401
    fresh = login(client)
    assert client.get("/orders", headers=fresh).json() == [] and client.get("/cart", headers=fresh).json()["items"] == []


@case("TC-SYS-002", "Health check and error format", "GET /health; GET /products/999", "Health: 200 {status: ok}. Errors are JSON with a 'detail' field")
def test_sys_002(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/products/999").json() == {"detail": "Product not found"}


@case("TC-SEC-001", "The data reset endpoint is not open to anyone",
      "Place an order, then POST /test/reset: 1. with no key\n2. with a wrong X-Reset-Key\n3. with the right key",
      "1 and 2: 403 and the order still exists. 3: 200 and the data is back to the seed state", "P1")
def test_sec_001(client):
    h = login(client)
    place(client, h)
    for headers in [{}, {"X-Reset-Key": "wrong"}, {"X-Reset-Key": ""}]:
        r = client.post("/test/reset", headers=headers)
        assert r.status_code == 403, "Actual: %s with headers %r" % (r.status_code, headers)
    assert len(client.get("/orders", headers=h).json()) == 1
    assert client.post("/test/reset", headers=RESET).status_code == 200
    assert client.get("/orders", headers=login(client)).json() == []


@case("TC-SEC-002", "A user cannot act on another user's cart or order by guessing ids",
      "Alice has product 5 in her cart and one order. Bob tries PUT and DELETE on product 5 in 'his' cart and reads order ids 1 to 3",
      "Bob gets 404 everywhere; Alice's data is unchanged", "P1")
def test_sec_002(client):
    alice, bob = login(client), login(client, BOB)
    place(client, alice, 9)
    add(client, alice, 5, 2)
    assert client.put("/cart/items/5", json={"quantity": 1}, headers=bob).status_code == 404
    assert client.delete("/cart/items/5", headers=bob).status_code == 404
    assert all(client.get("/orders/%d" % i, headers=bob).status_code == 404 for i in (1, 2, 3))
    assert client.get("/cart", headers=alice).json()["items"][0]["quantity"] == 2


@case("TC-SEC-003", "Markup in a name is stored and returned as plain text", "Register with the name <script>alert(1)</script> and read /me",
      "201; /me returns exactly the same text as JSON (the page is responsible for showing it safely)")
def test_sec_003(client):
    name = "<script>alert(1)</script>"
    r = register(client, name=name)
    assert r.status_code == 201
    me = client.get("/me", headers={"Authorization": "Bearer " + r.json()["token"]})
    assert me.json()["name"] == name and me.headers["content-type"].startswith("application/json")


# ====================================================================== found during the fix round
@case("TC-AUTH-013", "Malformed email domains are rejected", "Register with a@b..c, a@.com, a@b.c. and a@b_c.com", "422 for each")
def test_auth_013(client):
    for email in ["a@b..c", "a@.com", "a@b.c.", "a@b_c.com"]:
        r = register(client, email=email)
        assert r.status_code == 422, "Actual: %s for %r. The address was accepted" % (r.status_code, email)


@case("TC-CHK-011", "Two checkout requests for the same cart create one order",
      "One user has product 5 x1 in the cart. Send 8 checkout requests for that user at the same moment. Repeat 5 times",
      "Each time exactly one request returns 201; the rest are refused; one order is created and stock drops by 1; no server errors", "P1")
def test_chk_011(live_server):
    for attempt in range(5):
        httpx.post(live_server + "/test/reset", headers=RESET, timeout=10)
        tok = httpx.post(live_server + "/auth/login", json={"email": ALICE, "password": PASSWORD}, timeout=10).json()["token"]
        h = {"Authorization": "Bearer " + tok}
        httpx.post(live_server + "/cart/items", json={"product_id": 5, "quantity": 1}, headers=h, timeout=10)
        codes, gate = [], threading.Barrier(8)

        def buy():
            gate.wait()
            codes.append(httpx.post(live_server + "/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=h, timeout=30).status_code)

        threads = [threading.Thread(target=buy) for _ in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        orders = len(httpx.get(live_server + "/orders", headers=h, timeout=10).json())
        left = httpx.get(live_server + "/products/5", timeout=10).json()["stock"]
        ok = codes.count(201) == 1 and orders == 1 and left == 49 and all(c in (201, 400, 409) for c in codes)
        assert ok, "Actual (attempt %d): responses %s, %d orders created, stock %d (expected 1 order, stock 49)" % (attempt + 1, sorted(codes), orders, left)


@case("TC-CHK-012", "Card number must use the digits 0 to 9", "Checkout with 16 Arabic-Indic digits (٤١١١١١١١١١١١١١١١) and 16 full-width digits",
      "422; no order is created")
def test_chk_012(client):
    h = login(client)
    add(client, h, 7)
    for card in ["٤" + "١" * 15, "４" + "１" * 15]:
        r = client.post("/checkout", json={"card_number": card, "shipping": SHIP}, headers=h)
        assert r.status_code == 422, "Actual: %s. A card number in non-ASCII digits was accepted and an order was placed" % r.status_code
    assert client.get("/orders", headers=h).json() == []


@case("TC-SEC-004", "Very large numbers never crash the server",
      "Use the number 10^30 as: product id, order id, min_price, max_price, limit, cart product_id, cart quantity, cart PUT/DELETE id",
      "Each request gets a 4xx answer (404 or 422 or 409). None returns 500", "P1")
def test_sec_004(live_server):
    big = 10 ** 30
    tok = httpx.post(live_server + "/auth/login", json={"email": ALICE, "password": PASSWORD}, timeout=10).json()["token"]
    h = {"Authorization": "Bearer " + tok}
    calls = [
        ("GET", "/products/%d" % big, None), ("GET", "/products?max_price=%d" % big, None), ("GET", "/products?min_price=%d" % big, None),
        ("GET", "/products?limit=%d" % big, None), ("GET", "/orders/%d" % big, None), ("POST", "/orders/%d/cancel" % big, None),
        ("POST", "/cart/items", {"product_id": big, "quantity": 1}), ("POST", "/cart/items", {"product_id": 5, "quantity": big}),
        ("PUT", "/cart/items/%d" % big, {"quantity": 1}), ("PUT", "/cart/items/5", {"quantity": big}), ("DELETE", "/cart/items/%d" % big, None),
    ]
    bad = []
    for method, path, body in calls:
        code = httpx.request(method, live_server + path, json=body, headers=h, timeout=10).status_code
        if not 400 <= code < 500:
            bad.append("%s %s -> %s" % (method, path.replace(str(big), "10^30"), code))
    assert not bad, "Actual: " + "; ".join(bad)


@case("TC-CART-011", "Cart requests with a missing or empty body are rejected cleanly",
      "With product 5 in the cart: PUT /cart/items/5 with no body and with {}; POST /cart/items with no body", "422 each time; quantity unchanged")
def test_cart_011(client):
    h = login(client)
    add(client, h, 5, 2)
    assert client.put("/cart/items/5", headers=h).status_code == 422
    assert client.put("/cart/items/5", json={}, headers=h).status_code == 422
    assert client.post("/cart/items", headers=h).status_code == 422
    assert client.get("/cart", headers=h).json()["items"][0]["quantity"] == 2




@case("TC-CHK-013", "Shipping details are stored with the order",
      "Cart: product 5. POST /checkout with a card and a shipping object (name padded with spaces). GET the order. Also GET /shipping/options",
      "201. The order returns the same shipping details with the name trimmed. Options list India, 36 states and territories, and a shipping fee of 0", "P1")
def test_chk_013(client):
    h = login(client)
    add(client, h, 5)
    r = client.post("/checkout", json={"card_number": CARD, "shipping": dict(SHIP, full_name="  Asha Rao ")}, headers=h)
    assert r.status_code == 201
    assert client.get("/orders/%d" % r.json()["id"], headers=h).json()["shipping"] == SHIP
    opts = client.get("/shipping/options").json()
    assert opts["countries"] == ["India"] and len(opts["states"]) == 36 and opts["shipping_fee"] == 0


@case("TC-CHK-014", "Invalid shipping details stop the order",
      "Cart: product 5. Checkout with, one at a time: bad email; blank name; blank address line 1; blank city; state 'Atlantis'; PIN '1234', '012345', '5600011', 'abcdef'; country 'Nepal'; a 201-character address line; a missing field",
      "422 for each. No order is created, stock and cart are unchanged", "P1")
def test_chk_014(client):
    h = login(client)
    add(client, h, 5)
    bad = [{"email": "nope"}, {"full_name": "   "}, {"line1": ""}, {"city": " "}, {"state": "Atlantis"}, {"postal_code": "1234"},
           {"postal_code": "012345"}, {"postal_code": "5600011"}, {"postal_code": "abcdef"}, {"country": "Nepal"}, {"line1": "x" * 201}]
    for change in bad:
        r = client.post("/checkout", json={"card_number": CARD, "shipping": dict(SHIP, **change)}, headers=h)
        assert r.status_code == 422, "Actual: %s for %r" % (r.status_code, change)
    missing = {k: v for k, v in SHIP.items() if k != "city"}
    assert client.post("/checkout", json={"card_number": CARD, "shipping": missing}, headers=h).status_code == 422
    assert client.get("/orders", headers=h).json() == [] and stock(client, 5) == 50
    assert len(client.get("/cart", headers=h).json()["items"]) == 1


@case("TC-CHK-015", "An order cannot be placed without a delivery address", "Cart: product 5. POST /checkout with a card but no shipping object",
      "422; a shop cannot deliver an order that has no address. No order is created", "P1")
def test_chk_015(client):
    h = login(client)
    add(client, h, 5)
    r = client.post("/checkout", json={"card_number": CARD}, headers=h)
    assert r.status_code == 422, "Actual: %s. The API accepts an order with no delivery address (the web page always sends one)" % r.status_code
    assert client.get("/orders", headers=h).json() == []


@case("TC-ORD-008", "Cancelling the same order from several requests at once returns the stock once",
      "Order product 1 x3 (stock 12 to 9). Send 6 cancel requests for it at the same moment. Repeat 3 times",
      "Each time exactly one cancel succeeds, the rest get 409, and stock is back to 12, not higher", "P1")
def test_ord_008(live_server):
    for attempt in range(3):
        httpx.post(live_server + "/test/reset", headers=RESET, timeout=10)
        tok = httpx.post(live_server + "/auth/login", json={"email": ALICE, "password": PASSWORD}, timeout=10).json()["token"]
        h = {"Authorization": "Bearer " + tok}
        httpx.post(live_server + "/cart/items", json={"product_id": 1, "quantity": 3}, headers=h, timeout=10)
        oid = httpx.post(live_server + "/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=h, timeout=10).json()["id"]
        codes, gate = [], threading.Barrier(6)

        def cancel():
            gate.wait()
            codes.append(httpx.post(live_server + "/orders/%d/cancel" % oid, headers=h, timeout=30).status_code)

        threads = [threading.Thread(target=cancel) for _ in range(6)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        left = httpx.get(live_server + "/products/1", timeout=10).json()["stock"]
        assert sorted(codes) == [200, 409, 409, 409, 409, 409] and left == 12, "Actual (attempt %d): responses %s, stock %s" % (attempt + 1, sorted(codes), left)


# ====================================================================== search and suggestions
@case("TC-PROD-016", "Search finds products by part of a word in the name, category or specs",
      "GET /products with q = mob, MOB, amoled, run sh, red lip, mob zzz",
      "mob and MOB: the 3 mobile products (9, 11, 15), found through the category. amoled: product 11, found through its specs. "
      "'run sh': the 3 running shoes. 'red lip': product 20. 'mob zzz': nothing, because every word must match", "P1")
def test_prod_016(client):
    ids = lambda q: [p["id"] for p in client.get("/products", params={"q": q}).json()]
    assert ids("mob") == [9, 11, 15] and ids("MOB") == [9, 11, 15]
    assert ids("amoled") == [11] and ids("run sh") == [1, 2, 3] and ids("red lip") == [20]
    assert ids("mob zzz") == []
    assert [p["id"] for p in client.get("/products", params={"q": "mob", "max_price": 1000}).json()] == [9]  # still combines with filters


@case("TC-PROD-017", "Search suggestions",
      "GET /products/suggest with q = mob, ph, m, (empty), zz, %%, and q=sho&limit=2; then limit=0 and limit=21",
      "mob: category Mobiles (3 products) and products 9, 11, 15. ph: products whose name has a word starting with 'ph' come first (9, 15), "
      "then other matches (11, 14). One character or empty: no suggestions. zz and %%: no suggestions. limit=2: two products but total 5. "
      "limit 0 or 21: 422", "P1")
def test_prod_017(client):
    get = lambda q, **kw: client.get("/products/suggest", params=dict(q=q, **kw)).json()
    mob = get("mob")
    assert [(c["slug"], c["name"], c["count"]) for c in mob["categories"]] == [("mobiles", "Mobiles", 3)]
    assert [p["id"] for p in mob["products"]] == [9, 11, 15] and mob["total"] == 3
    assert set(mob["products"][0]) == {"id", "name", "category", "price", "image", "in_stock"}
    assert [p["id"] for p in get("ph")["products"]] == [9, 15, 11, 14]
    for q in ["m", "", " ", "zz", "%%"]:
        r = get(q)
        assert r["categories"] == [] and r["products"] == [] and r["total"] == 0, q
    two = get("sho", limit=2)
    assert len(two["products"]) == 2 and two["total"] == 5
    assert client.get("/products/suggest", params={"q": "mob", "limit": 0}).status_code == 422
    assert client.get("/products/suggest", params={"q": "mob", "limit": 21}).status_code == 422
    assert client.get("/products/suggest", params={"q": "x" * 101}).status_code == 422
