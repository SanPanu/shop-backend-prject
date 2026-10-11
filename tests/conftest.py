import csv
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pytest

RESET = {"X-Reset-Key": "practice-reset"}

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("DATABASE_URL", "sqlite:///%s/test.db" % tempfile.mkdtemp())

AREAS = {
    "AUTH": "Authentication", "PROD": "Products", "CART": "Cart", "COUP": "Coupons", "CHK": "Checkout",
    "ORD": "Orders", "SYS": "System", "SEC": "Security", "UI": "User interface",
}
RESULTS = {}


def pytest_configure(config):
    config.addinivalue_line("markers", "case(id, title, steps, expected, priority): documented test case")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    marker = item.get_closest_marker("case")
    if marker is None:
        return
    k = marker.kwargs
    row = RESULTS.setdefault(k["id"], {
        "id": k["id"], "area": AREAS.get(k["id"].split("-")[1], ""), "type": "UI" if "_ui" in item.fspath.basename else "API",
        "priority": k["priority"], "title": k["title"], "steps": k["steps"], "expected": k["expected"],
        "status": "Not run", "actual": "", "automated_by": "%s::%s" % (item.fspath.basename, item.name),
    })
    if rep.skipped:
        row["status"], row["actual"] = "Skipped", str(rep.longrepr[-1] if isinstance(rep.longrepr, tuple) else rep.longrepr)[:300]
    elif rep.when == "call":
        row["status"] = "Pass" if rep.passed else "Fail"
        # Keep the tester's own message and drop pytest's "assert ..." detail that follows it.
        row["actual"] = "As expected" if rep.passed else " ".join(str(call.excinfo.value).split("\nassert ")[0].split())[:400]
    elif rep.failed:
        row["status"], row["actual"] = "Blocked", ("%s failed: %s" % (rep.when, " ".join(str(call.excinfo.value).split())))[:400]


def pytest_sessionfinish(session):
    if not RESULTS:
        return
    out = ROOT / "test-report"
    out.mkdir(exist_ok=True)
    # A run of only some cases (or one where the browser cases were skipped) updates those rows and keeps the rest,
    # so the report always holds the latest real result for every case.
    merged = {}
    try:
        merged = {r["id"]: r for r in json.loads((out / "results.json").read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        pass
    for case_id, row in RESULTS.items():
        if row["status"] == "Skipped" and case_id in merged:
            continue
        merged[case_id] = row
    rows = sorted(merged.values(), key=lambda r: r["id"])
    cols = ["id", "area", "type", "priority", "title", "steps", "expected", "status", "actual", "automated_by"]
    heads = ["ID", "Area", "Type", "Priority", "Title", "Steps", "Expected result", "Status", "Actual result", "Automated by"]
    with open(out / "test_cases.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(heads)
        w.writerows([r[c] for c in cols] for r in rows)
    (out / "results.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")


# ---------- API tests: in-process client ----------
# Set SHOP_BASE_URL (for example http://localhost:9080/shop) to run the documented cases against a shop that is
# already running somewhere else, such as the WebSphere build, instead of the Python application in this folder.
EXTERNAL = os.environ.get("SHOP_BASE_URL", "").rstrip("/")


@pytest.fixture
def client():
    if EXTERNAL:
        with httpx.Client(base_url=EXTERNAL, timeout=30) as c:
            assert c.post("/test/reset", headers=RESET).status_code == 200
            yield c
        return
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        assert c.post("/test/reset", headers=RESET).status_code == 200
        yield c


# ---------- live server, for browser and concurrency tests ----------
@pytest.fixture(scope="session")
def live_server():
    if EXTERNAL:
        yield EXTERNAL
        return
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    env = dict(os.environ, DATABASE_URL="sqlite:///%s/live.db" % tempfile.mkdtemp(), AGENT_ENABLED="false")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"], cwd=str(ROOT), env=env
    )
    base = "http://127.0.0.1:%d" % port
    try:
        for _ in range(60):
            try:
                if httpx.get(base + "/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.25)
        else:
            pytest.fail("The shop server did not start")
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture(scope="session")
def browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright is not installed (pip install playwright, then: playwright install chromium)")
    with sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception as e:  # browser binary missing
            pytest.skip("Chromium is not available for Playwright: %s" % str(e).splitlines()[0])
        yield b
        b.close()


@pytest.fixture
def page(browser, live_server):
    httpx.post(live_server + "/test/reset", headers=RESET, timeout=10)
    ctx = browser.new_context(viewport={"width": 1366, "height": 850}, base_url=live_server)
    ctx.set_default_timeout(7000)
    p = ctx.new_page()
    p.js_errors = []
    p.on("pageerror", lambda e: p.js_errors.append(str(e)))
    yield p
    ctx.close()
