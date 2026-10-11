import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/test.db")
for _name in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "AGENT_API_KEY", "AGENT_PROVIDER", "AGENT_BASE_URL", "AGENT_MODEL"):
    os.environ.pop(_name, None)

import pytest

RESET = {"X-Reset-Key": "practice-reset"}
from helpers import SHIP  # noqa: E402
from fastapi.testclient import TestClient

from app.main import app  # must be imported before app.agent
from app import agent  # noqa: E402,I001


@pytest.fixture
def client():
    with TestClient(app) as c:
        assert c.post("/test/reset", headers=RESET).status_code == 200
        yield c


def login(client, email="alice@example.com"):
    r = client.post("/auth/login", json={"email": email, "password": "Password123"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def use(name, args, i=1):
    return {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": f"t{i}", "name": name, "input": args}]}


def text(t):
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": t}]}


def script(monkeypatch, *responses):
    """Replace the model with a fixed list of responses and record what it was sent."""
    queue, seen = list(responses), []

    def fake(system, messages, tools):
        seen.append([dict(m) for m in messages])
        return queue.pop(0)

    monkeypatch.setattr(agent, "call_model", fake)
    return seen


def test_not_configured_and_login_required(client):
    assert client.get("/agent/status").json()["configured"] is False
    assert client.post("/agent/chat", json={"message": "hi"}).status_code == 401
    r = client.post("/agent/chat", json={"message": "hi"}, headers=login(client))
    assert r.status_code == 503 and "GEMINI_API_KEY" in r.json()["detail"]


def test_tool_call_changes_cart_and_is_logged(client, monkeypatch):
    h = login(client)
    seen = script(
        monkeypatch,
        use("search_products", {"query": "running", "max_price": 3000, "sort": "price_asc"}, 1),
        use("add_to_cart", {"product_id": 3, "quantity": 1}, 2),
        text("Added Budget Running Shoes (id 3) to your cart."),
    )
    r = client.post("/agent/chat", json={"message": "cheapest running shoes under 3000, add to cart"}, headers=h).json()
    assert r["reply"].startswith("Added Budget")
    assert [a["tool"] for a in r["actions"]] == ["search_products", "add_to_cart"]
    assert [p["id"] for p in r["actions"][0]["output"]] == [3, 1]
    assert client.get("/cart", headers=h).json()["subtotal"] == 1499  # same cart the UI shows
    log = client.get("/agent/actions", headers=h).json()
    assert [a["tool"] for a in log] == ["add_to_cart", "search_products"] and not any(a["is_error"] for a in log)
    assert seen[2][-1]["content"][0]["type"] == "tool_result"  # the model was shown the tool output
    assert client.get("/agent/actions", headers=login(client, "bob@example.com")).json() == []


def test_tool_errors_are_reported_not_hidden(client, monkeypatch):
    h = login(client)
    script(
        monkeypatch,
        use("add_to_cart", {"product_id": 8, "quantity": 1}, 1),  # out of stock
        use("add_to_cart", {"product_id": "abc"}, 2),  # bad argument
        use("delete_everything", {}, 3),  # not a real tool
        use("cancel_order", {"order_id": 999}, 4),
        text("Sorry, that is out of stock."),
    )
    r = client.post("/agent/chat", json={"message": "add the speaker"}, headers=h).json()
    assert [a["is_error"] for a in r["actions"]] == [True, True, True, True]
    assert r["actions"][0]["output"] == {"error": "Only 0 in stock"}
    assert r["actions"][3]["output"] == {"error": "Order not found"}
    assert client.get("/cart", headers=h).json()["items"] == []


def test_conversation_continues_and_is_private(client, monkeypatch):
    h = login(client)
    script(monkeypatch, text("Hello!"), text("Still here."))
    first = client.post("/agent/chat", json={"message": "hi"}, headers=h).json()
    seen = script(monkeypatch, text("Still here."))
    second = client.post("/agent/chat", json={"message": "again", "conversation_id": first["conversation_id"]}, headers=h)
    assert second.json()["conversation_id"] == first["conversation_id"]
    assert [m["role"] for m in seen[0]] == ["user", "assistant", "user"]
    bob = client.post(
        "/agent/chat", json={"message": "x", "conversation_id": first["conversation_id"]}, headers=login(client, "bob@example.com")
    )
    assert bob.status_code == 404


def test_step_limit_stops_a_looping_agent(client, monkeypatch):
    h = login(client)
    script(monkeypatch, *[use("view_cart", {}, i) for i in range(agent.MAX_STEPS)])
    r = client.post("/agent/chat", json={"message": "loop"}, headers=h).json()
    assert len(r["actions"]) == agent.MAX_STEPS and "allowed number of steps" in r["reply"]


def test_agent_can_cancel_only_own_order(client, monkeypatch):
    alice, bob = login(client), login(client, "bob@example.com")
    client.post("/cart/items", json={"product_id": 5}, headers=alice)
    oid = client.post("/checkout", json={"card_number": "4111111111111111", "shipping": SHIP}, headers=alice).json()["id"]
    script(monkeypatch, use("cancel_order", {"order_id": oid}), text("Not found."))
    assert client.post("/agent/chat", json={"message": "cancel it"}, headers=bob).json()["actions"][0]["is_error"]
    assert client.get(f"/orders/{oid}", headers=alice).json()["status"] == "paid"
    script(monkeypatch, use("cancel_order", {"order_id": oid}), text("Cancelled."))
    assert not client.post("/agent/chat", json={"message": "yes cancel"}, headers=alice).json()["actions"][0]["is_error"]
    assert client.get(f"/orders/{oid}", headers=alice).json()["status"] == "cancelled"


class FakeResponse:
    def __init__(self, status, body):
        self.status_code, self._body, self.text = status, body, str(body)

    def json(self):
        return self._body


def test_gemini_request_and_response_format(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert client.get("/agent/status").json() == {"enabled": False, "configured": True, "provider": "gemini", "model": "gemini-flash-latest"}
    sent = []
    replies = [
        FakeResponse(200, {"choices": [{"message": {"content": None, "tool_calls": [{
            "id": "c1", "type": "function", "extra_content": {"google": {"thought_signature": "sig"}},
            "function": {"name": "add_to_cart", "arguments": '{"product_id": 5, "quantity": 2}'}}]}}]}),
        FakeResponse(200, {"choices": [{"message": {"content": "Added 2 T-shirts."}}]}),
    ]

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.append((url, headers, json))
        return replies.pop(0)

    monkeypatch.setattr(agent.httpx, "post", fake_post)
    h = login(client)
    r = client.post("/agent/chat", json={"message": "two t-shirts please"}, headers=h).json()
    assert r["reply"] == "Added 2 T-shirts." and r["actions"][0]["tool"] == "add_to_cart"
    assert client.get("/cart", headers=h).json()["subtotal"] == 998
    url, headers, first = sent[0]
    assert url.endswith("/openai/chat/completions") and headers == {"Authorization": "Bearer test-key"}
    assert first["messages"][0]["role"] == "system" and first["messages"][1] == {"role": "user", "content": "two t-shirts please"}
    assert first["tools"][0]["type"] == "function" and "parameters" in first["tools"][0]["function"]
    second = sent[1][2]["messages"]
    assert second[2]["tool_calls"][0]["extra_content"] == {"google": {"thought_signature": "sig"}}  # sent back unchanged
    assert second[3]["role"] == "tool" and second[3]["tool_call_id"] == "c1" and "998" in second[3]["content"]


def test_model_errors_become_clear_messages(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    h = login(client)
    for status, body, expected in [
        (429, [{"error": {"message": "Quota exceeded"}}], "rate limit"),
        (404, {"error": {"message": "models/x is not found"}}, "AGENT_MODEL"),
        (400, {"error": {"message": "API key not valid"}}, "API key not valid"),
    ]:
        monkeypatch.setattr(agent.httpx, "post", lambda *a, _s=status, _b=body, **k: FakeResponse(_s, _b))
        r = client.post("/agent/chat", json={"message": "hi"}, headers=h)
        assert r.status_code == 503 and expected in r.json()["detail"]


def test_anthropic_and_custom_providers(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert client.get("/agent/status").json()["provider"] == "anthropic"
    sent = []

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.append((url, headers, json))
        return FakeResponse(200, {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Hi"}]})

    monkeypatch.setattr(agent.httpx, "post", fake_post)
    assert client.post("/agent/chat", json={"message": "hi"}, headers=login(client)).json()["reply"] == "Hi"
    assert sent[0][1]["x-api-key"] == "k" and "system" in sent[0][2]
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.setenv("AGENT_BASE_URL", "http://localhost:11434/v1/")
    monkeypatch.setenv("AGENT_MODEL", "llama")
    assert client.get("/agent/status").json() == {"enabled": False, "configured": True, "provider": "openai", "model": "llama"}
    monkeypatch.setattr(agent.httpx, "post", lambda url, **k: sent.append(url) or FakeResponse(200, {"choices": [{"message": {"content": "Yo"}}]}))
    assert client.post("/agent/chat", json={"message": "hi"}, headers=login(client)).json()["reply"] == "Yo"
    assert sent[-1] == "http://localhost:11434/v1/chat/completions"
