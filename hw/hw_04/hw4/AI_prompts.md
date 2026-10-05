# Homework 4 AI Prompts

Records the prompt used for each problem, plus at most one follow-up when a
correction or clarification was needed. Each prompt is typed in my own words,
one problem at a time. Coding assistant: Claude Code.

## Problem 2 — Analyze the database

**Prompt:** Help me open the database so I can understand the fields like
catalogue inventory and users

**Notes:**

- Setup: created the `hw4/` folder and placed the data pack at `hw4/data/`.
  It is excluded from git (assignment rule: never commit the DB or images).
- No LLM was used. The analysis is direct SQL against `campus_customs.db`
  with the `sqlite3` command-line tool.
- Findings that shape later problems:
  - **Tables:** `catalogue` (102 products), `inventory` (612 rows: every
    product × 6 sizes), `users` (3), and `chat_messages` (22 rows from an
    earlier reference run).
  - **Links:** `inventory.product_id` and `chat_messages.user_id` point to
    `catalogue` and `users`. SQLite doesn't enforce these links, but there
    are no orphan rows.
  - **Stock:** 145 of 612 size rows are out of stock (quantity 0). Every
    product has some stock in at least one size, so stock answers must be
    per size, not just "in stock / out of stock" (P6).
  - **Price:** set by garment family, with 7 distinct prices from $32 to
    $98. Price is per product, not per size.
  - **`garment_type` labels are inconsistent.** There are 22 different
    labels; hoodies alone appear under 5 labels at 3 prices ($45 / $68 /
    $88). A saved reference chat lists 8 hoodies "all priced at $68," but
    there are 27 hoodie-type products. Search can't rely on exact
    `garment_type` matches (P6/P7).
  - **`colors` and `search_tags`** are JSON lists stored as text. Three
    products have an empty colors list.
  - **Passwords** use the format `pbkdf2_sha256$<salt>$<64-hex hash>`, not
    bcrypt. The iteration count is not stored in the string, so it must be
    confirmed before login can work (P4).
  - **`chat_messages.products_json`** stores the full product objects shown
    with each assistant reply. This is a hint for the P7 response shape and
    P8 memory.
  - All 102 image files match their `image_file_path`. One product ID has a
    typo baked in (`yale-sports-creqneck-field-hockey`); keep it as is,
    since the image file uses the same name.
