import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

import pytest

RESET = {"X-Reset-Key": "practice-reset"}
from helpers import SHIP  # noqa: E402
from fastapi.testclient import TestClient

from app.main import app

CARD = "4111111111111111"
DECLINED = "4000000000000002"


@pytest.fixture
def client():
    with TestClient(app) as c:
        assert c.post("/test/reset", headers=RESET).status_code == 200
        yield c


def login(client, email="alice@example.com"):
    r = client.post("/auth/login", json={"email": email, "password": "Password123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_health_and_seed(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert len(client.get("/products").json()) == 30


def test_register_login_and_duplicates(client):
    body = {"email": "new@example.com", "name": "New", "password": "Secret123"}
    r = client.post("/auth/register", json=body)
    assert r.status_code == 201
    assert client.get("/me", headers={"Authorization": f"Bearer {r.json()['token']}"}).json()["email"] == "new@example.com"
    assert client.post("/auth/register", json=body).status_code == 409
    assert client.post("/auth/register", json={**body, "email": "bad"}).status_code == 422
    assert client.post("/auth/login", json={"email": "new@example.com", "password": "wrong"}).status_code == 401


def test_auth_required(client):
    assert client.get("/cart").status_code == 401
    assert client.get("/cart", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_product_search_and_filters(client):
    shoes = client.get("/products", params={"q": "running", "max_price": 3000, "sort": "price_asc"}).json()
    assert [p["id"] for p in shoes] == [3, 1]
    assert [p["id"] for p in client.get("/products", params={"in_stock": False}).json()] == [8]
    assert client.get("/products/999").status_code == 404
    assert client.get("/products", params={"sort": "bogus"}).status_code == 422


def test_cart_rules(client):
    h = login(client)
    assert client.post("/cart/items", json={"product_id": 5, "quantity": 2}, headers=h).json()["subtotal"] == 998
    assert client.post("/cart/items", json={"product_id": 5, "quantity": 1}, headers=h).json()["items"][0]["quantity"] == 3
    assert client.post("/cart/items", json={"product_id": 8}, headers=h).status_code == 409  # out of stock
    assert client.post("/cart/items", json={"product_id": 10, "quantity": 3}, headers=h).status_code == 409
    assert client.post("/cart/items", json={"product_id": 5, "quantity": 0}, headers=h).status_code == 422
    assert client.put("/cart/items/5", json={"quantity": 1}, headers=h).json()["subtotal"] == 499
    assert client.put("/cart/items/1", json={"quantity": 1}, headers=h).status_code == 404
    assert client.delete("/cart/items/5", headers=h).json() == {"items": [], "subtotal": 0}
    # carts are per user
    client.post("/cart/items", json={"product_id": 9}, headers=h)
    assert client.get("/cart", headers=login(client, "bob@example.com")).json()["items"] == []


def test_coupons(client):
    h = login(client)
    client.post("/cart/items", json={"product_id": 5, "quantity": 2}, headers=h)  # 998
    ok = client.post("/coupons/validate", json={"code": "welcome10"}, headers=h).json()
    assert (ok["discount"], ok["total"]) == (99, 899)
    for code in ("FLAT200", "EXPIRED50", "DISABLED20", "NOPE"):
        assert client.post("/coupons/validate", json={"code": code}, headers=h).status_code == 400
    client.post("/cart/items", json={"product_id": 1}, headers=h)  # 998 + 2799 = 3797
    assert client.post("/coupons/validate", json={"code": "FLAT200"}, headers=h).json()["total"] == 3597


def test_checkout_updates_stock_and_orders(client):
    h = login(client)
    client.post("/cart/items", json={"product_id": 10, "quantity": 2}, headers=h)
    r = client.post("/checkout", json={"card_number": CARD, "coupon_code": "WELCOME10", "shipping": SHIP}, headers=h)
    assert r.status_code == 201
    order = r.json()
    assert (order["subtotal"], order["discount"], order["total"], order["status"]) == (1298, 129, 1169, "paid")
    assert client.get("/products/10").json()["stock"] == 0
    assert client.get("/cart", headers=h).json()["items"] == []
    assert [o["id"] for o in client.get("/orders", headers=h).json()] == [order["id"]]
    # another user cannot see it
    assert client.get(f"/orders/{order['id']}", headers=login(client, "bob@example.com")).status_code == 404


def test_checkout_failures_change_nothing(client):
    h = login(client)
    assert client.post("/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=h).status_code == 400  # empty cart
    client.post("/cart/items", json={"product_id": 7}, headers=h)
    assert client.post("/checkout", json={"card_number": DECLINED, "shipping": SHIP}, headers=h).status_code == 402
    assert client.post("/checkout", json={"card_number": "123", "shipping": SHIP}, headers=h).status_code == 422
    assert client.post("/checkout", json={"card_number": CARD, "coupon_code": "EXPIRED50", "shipping": SHIP}, headers=h).status_code == 400
    assert client.get("/products/7").json()["stock"] == 15
    assert len(client.get("/cart", headers=h).json()["items"]) == 1
    assert client.get("/orders", headers=h).json() == []


def test_stock_taken_by_someone_else(client):
    alice, bob = login(client), login(client, "bob@example.com")
    client.post("/cart/items", json={"product_id": 10, "quantity": 2}, headers=alice)
    client.post("/cart/items", json={"product_id": 10, "quantity": 2}, headers=bob)
    assert client.post("/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=alice).status_code == 201
    assert client.post("/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=bob).status_code == 409
    assert client.get("/products/10").json()["stock"] == 0


def test_cancel_restores_stock_once(client):
    h = login(client)
    client.post("/cart/items", json={"product_id": 1, "quantity": 3}, headers=h)
    oid = client.post("/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=h).json()["id"]
    assert client.get("/products/1").json()["stock"] == 9
    assert client.post(f"/orders/{oid}/cancel", headers=h).json()["status"] == "cancelled"
    assert client.post(f"/orders/{oid}/cancel", headers=h).status_code == 409
    assert client.get("/products/1").json()["stock"] == 12


def test_reset_restores_known_state(client):
    h = login(client)
    client.post("/cart/items", json={"product_id": 1, "quantity": 3}, headers=h)
    client.post("/checkout", json={"card_number": CARD, "shipping": SHIP}, headers=h)
    client.post("/test/reset", headers=RESET)
    assert client.get("/products/1").json()["stock"] == 12
    assert client.get("/cart", headers=h).status_code == 401  # old tokens are gone too
    assert client.get("/orders", headers=login(client)).json() == []


def test_ui_is_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "Practice Shop" in r.text


def test_catalogue_fields_and_categories(client):
    p = client.get("/products/11").json()
    assert (p["price"], p["mrp"], p["discount_percent"], p["rating"], p["category"]) == (49999, 55999, 11, 4.6, "mobiles")
    cats = client.get("/categories").json()
    assert len(cats) == 10 and sum(c["count"] for c in cats) == 30
    assert [p["id"] for p in client.get("/products", params={"category": "books"}).json()] == [29, 30]
    top = client.get("/products", params={"sort": "discount", "limit": 3}).json()
    assert len(top) == 3 and top[0]["discount_percent"] >= top[1]["discount_percent"] >= top[2]["discount_percent"]
    assert client.get("/products", params={"sort": "rating", "limit": 1}).json()[0]["id"] == 23
