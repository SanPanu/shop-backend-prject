"""Shared helpers for the documented test cases (test_cases_*.py)."""
import pytest

CARD = "4111111111111111"
DECLINED = "4000000000000002"
PASSWORD = "Password123"
SHIP = {"email": "asha@example.com", "full_name": "Asha Rao", "line1": "12 MG Road", "line2": "Flat 4B", "city": "Bengaluru",
        "state": "Karnataka", "postal_code": "560001", "country": "India"}
RESET = {"X-Reset-Key": "practice-reset"}  # default key; see RESET_KEY in the README


def case(id, title, steps, expected, priority="P2"):
    """Attach test-case documentation to a test. It ends up in test-report/test_cases.csv."""
    return pytest.mark.case(id=id, title=title, steps=steps, expected=expected, priority=priority)


def login(client, email="alice@example.com", password=PASSWORD):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def add(client, headers, product_id, quantity=1):
    return client.post("/cart/items", json={"product_id": product_id, "quantity": quantity}, headers=headers)


def stock(client, product_id):
    return client.get("/products/%d" % product_id).json()["stock"]
