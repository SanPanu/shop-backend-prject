# Practice Shop - Project Conventions for Claude Code

## Project Overview
Practice Shop is a small e-commerce site built as a target for QA practice. Users can browse and search products,
manage a cart, apply coupons, check out with a mock card payment, and view or cancel orders. `README.md` has the
full endpoint list and seed data.

## Tech Stack

* Backend: Python 3.9, FastAPI, SQLAlchemy 2.0, pydantic v2, uvicorn
* Database: MySQL 8 (schema `shop`) when `DATABASE_URL` is set; a local SQLite file `shop.db` otherwise
* Frontend: one vanilla HTML/CSS/JS file with hash routing (no framework, no build step)
* Auth: bearer token in the `Authorization` header, PBKDF2 password hashes
* Testing: pytest with FastAPI TestClient (API) and Playwright for Python, Chromium (UI)

## Project Structure
```
Shop-Backend/
├── app/
│   ├── main.py            # All HTTP endpoints, validation, business rules
│   ├── models.py          # SQLAlchemy tables
│   ├── database.py        # Engine from DATABASE_URL
│   ├── seed.py            # Seed products, coupons, users; reset_database()
│   ├── agent.py           # Chat assistant (switched off, see below)
│   └── static/index.html  # The whole UI
├── tests/
│   ├── conftest.py        # Fixtures, report writer
│   ├── helpers.py         # case(), login(), add(), stock(), CARD, DECLINED, SHIP, RESET
│   ├── test_cases_api.py  # Documented API cases
│   ├── test_cases_ui.py   # Documented browser cases
│   ├── test_shop.py       # Quick developer checks (not in the report)
│   └── test_agent.py      # Quick developer checks (not in the report)
├── test-report/           # test_cases.csv, results.json, Excel workbooks
├── websphere/             # Old Java/Oracle port. Out of date. Do not change.
├── README.md
├── requirements.txt
└── pytest.ini
```

## Architecture Pattern
There are no layers: routes, validation and business rules all live in `app/main.py`, and the UI is the single file
`app/static/index.html`. Keep it that way; do not split files or add a framework unless asked.

## Commands to Run
```
source .venv/bin/activate                 # Always first
uvicorn app.main:app --reload             # Start the shop on http://127.0.0.1:8000
pytest                                    # All tests
pytest tests/test_cases_api.py            # API cases only
pytest tests/test_cases_ui.py             # Browser cases only
pytest tests/test_cases_api.py -k chk     # One area (functions are test_chk_001 ...)
lsof -ti :8000 | xargs kill               # Free port 8000 ("Address already in use")
```

API docs: http://127.0.0.1:8000/docs

## Database Safety

* The developer runs the shop on MySQL by exporting `DATABASE_URL` in the server's terminal. That database holds
  manually created accounts and orders.
* The tests reset the database before every case. They use a temporary SQLite file only when `DATABASE_URL` is NOT
  set in the shell that runs pytest. Before running pytest, run `unset DATABASE_URL` or confirm it is empty.
* Never call `POST /test/reset` against the running shop, and never run INSERT, UPDATE, DELETE or DROP on the
  MySQL `shop` schema, unless asked.
* Never print, ask for, or write the MySQL password into any file.

## Coding Rules

* Python 3.9 only: write `Optional[str]`, never `str | None`; no `match` statements.
* Each route with a path id needs its own `Path(...)` object; sharing one across routes breaks them.
* Prices are whole rupees (integers).
* Every interactive element in `index.html` must have a unique `data-testid`.
* Validation errors are shown under the field that caused them, using the `RULES`, `fieldError` and `validateForm`
  helpers in `index.html`. Do not add page-level alerts for field errors.
* API calls in `index.html` go through the `BASE` prefix.
* Error text shown to users must be plain language, never a stack trace or raw validation output.

## Testing Conventions

* Every documented case has the decorator `@case(id, title, steps, expected, priority)` from `tests/helpers.py`.
* ID prefixes: `TC-AUTH`, `TC-PROD`, `TC-CART`, `TC-COUP`, `TC-CHK`, `TC-ORD`, `TC-SEC`, `TC-SYS` (API) and `TC-UI`
  (browser). Use the next free number; never reuse an ID.
* Each run rewrites `test-report/test_cases.csv` and `results.json`. A partial run merges into the existing results.
* A failing documented case means a defect in the shop. Report it; do not weaken the assertion to make it pass.
* UI locators: `data-testid` first, then role, then label. No CSS classes.
* No fixed sleeps in UI tests; wait with `expect(...)`.
* Tests must be self-contained: the fixtures reset data, so each test logs in, acts, and asserts.
* Seed accounts: `alice@example.com` and `bob@example.com`, password `Password123`.
* Test cards: `4111111111111111` succeeds, `4000000000000002` is always declined (HTTP 402).
* Browser cases are reported as Skipped when Playwright is not installed
  (`pip install playwright && playwright install chromium`).

## Key Business Rules

* 30 seed products in 10 categories. Product 8 is out of stock; product 10 has 2 units.
* Coupons: `WELCOME10` 10% off; `FLAT200` 200 off with minimum order 1500; `EXPIRED50` and `DISABLED20` are
  always rejected. A coupon cannot be applied to an empty cart.
* Checkout needs a 16-digit card number (ASCII digits only) and a shipping address: India only, state from the
  fixed list, PIN code 6 digits not starting with 0. Shipping is free.
* Stock drops on checkout and is restored when an order is cancelled.
* An order can be cancelled once. A second cancel is rejected.
* Two simultaneous checkouts of the same cart must create one order, and stock must never go below zero.
* A user can see only their own cart and orders.
* Search: `q` matches part of a word in name, category or specs, ignoring case; every word must match.
  `%` and `_` are literal characters. Suggestions need at least 2 characters.
* `POST /test/reset` needs the header `X-Reset-Key: practice-reset`.

## Known Open Defect (left in on purpose)
On MySQL, `orders.created_at` has no fractional seconds, so the time in the checkout response differs slightly
from the time returned by later reads of the same order. Do not fix unless asked.

## Out of Scope Unless Asked

* The chat assistant (`app/agent.py`) is switched off (`AGENT_ENABLED` is not set). Leave it off.
* The `websphere/` folder is a stale Java port. Do not update or rebuild it.

## Code Style

* Match the existing style in each file: compact functions, short comments only where the reason is not obvious.
* Meaningful names; one job per function.
* Keep `README.md` in step with any change to endpoints, seed data or settings.
