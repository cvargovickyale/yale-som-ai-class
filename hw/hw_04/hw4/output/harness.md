# Campus Customs — Agent Harness

How the Campus Customs website and its chatbot are put together: the data
they rely on, how accounts work, the agent's structured outputs, its tools, its safety rules,
and its limits. Built up one problem at a time, then consolidated at the end.

## 1. Data (`data/campus_customs.db`)

SQLite database with four tables. The database and product images stay
local and are never committed to git.

```
catalogue (102)  ──product_id──▶  inventory (612)
  one row per product               one row per product + size

users (3)  ──id = user_id──▶  chat_messages (22)
  one row per account             one row per chat message
```

### `catalogue` — what the store sells (102 rows, one per product)

| Field | Type | What it holds | Why it matters (shop / chatbot) |
|---|---|---|---|
| `product_id` | text, primary key | Unique slug, e.g. `yale-mom-hoodie` | The key everything links to. `inventory` rows, the image file name, and the products the chatbot returns all point back to a product by this ID, which is how a chat answer turns into product cards on the page. |
| `name` | text | Display name | Need to know what we're buying and selling. It's the label on the product card and the name the bot uses in replies. |
| `garment_type` | text | Kind of garment, e.g. `pullover hoodie` (22 inconsistent labels) | Classification by category, so shoppers and the bot can narrow to hoodies, crewnecks, etc. The labels are inconsistent (see quirks), so treat this as a hint, not an exact filter. |
| `description` | text | One-sentence visual description | Searchable in a way images aren't. The bot can match requests like "kangaroo pocket" or "arched lettering" against this text. |
| `colors` | text (JSON list) | e.g. `["navy", "white"]`; 3 products have `[]` | Necessary product detail. Answers "do you have it in pink?" straight from the data. |
| `search_tags` | text (JSON list) | 4–12 keywords per product | Simpler than starting fresh with image recognition every time. The keywords were already pulled from the photos, so matching is fast. |
| `image_file_path` | text | `products/<product_id>.jpg`, relative to `data/` | Necessary visual for a visual product. The backend serves this file so each card shows the garment. |
| `price` | real | One price per product, $32–$98 | Critical consumer information and financial data. Must come from here, never from the model. |

### `inventory` — stock on hand (612 rows = 102 products × 6 sizes)

| Field | Type | What it holds | Why it matters (shop / chatbot) |
|---|---|---|---|
| `id` | integer, primary key | Row number | Row bookkeeping. Shoppers never see it. |
| `product_id` | text → `catalogue` | Which product | Ties each stock count back to its catalogue product. |
| `size` | text | One of XS, S, M, L, XL, XXL | Stock is per size, so "is it in stock?" depends on which size. |
| `quantity` | integer | Units on hand, 0–25; 145 rows are 0 | The real stock answer. 0 means sold out in that size. The bot reads it; it never guesses. |

### `users` — customer accounts (3 rows in the seed data)

| Field | Type | What it holds | Why it matters (shop / chatbot) |
|---|---|---|---|
| `id` | integer, primary key | Account number | Links an account to its chat history. |
| `name` | text | Full name | Who the customer is. |
| `first_name` | text | Added after the table was created | Lets the site and the bot greet them by name ("Hi, Test!"). |
| `last_name` | text | Added after the table was created | Completes the name. Mostly duplicates `name`. |
| `email` | text, unique | Login identifier | Login identifier, unique, so one account per email. Personal data: keep it out of chat and out of git. |
| `password_hash` | text | `pbkdf2_sha256$<salt>$<hash>`; never the real password | Checks the password without storing it. Login hashes what's typed and compares. Never shown to anyone, including the bot. |
| `created_at` | text (timestamp) | When the account was made | When they joined. Record-keeping; the bot doesn't need it. |

### `chat_messages` — conversation history (22 rows from a reference run)

| Field | Type | What it holds | Why it matters (shop / chatbot) |
|---|---|---|---|
| `id` | integer, primary key | Message number | Keeps messages in order. |
| `user_id` | integer → `users` | Whose conversation | Whose conversation. Memory is per customer. |
| `role` | text | `user` or `assistant` | Who said it, shopper or bot, so the history replays correctly. |
| `content` | text | The message text | What was said. Lets the bot remember context, like what "this" refers to. |
| `products_json` | text (JSON list) | Full product objects shown with an assistant reply | Tells us which products were referenced or returned, so a past chat can show the same product cards again. |
| `created_at` | text (timestamp) | When it was sent | When it was sent. Used for ordering and the audit trail. |

(`sqlite_sequence` is SQLite's own internal counter for auto-numbered IDs,
not store data.)

### Data quirks to handle

- **`garment_type` is inconsistent.** There are 22 labels for what a
  shopper would call about 8 kinds of garment. Hoodies alone span 5 labels
  ("pullover hoodie", "hoodie", "hooded sweatshirt", …) and 3 prices, so
  search can't rely on exact label matches.
- **Stock is per size.** No product is fully sold out, but 145 of the 612
  size rows are 0.
- **Links between tables are not enforced** (SQLite foreign keys are off).
  There are no orphan rows today.
- **One product ID has a built-in typo** (`yale-sports-creqneck-field-hockey`).
  The image file uses the same spelling, so leave it.

## 2. Accounts and login

Shoppers can browse without an account. An account lets the site (and, from
P8, the chatbot) know who they are. All account logic is plain backend code
in `backend/main.py`. **No AI model ever sees a password, a password hash,
or a login token.**

### How it works

1. **Create account:** the shopper enters first name, last name, email,
   password, and confirm password. The page checks that the passwords match
   and are at least 8 characters, then sends them to `POST /api/auth/signup`.
   The backend checks everything again (it never trusts the page), lowercases
   the email, rejects an email that's already registered, hashes the
   password, and inserts a new `users` row.
2. **Log in:** email and password go to `POST /api/auth/login`. The backend
   finds the user by email, hashes the typed password with that user's
   stored salt, and compares the result to the stored hash.
3. **Staying logged in:** on success the backend returns a signed login
   token (a JWT) that expires after 24 hours. The browser keeps it and sends
   it with each request as `Authorization: Bearer <token>`. `GET /api/auth/me`
   turns a valid token back into the user's name and email. Logging out
   deletes the token from the browser.

### Password hashing

| Setting | Value |
|---|---|
| Method | PBKDF2-HMAC-SHA256 |
| Iterations | 120,000 |
| Salt | 16 random hex characters per user, used as text |
| Stored format | `pbkdf2_sha256$<salt>$<64-hex-character hash>` |

This is the same format the seed database already used. New accounts are
hashed exactly the way the seed users were, so old and new accounts log in
through one code path. The iteration count isn't written in the stored
string, so I confirmed it by reproducing the seed test user's stored hash
from its known password.

A hash is one-way. The backend can check whether a typed password is right,
but nobody (a person, an AI, or the backend itself) can turn the stored
hash back into the password. The random salt means two people with the
same password still get different hashes.

### What gets stored, and who can read it

| Data | Where | Stored as | Who can read it |
|---|---|---|---|
| First name, last name | `users` table | Plain text | The backend; the logged-in user sees their own name |
| Email | `users` table | Plain text, lowercased | The backend; the logged-in user sees their own email |
| Password | Nowhere | Never stored, logged, or sent back | Nobody. It exists only for the moment it's checked. |
| Password hash | `users.password_hash` | PBKDF2 hash | The backend only. Never returned by any API endpoint. |
| Login token | The shopper's browser (`localStorage`) | Signed JWT holding only the user ID and expiry | That browser; the backend verifies the signature |
| Token signing secret | `.env` (`JWT_SECRET`) | Plain text, never committed | The backend |

### Protections built in

- **Same error for a wrong email and a wrong password** ("Incorrect email
  or password"), so the login form can't be used to find out who has an
  account. An unknown email is still checked against a dummy hash, so it
  takes as long as a wrong password.
- **Validation errors never echo what was typed.** FastAPI's default error
  response repeats the request body, which would send passwords back. A
  custom handler returns only the field name and the message.
- **One account per email:** the email is lowercased and must be unique.
- **The database file is never served or committed.** Only
  `data/products/` is public, and `data/` is in `.gitignore`.
- **Read-only by default:** the backend opens the database read-only for
  everything except inserting a new account.

### Known limits (honest list)

- **Emails and names are plain text.** Anyone holding the `.db` file can
  read them. Only passwords are protected by hashing.
- **120,000 iterations is below today's guidance** (OWASP recommends
  600,000 for PBKDF2-SHA256). I kept it to match the seed data. The fix
  would be storing the iteration count in the hash and re-hashing each user
  at their next login.
- **No lockout or rate limit** on repeated login attempts.
- **The token lives in `localStorage`,** which any script running on the
  page can read. That's fine for a class project; a production site would
  use an HTTP-only cookie.
- **No password reset or email verification.**
- **If `JWT_SECRET` isn't set,** the backend makes a random one at startup,
  so everyone is logged out whenever the server restarts.

## 3. Models — *to come (P5–P7)*

## 4. Tools — *to come (P6–P7)*

## 5. Safety — *to come (P12)*

## 6. Specs and limits — *to come (P12)*
