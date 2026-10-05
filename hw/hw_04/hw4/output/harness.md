# Campus Customs — Agent Harness

How the Campus Customs website and its chatbot are put together: the data
they rely on, the agent's structured outputs, its tools, its safety rules,
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
| `product_id` | text, primary key | Unique slug, e.g. `yale-mom-hoodie` | |
| `name` | text | Display name | |
| `garment_type` | text | Kind of garment, e.g. `pullover hoodie` (22 inconsistent labels) | |
| `description` | text | One-sentence visual description | |
| `colors` | text (JSON list) | e.g. `["navy", "white"]`; 3 products have `[]` | |
| `search_tags` | text (JSON list) | 4–12 keywords per product | |
| `image_file_path` | text | `products/<product_id>.jpg`, relative to `data/` | |
| `price` | real | One price per product, $32–$98 | |

### `inventory` — stock on hand (612 rows = 102 products × 6 sizes)

| Field | Type | What it holds | Why it matters (shop / chatbot) |
|---|---|---|---|
| `id` | integer, primary key | Row number | |
| `product_id` | text → `catalogue` | Which product | |
| `size` | text | One of XS, S, M, L, XL, XXL | |
| `quantity` | integer | Units on hand, 0–25; 145 rows are 0 | |

### `users` — customer accounts (3 rows)

| Field | Type | What it holds | Why it matters (shop / chatbot) |
|---|---|---|---|
| `id` | integer, primary key | Account number | |
| `name` | text | Full name | |
| `first_name` | text | Added after the table was created | |
| `last_name` | text | Added after the table was created | |
| `email` | text, unique | Login identifier | |
| `password_hash` | text | `pbkdf2_sha256$<salt>$<hash>`; never the real password | |
| `created_at` | text (timestamp) | When the account was made | |

### `chat_messages` — conversation history (22 rows from a reference run)

| Field | Type | What it holds | Why it matters (shop / chatbot) |
|---|---|---|---|
| `id` | integer, primary key | Message number | |
| `user_id` | integer → `users` | Whose conversation | |
| `role` | text | `user` or `assistant` | |
| `content` | text | The message text | |
| `products_json` | text (JSON list) | Full product objects shown with an assistant reply | |
| `created_at` | text (timestamp) | When it was sent | |

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

## 2. Models — *to come (P5–P7)*

## 3. Tools — *to come (P6–P7)*

## 4. Safety — *to come (P12)*

## 5. Specs and limits — *to come (P12)*
