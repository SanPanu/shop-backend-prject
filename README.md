# Practice Shop API

A small e-commerce backend built to be tested: products, cart, coupons, mock checkout, orders, and a reset endpoint.

## Run

```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Shop UI: http://127.0.0.1:8000/
Interactive API docs: http://127.0.0.1:8000/docs

The UI is one file, `app/static/index.html`. Every control has a `data-testid` attribute for automation.

It uses a local SQLite file by default. To use MySQL, create an empty database and set:

```
DATABASE_URL=mysql+pymysql://USER:PASSWORD@localhost:3306/shop
```

Tables and seed data are created on first start.

## Run the tests

```
pytest
```

- `tests/test_cases_api.py` and `tests/test_cases_ui.py` are the documented test cases (IDs TC-...).
  Each run rewrites `test-report/test_cases.csv` with every case, its steps, expected result, status and actual result.
- A failing case there is a defect in the shop, not a broken test. `test-report/Practice-Shop-Test-Cases.xlsx`
  holds the latest full run with a summary and the list of defects found and fixed.
- The browser cases need Playwright. Without it they are reported as Skipped. To install it once:

```
pip install playwright
playwright install chromium
```

- `tests/test_shop.py` and `tests/test_agent.py` are quick developer checks and are not in the report.

### CI

`.github/workflows/playwright.yml` runs `tests/test_cases_ui.py` on every push to `main`. The HTML report
(`playwright-report/index.html`, made with `pytest-html`) and `test_cases.csv` / `results.json` are uploaded as the
`playwright-report` artifact of the run. To make the same HTML report locally:

```
pip install pytest-html
pytest tests/test_cases_ui.py --html=playwright-report/index.html --self-contained-html
```

## Seed data (restored by `POST /test/reset`)

| Users | Password |
|---|---|
| alice@example.com, bob@example.com | Password123 |

| Coupon | Behaviour |
|---|---|
| WELCOME10 | 10% off, no minimum |
| FLAT200 | 200 off, minimum order 1500 |
| EXPIRED50 | expired, always rejected |
| DISABLED20 | inactive, always rejected |

30 products in 10 categories. Product 8 is out of stock and product 10 has only 2 units, for stock tests.
Prices are whole rupees. Each product has a selling price and a list price (`mrp`); the discount shown is derived from the two.
Ratings and review counts are fixed seed values; there is no review feature.

Product pictures are line icons. To use a real photo, set a product's `image` in `app/seed.py` to an image URL.

## Search

`q` matches part of a word in the product name, category or specs, ignoring letter case. With several words, every
word must match. So `mob` finds the Mobiles category's products and `amoled` finds the phone whose specs mention it.

`GET /products/suggest?q=mob` feeds the list under the search box. It needs at least 2 characters and returns matching
categories, up to `limit` products (default 6, best matches first) and the total number of matching products.

## Checkout

The web checkout has three steps: Shipping, Payment, Review. `POST /checkout` needs a `card_number` and a `shipping` object:

```
{"card_number": "4111111111111111", "coupon_code": "WELCOME10",
 "shipping": {"email": "a@example.com", "full_name": "Asha Rao", "line1": "12 MG Road", "line2": "",
              "city": "Bengaluru", "state": "Karnataka", "postal_code": "560001", "country": "India"}}
```

Delivery is to India only, the PIN code must be 6 digits not starting with 0, and shipping is free.
"Save this information for next time" stores the address in that browser only.

## Mock payment

Any 16-digit card number succeeds, except `4000000000000002`, which is always declined (HTTP 402).

## Chat agent

The chat agent is switched off by default. To show the "Shopping assistant" button, start the server with
`export AGENT_ENABLED=true` as well as a key (below).

The "Shopping assistant" button opens a chat. The agent can search products, change the cart, check coupons,
and view or cancel orders. It cannot check out or take payment.

It needs a model to think with. The default is Google's Gemini API, which has a free tier.
Create a key at https://aistudio.google.com/apikey, then in the same Terminal window, before starting the server:

```
export GEMINI_API_KEY="your-key"
uvicorn app.main:app --reload
```

Google can use free-tier content to improve its products, so do not type real personal details into the chat.

| Setting | Purpose |
|---|---|
| `GEMINI_API_KEY` | Use Gemini (default model `gemini-flash-latest`) |
| `ANTHROPIC_API_KEY` | Use Claude instead (paid; default model `claude-haiku-4-5-20251001`) |
| `AGENT_BASE_URL` + `AGENT_MODEL` (+ `AGENT_API_KEY`) | Any other OpenAI-compatible service, such as Groq or a local Ollama server |
| `AGENT_MODEL` | Override the model name |
| `AGENT_PROVIDER` | Force `gemini`, `anthropic` or `openai` when more than one key is set |

`GET /agent/status` shows which provider and model are active.
Without any key the shop works normally and the chat replies that it is not configured.

Every tool call the agent makes is stored and shown on the Activity page (`/#/assistant`) and at `GET /agent/actions`,
so a test can check what the agent did, not only what it said. `tests/test_agent.py` shows how to replace the model
with a scripted one for repeatable tests.

## WebSphere and Oracle build

The `websphere` folder holds a Java version of the shop for IBM WebSphere 9.0 with an Oracle database:
`practice-shop.war`, the Oracle scripts, and `README-DEPLOY.md` with the installation steps.

To run the documented API cases against a shop running elsewhere (for example that build):

```
SHOP_BASE_URL=http://washost:9080/shop pytest tests/test_cases_api.py
```

## Endpoints

| Area | Endpoints |
|---|---|
| System | `GET /health`, `POST /test/reset` |
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /me` |
| Products | `GET /products` (q, category, min_price, max_price, in_stock, sort, limit), `GET /products/suggest` (q, limit), `GET /products/{id}`, `GET /categories` |
| Cart | `GET /cart`, `POST /cart/items`, `PUT /cart/items/{product_id}`, `DELETE /cart/items/{product_id}`, `DELETE /cart` |
| Checkout | `POST /coupons/validate`, `GET /shipping/options`, `POST /checkout` |
| Orders | `GET /orders`, `GET /orders/{id}`, `POST /orders/{id}/cancel` |
| Agent | `GET /agent/status`, `POST /agent/chat`, `GET /agent/actions` |

Send the login token as `Authorization: Bearer <token>`.

`POST /test/reset` needs the header `X-Reset-Key: practice-reset`. Set `RESET_KEY` to choose your own key, or
`ALLOW_RESET=false` to disable the endpoint.

`POST /auth/logout` ends the current session.
