# Practice Shop — Login Test Scenarios

Generated: 2026-10-11
Scope: Login (Log In, Log Out, Remember Me, Session Handling, Login Page)

---

## Happy Path

### TC-001: Log in with valid credentials from the login page
**Category**: Happy Path
**Priority**: P0
**Preconditions**: User is logged out; seed account `alice@example.com` / `Password123` exists
**Steps**:
1. Navigate to `#/login`
2. Enter `alice@example.com` in `login-email` and `Password123` in `login-password`
3. Click `login-submit`
**Expected Results**: User is sent to `#/`; the header shows `user-name` "Alice" and a "Log out" button (`logout`); the "Login / Sign Up" link (`nav-login`) is gone
**Business Rule**: `POST /auth/login` returns a token; the form submit handler calls `store.save` then `go(back)`
**Suggested Layer**: E2E

---

### TC-002: Log in via API returns a token and the user
**Category**: Happy Path
**Priority**: P0
**Preconditions**: Seed account `alice@example.com` exists
**Steps**:
1. Send `POST /auth/login` with `{"email": "alice@example.com", "password": "Password123"}`
2. Send `GET /me` with `Authorization: Bearer <token>`
**Expected Results**: Step 1 returns 200 with `token` (48 hex characters) and `user` `{id, email, name}`; step 2 returns 200 with `email: "alice@example.com"` and `name: "Alice"`
**Business Rule**: `issue_token` — `secrets.token_hex(24)`, returns `{"token", "user": {"id", "email", "name"}}`
**Suggested Layer**: API

---

### TC-003: Log out from the header
**Category**: Happy Path
**Priority**: P0
**Preconditions**: User is logged in through the UI
**Steps**:
1. Click "Log out" (`logout`) in the header
2. Observe the page and the header
**Expected Results**: User is sent to `#/`; the header shows "Login / Sign Up" (`nav-login`); the cart badge (`cart-count`) shows 0; no message is shown
**Business Rule**: `logout` action — `store.save(null, null)`, `setCoupon(null)`, `go('#/')`, then `POST /auth/logout`
**Suggested Layer**: E2E

---

### TC-004: Log out via API
**Category**: Happy Path
**Priority**: P0
**Preconditions**: User has a valid token
**Steps**:
1. Send `POST /auth/logout` with the token
2. Send `GET /me` with the same token
**Expected Results**: Step 1 returns 200 `{"status": "logged out"}`; step 2 returns 401 "Invalid token"
**Business Rule**: `logout` deletes the `Token` row — "the token stops working straight away"
**Suggested Layer**: API

---

### TC-005: Login returns the user to the page that asked for login
**Category**: Happy Path
**Priority**: P1
**Preconditions**: User is logged out
**Steps**:
1. Navigate to `#/orders`
2. Observe the redirect and message
3. Log in as `alice@example.com` / `Password123`
**Expected Results**: Step 2: user is on `#/login` with the message "Please log in first."; after login the user lands back on `#/orders`
**Business Rule**: `needLogin` stores `returnTo = location.hash`; after login `go(returnTo)`
**Suggested Layer**: E2E

---

### TC-006: Open the login page from the header link
**Category**: Happy Path
**Priority**: P2
**Preconditions**: User is logged out, on `#/`
**Steps**:
1. Click "Login / Sign Up" (`nav-login`)
**Expected Results**: User is on `#/login`; `login-page` and `login-form` are visible; heading "Login to Practice Shop"; browser tab title is "Login – Practice Shop"
**Business Rule**: `showAuth('login')` and `setTitle('Login')`
**Suggested Layer**: E2E

---

### TC-007: Switch between login and sign-up pages
**Category**: Happy Path
**Priority**: P2
**Preconditions**: User is on `#/login`
**Steps**:
1. Click "Sign Up" (`link-signup`)
2. Click "Login" (`link-login`)
**Expected Results**: Step 1 shows `#/signup` with `register-form`; step 2 returns to `#/login` with `login-form`
**Business Rule**: `showAuth(mode)` renders one form per route
**Suggested Layer**: E2E

---

## Business Rules

### TC-100: Email is not case-sensitive at login
**Category**: Business Rule
**Priority**: P0
**Preconditions**: Seed account `alice@example.com` exists
**Steps**:
1. Send `POST /auth/login` with `email: "ALICE@Example.COM"` and `password: "Password123"`
**Expected Results**: 200 with a token; `user.email` is `alice@example.com`
**Business Rule**: `login` looks up `body.email.lower()`; `register` stores emails in lower case
**Suggested Layer**: API

---

### TC-101: Password is case-sensitive
**Category**: Business Rule
**Priority**: P0
**Preconditions**: Seed account `alice@example.com` exists
**Steps**:
1. Send `POST /auth/login` with `password: "password123"`
2. Send `POST /auth/login` with `password: "PASSWORD123"`
**Expected Results**: 401 "Wrong email or password" for both
**Business Rule**: `login` compares `hash_password(body.password)`; the password is not changed before hashing
**Suggested Layer**: API

---

### TC-102: Password with surrounding spaces is not trimmed
**Category**: Business Rule
**Priority**: P1
**Preconditions**: Seed account `alice@example.com` exists
**Steps**:
1. Log in with password `" Password123"`, then `"Password123 "`, via API and via the UI
**Expected Results**: 401 "Wrong email or password" in every case; in the UI the message appears under the password field
**Business Rule**: Neither `login` nor the UI submit handler trims the password (`password: f.password`)
**Suggested Layer**: API / E2E

---

### TC-103: Email with surrounding spaces — UI trims, API does not
**Category**: Business Rule
**Priority**: P1
**Preconditions**: Seed account `alice@example.com` exists
**Steps**:
1. In the UI, enter `"  alice@example.com  "` and `Password123`, click `login-submit`
2. Send `POST /auth/login` with `email: "  alice@example.com  "`
**Expected Results**: Step 1 logs in (UI sends `f.email.trim()`); step 2 returns 401 "Wrong email or password" (API only lower-cases)
**Business Rule**: UI submit handler trims the email; `login` uses `body.email.lower()` without trimming
**Suggested Layer**: E2E / API

---

### TC-104: Each login creates a separate session; logout ends only that one
**Category**: Business Rule
**Priority**: P1
**Preconditions**: Seed account `alice@example.com` exists
**Steps**:
1. Log in twice via API; keep token A and token B
2. Send `POST /auth/logout` with token A
3. Send `GET /me` with token A and with token B
**Expected Results**: Tokens A and B differ; after logout token A gets 401 "Invalid token" and token B still gets 200
**Business Rule**: `issue_token` adds a new `Token` row on every login; `logout` deletes only the token in the header
**Suggested Layer**: API

---

### TC-105: "Remember me" checked keeps the session after the tab is closed
**Category**: Business Rule
**Priority**: P1
**Preconditions**: User is logged out
**Steps**:
1. On `#/login`, leave `login-remember` checked (default) and log in
2. Close the tab, open the shop in a new tab
**Expected Results**: User is still logged in (`user-name` shows "Alice"); token is in `localStorage`
**Business Rule**: `store.save(token, name, persist)` — `persist` true writes to `localStorage`
**Suggested Layer**: E2E

---

### TC-106: "Remember me" unchecked ends the session when the tab is closed
**Category**: Business Rule
**Priority**: P1
**Preconditions**: User is logged out
**Steps**:
1. On `#/login`, uncheck `login-remember` and log in
2. Open the shop in a new tab (new browser context page)
**Expected Results**: Original tab is logged in; token is in `sessionStorage`, not `localStorage`; the new tab shows "Login / Sign Up"
**Business Rule**: `store.save(..., persist=false)` writes to `sessionStorage`: "otherwise it lasts until the tab is closed"
**Suggested Layer**: E2E

---

### TC-107: Logout clears the applied coupon
**Category**: Business Rule
**Priority**: P2
**Preconditions**: User is logged in, has a product in the cart and coupon `WELCOME10` applied
**Steps**:
1. Click "Log out"
2. Log in again and open `#/cart`
**Expected Results**: No coupon is applied; `localStorage` key `coupon` is removed
**Business Rule**: `logout` action calls `setCoupon(null)` — "remembered ... until it is removed, used, or the shopper logs out"
**Suggested Layer**: E2E

---

### TC-108: Cart is kept between logout and the next login
**Category**: Business Rule
**Priority**: P2
**Preconditions**: User is logged in with 2 items in the cart
**Steps**:
1. Log out
2. Log in again as the same user
**Expected Results**: Cart badge (`cart-count`) shows 2 and `#/cart` lists the same items
**Business Rule**: Cart rows belong to the user, not the token; `logout` deletes only the `Token` row
**Suggested Layer**: E2E / API

---

## Security

### TC-200: Wrong password and unknown email give the same answer
**Category**: Security
**Priority**: P0
**Preconditions**: Seed account `alice@example.com` exists
**Steps**:
1. Send `POST /auth/login` with `alice@example.com` and a wrong password
2. Send `POST /auth/login` with `nobody@example.com` and any password
**Expected Results**: Both return 401 with the identical body `{"detail": "Wrong email or password"}`; the response does not reveal whether the email exists
**Business Rule**: `login` raises one error for `user is None` or a wrong password
**Suggested Layer**: API

---

### TC-201: Login response does not contain the password or its hash
**Category**: Security
**Priority**: P0
**Preconditions**: Seed account exists
**Steps**:
1. Send `POST /auth/login` with valid credentials
2. Inspect the full response body
**Expected Results**: Body contains only `token` and `user` (`id`, `email`, `name`); no `password` or `password_hash`
**Business Rule**: `issue_token` builds the response from three user fields only
**Suggested Layer**: API

---

### TC-202: SQL injection text in email is treated as plain text
**Category**: Security
**Priority**: P0
**Preconditions**: None
**Steps**:
1. Send `POST /auth/login` with `email: "' OR '1'='1"` and `password: "' OR '1'='1"`
2. Send `POST /auth/login` with `email: "alice@example.com' --"` and any password
**Expected Results**: 401 "Wrong email or password" for both; never 200 or 500
**Business Rule**: `login` uses a SQLAlchemy `select(...).where(User.email == ...)` with bound parameters
**Suggested Layer**: API

---

### TC-203: Logged-out token cannot be reused
**Category**: Security
**Priority**: P0
**Preconditions**: User has a valid token
**Steps**:
1. Send `POST /auth/logout` with the token
2. Send `GET /cart`, `GET /orders` and `POST /auth/logout` with the same token
**Expected Results**: All return 401 "Invalid token"
**Business Rule**: `current_user` — `db.get(Token, ...)` is `None` → 401 "Invalid token"
**Suggested Layer**: API

---

### TC-204: Protected endpoints reject a missing or malformed Authorization header
**Category**: Security
**Priority**: P0
**Preconditions**: None
**Steps**:
1. Send `GET /me` with no header, with `Token abc`, with `Bearer`, and with `bearer <valid token>` (lower-case scheme)
2. Send `GET /me` with `Bearer not-a-token`
**Expected Results**: Step 1: 401 "Missing bearer token" for each; step 2: 401 "Invalid token"
**Business Rule**: `current_user` requires the header to start with `"Bearer "` (case-sensitive) and the token to exist
**Suggested Layer**: API

---

### TC-205: Logout on the UI also ends the session on the server
**Category**: Security
**Priority**: P1
**Preconditions**: User is logged in through the UI
**Steps**:
1. Read the token from `localStorage`
2. Click "Log out"
3. Send `GET /me` with the saved token
**Expected Results**: 401 "Invalid token"
**Business Rule**: `logout` action sends `POST /auth/logout` with the old token
**Suggested Layer**: E2E / API

---

### TC-206: No lockout after repeated wrong passwords
**Category**: Security
**Priority**: P2
**Preconditions**: Seed account `alice@example.com` exists
**Steps**:
1. Send `POST /auth/login` with a wrong password 20 times
2. Send `POST /auth/login` with the correct password
**Expected Results**: Every wrong attempt returns 401; the correct attempt returns 200. The code has no rate limit or lockout; report as a security risk if one is required
**Business Rule**: `login` has no attempt counter
**Suggested Layer**: API

---

### TC-207: Password field is masked and can be shown on request
**Category**: Security
**Priority**: P2
**Preconditions**: User is on `#/login`
**Steps**:
1. Type a password into `login-password`
2. Click `toggle-password`, then click it again
**Expected Results**: Input starts as `type="password"`; first click shows the text and the button label becomes "Hide password"; second click masks it again with label "Show password"
**Business Rule**: `toggle-pw` action switches `input.type` and `aria-label`
**Suggested Layer**: E2E

---

## Negative / Error

### TC-300: Wrong password shows the error under the password field
**Category**: Negative
**Priority**: P0
**Preconditions**: User is on `#/login`
**Steps**:
1. Enter `alice@example.com` and `WrongPass1`
2. Click `login-submit`
**Expected Results**: "Wrong email or password" appears under the password field (`error-login-password`); password field is focused and marked `aria-invalid`; user stays on `#/login`; no page-level banner
**Business Rule**: Submit handler — `err.status === 401` → `fieldError(form.elements.password, err.message)`
**Suggested Layer**: E2E

---

### TC-301: Unknown email shows the same error as a wrong password
**Category**: Negative
**Priority**: P1
**Preconditions**: User is on `#/login`
**Steps**:
1. Enter `nobody@example.com` and `Password123`
2. Click `login-submit`
**Expected Results**: "Wrong email or password" under the password field; no error under the email field
**Business Rule**: `login` → 401 "Wrong email or password"
**Suggested Layer**: E2E

---

### TC-302: Submitting an empty login form
**Category**: Negative
**Priority**: P0
**Preconditions**: User is on `#/login`
**Steps**:
1. Leave both fields empty and click `login-submit`
**Expected Results**: "Enter your email address" under the email field and "Enter your password" under the password field; email field is focused; no request is sent to `/auth/login`
**Business Rule**: `RULES['login-form']` and `validateForm` — all errors shown at once, focus on the first wrong field
**Suggested Layer**: E2E

---

### TC-303: Badly formed email is rejected before sending
**Category**: Negative
**Priority**: P1
**Preconditions**: User is on `#/login`
**Steps**:
1. Enter each of `plain`, `a@b`, `@b.com`, `a b@c.com`, `a@b..c` as email, with any password
2. Click `login-submit`
**Expected Results**: "Enter a valid email address, like name@example.com" under the email field each time; no request is sent
**Business Rule**: `emailRule` with `EMAIL_RE = /^[^@\s]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$/`
**Suggested Layer**: E2E

---

### TC-304: Login API with missing or wrong-typed fields returns 422
**Category**: Negative
**Priority**: P1
**Preconditions**: None
**Steps**:
1. Send `POST /auth/login` with `{}`
2. Send with only `email`
3. Send with only `password`
4. Send with `email: null` or `email: 123`
**Expected Results**: HTTP 422 for each, naming the missing or invalid field; never 500
**Business Rule**: `LoginIn` — `email: str`, `password: str`, both required
**Suggested Layer**: API

---

### TC-305: Empty strings via API return 401, not 422
**Category**: Negative
**Priority**: P2
**Preconditions**: None
**Steps**:
1. Send `POST /auth/login` with `{"email": "", "password": ""}`
**Expected Results**: HTTP 401 "Wrong email or password" (`LoginIn` has no length or pattern rules)
**Business Rule**: `LoginIn` accepts any string; the lookup finds no user
**Suggested Layer**: API

---

### TC-306: Logout without a token returns 401
**Category**: Negative
**Priority**: P1
**Preconditions**: None
**Steps**:
1. Send `POST /auth/logout` with no Authorization header
2. Send `POST /auth/logout` with `Bearer not-a-token`
**Expected Results**: Step 1: 401 "Missing bearer token"; step 2: 401 "Invalid token"
**Business Rule**: `logout` depends on `current_user`
**Suggested Layer**: API

---

### TC-307: Login page shows an error when the server is unreachable
**Category**: Negative
**Priority**: P2
**Preconditions**: Login page is open; backend server is then stopped
**Steps**:
1. Enter valid credentials and click `login-submit`
**Expected Results**: A plain-language error message is shown and the user stays on `#/login`. Current behaviour: `act` shows `e.message` of the failed `fetch`, so a raw browser message such as "Failed to fetch" is expected — a defect to report
**Business Rule**: Error text shown to users must be plain language
**Suggested Layer**: E2E

---

## Edge Cases

### TC-400: Very long email and password do not crash the server
**Category**: Edge Case
**Priority**: P2
**Preconditions**: None
**Steps**:
1. Send `POST /auth/login` with a 10,000-character email
2. Send `POST /auth/login` with `alice@example.com` and a 10,000-character password
**Expected Results**: HTTP 401 "Wrong email or password" for both; never 500
**Business Rule**: `LoginIn` has no `max_length`; the lookup and hash simply fail to match
**Suggested Layer**: API

---

### TC-401: Unicode and special characters in the password
**Category**: Edge Case
**Priority**: P2
**Preconditions**: A user registered with password `Pässwörd✓123`
**Steps**:
1. Log in with `Pässwörd✓123`
2. Log in with `Passwörd✓123` (one character different)
**Expected Results**: Step 1 returns 200; step 2 returns 401
**Business Rule**: `hash_password` encodes the password as UTF-8 before PBKDF2
**Suggested Layer**: API

---

### TC-402: Failed login while already logged in ends the current session in the browser
**Category**: Edge Case
**Priority**: P1
**Preconditions**: User is logged in as Alice in the UI
**Steps**:
1. Navigate to `#/login`
2. Enter `bob@example.com` and a wrong password, click `login-submit`
3. Observe the header
**Expected Results**: "Wrong email or password" under the password field. Current behaviour: the header switches to "Login / Sign Up" because `api()` treats any 401 with a stored token as an ended session and clears it; Alice's token remains valid on the server. Report if the existing session should survive a failed login
**Business Rule**: `api()` — `expired = res.status === 401 && !!store.token` → `store.save(null, null)`
**Suggested Layer**: E2E

---

### TC-403: Logging in as another user while logged in replaces the session
**Category**: Edge Case
**Priority**: P2
**Preconditions**: User is logged in as Alice in the UI; Alice's token is noted
**Steps**:
1. Navigate to `#/login` (the page is shown even when logged in)
2. Log in as `bob@example.com` / `Password123`
3. Send `GET /me` with Alice's noted token
**Expected Results**: Header shows "Bob"; cart shows Bob's cart. Alice's old token still returns 200 because the switch does not call `POST /auth/logout`
**Business Rule**: `store.save` overwrites the stored token; no logout call is made for the old one
**Suggested Layer**: E2E / API

---

### TC-404: Return page after login is never the login or sign-up page
**Category**: Edge Case
**Priority**: P2
**Preconditions**: User is logged out
**Steps**:
1. Navigate directly to `#/login` and log in
2. Log out, navigate to `#/signup`, click `link-login`, log in
**Expected Results**: Both logins land on `#/`
**Business Rule**: `back = returnTo && !/^#\/(login|signup)/.test(returnTo) ? returnTo : '#/'`
**Suggested Layer**: E2E

---

### TC-405: Clicking "Add to cart" while logged out returns to the product after login
**Category**: Edge Case
**Priority**: P1
**Preconditions**: User is logged out, on `#/p/1`
**Steps**:
1. Click the add to cart button
2. Log in as `alice@example.com`
**Expected Results**: Step 1 shows `#/login` with "Please log in first."; after login the user is back on `#/p/1`; the product was not added automatically
**Business Rule**: `add` action calls `needLogin()`, which stores `returnTo` and returns before adding
**Suggested Layer**: E2E

---

### TC-406: Logging out in one tab logs out other tabs on their next action
**Category**: Edge Case
**Priority**: P2
**Preconditions**: User logged in with "Remember me"; the shop is open in two tabs
**Steps**:
1. Click "Log out" in tab 1
2. In tab 2 click "Orders" (or any page needing login)
**Expected Results**: Tab 2 is sent to `#/login` with "Please log in first." (the token was removed from the shared `localStorage`)
**Business Rule**: `store.token` reads `localStorage` on every access; `needLogin` checks it
**Suggested Layer**: E2E

---

### TC-407: Double-clicking the login button
**Category**: Edge Case
**Priority**: P2
**Preconditions**: User is on `#/login` with valid credentials entered
**Steps**:
1. Double-click `login-submit`
2. Count `POST /auth/login` requests and observe the page
**Expected Results**: User is logged in and lands on one page with no error. The button is not disabled while waiting, so two requests (and two tokens) may be created; report if only one session is expected
**Business Rule**: Submit handler has no in-flight guard; each login issues a new token
**Suggested Layer**: E2E

---

## UI State

### TC-500: Logged-out visit to a protected page redirects to login
**Category**: UI State
**Priority**: P0
**Preconditions**: User is not logged in
**Steps**:
1. Navigate to `#/cart`, `#/checkout`, `#/orders` in turn
**Expected Results**: Each sends the user to `#/login` with the message "Please log in first." in `message`
**Business Rule**: `needLogin` in `showCart`, `showCheckout`, `showOrders`
**Suggested Layer**: E2E

---

### TC-501: Field error appears when leaving a field and clears while correcting it
**Category**: UI State
**Priority**: P1
**Preconditions**: User is on `#/login`
**Steps**:
1. Type `alice@` in `login-email` and press Tab
2. Continue typing to `alice@example.com`
**Expected Results**: Step 1 shows "Enter a valid email address, like name@example.com" under the email field; during step 2 the message disappears as soon as the value is valid
**Business Rule**: `focusout` runs `checkField` for non-empty fields; `input` re-checks fields marked `aria-invalid`
**Suggested Layer**: E2E

---

### TC-502: Leaving an empty field before the first submit shows no error
**Category**: UI State
**Priority**: P2
**Preconditions**: User is on a freshly loaded `#/login`
**Steps**:
1. Click into `login-email`, then Tab out without typing
**Expected Results**: No error is shown. After one failed submit, leaving an empty field does show "Enter your email address"
**Business Rule**: `focusout` checks only when `t.value !== ''` or `form.dataset.tried` is set by `validateForm`
**Suggested Layer**: E2E

---

### TC-503: Login page default state
**Category**: UI State
**Priority**: P2
**Preconditions**: User is logged out
**Steps**:
1. Navigate to `#/login`
**Expected Results**: Side panel "Welcome Back!" / "Good to see you again!"; fields `login-email` and `login-password` are empty with placeholders "Enter your email address" and "Enter your password"; `login-remember` is checked; `toggle-password` has label "Show password"; no field errors
**Business Rule**: `showAuth('login')` markup
**Suggested Layer**: E2E

---

### TC-504: Pressing Enter in the password field submits the form
**Category**: UI State
**Priority**: P2
**Preconditions**: User is on `#/login`
**Steps**:
1. Enter valid credentials
2. Press Enter in `login-password`
**Expected Results**: User is logged in and sent to `#/`
**Business Rule**: `login-form` is a `<form>`; the `submit` listener handles it
**Suggested Layer**: E2E

---

### TC-505: Ended session during navigation sends the user to login
**Category**: UI State
**Priority**: P1
**Preconditions**: User is logged in in the browser and has already opened a page in this tab; the token is then ended on the server (`POST /auth/logout` with the same token)
**Steps**:
1. Navigate to `#/orders` from inside the open page
**Expected Results**: User is sent to `#/login` with "Your session has ended. Please log in again."; the header shows "Login / Sign Up"
**Business Rule**: `doRender` catch — `e.status === 401` sets that flash and `go('#/login')`
**Suggested Layer**: E2E

---

### TC-506: Ended session on a full page reload
**Category**: UI State
**Priority**: P2
**Preconditions**: Token stored in the browser has been ended on the server
**Steps**:
1. Reload the browser on `#/orders`
**Expected Results**: User is sent to `#/login`. Current behaviour: the message is "Please log in first." rather than "Your session has ended. Please log in again.", because the first `refreshNav` cart request clears the token silently before `showOrders` runs. Report if the session-ended message is expected here
**Business Rule**: `refreshNav` swallows errors from `GET /cart`; `api()` clears the token on 401
**Suggested Layer**: E2E

---

### TC-507: Field errors are shown under fields, never as a page banner
**Category**: UI State
**Priority**: P1
**Preconditions**: User is on `#/login`
**Steps**:
1. Submit an empty form
2. Submit a wrong password
3. Check the `message` banner after each
**Expected Results**: `message` stays empty in both cases; errors appear only in `error-login-email` / `error-login-password` with `role="alert"`
**Business Rule**: CLAUDE.md — validation errors under the field using `RULES`, `fieldError`, `validateForm`
**Suggested Layer**: E2E
