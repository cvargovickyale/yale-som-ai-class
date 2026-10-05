# Homework 4 AI Prompts

Records the prompt used for each problem, plus at most one follow-up when a
correction or clarification was needed. Each prompt is typed in my own words,
one problem at a time. Coding assistant: Claude Code.

## Problem 2 — Analyze the database

**Prompt:** Help me open the database so I can understand the fields like
catalogue inventory and users

**Follow-up prompt used:** no, you run that in terminal. then, start a
harness.md file in the ouput. the first section of this harness file will
have each table and its fields - I'll type why each field matters for either
the shop or the chatbot, you can help fill in based on my lead. we'll do
models tools and safety and specs in the harness in later problems

**Notes:**

- Setup: created the `hw4/` folder and placed the data pack at `hw4/data/`.
  It is excluded from git (assignment rule: never commit the DB or images).
- No LLM was used. The analysis is direct SQL against `campus_customs.db`
  with the `sqlite3` command-line tool, opened in my terminal with sample
  rows from each table.
- Started `output/harness.md`. Section 1 (Data) lists every table and field.
  The "why it matters" column is written from my own notes. Models, tools,
  safety, and specs sections come in later problems.
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

## Problem 3 — Build the Campus Customs website

**Prompt:** P3 we need to build a front end. built with react vite and
typescript. the top should have a navigation bar at the top that shows main
pages. I think a later problem will have us style this like another merch
website so ignore all gateway 2000 styling early 2000s stuff I have for now.
ah here it is - Pull Campus Customs-style wording ffrom yalebulldogblue.com
for the Home and About Us panels. mix their style with mine, don't just copy
their text. the main pages are home;products;about us;log in; create account

priducts page shows product images from the catalogue using image paths in
the database with basic info like name price and short descrip.

each product when clicked will open a single item page like amazon - large
image on left side, full text on right side - description, price, sizes and
number in stock when available.

also a chat interface in bottom right. no agent yet. make a stub that calls
backend for now. stub agent should be a simple FastAPI app in main.py in
backend that serves products and images. will grow later

**Notes:**

- **Frontend:** Vite + React + TypeScript with `react-router-dom`. Nav bar
  pages: Home, Products, About Us, Log In, Create Account, plus a
  single-item page at `/products/:id`. A floating chat widget sits in the
  bottom-right corner. Styling is deliberately plain; real design comes in
  P10.
- **Backend:** `backend/main.py` (FastAPI) serves `/api/products`,
  `/api/products/{id}` (stock per size, ordered XS→XXL), product images at
  `/images/`, and a stub `/api/chat`. API shapes live in `backend/models.py`
  and are mirrored in `frontend/src/types.ts`. Chat already returns
  `{reply, products}`, so P7 can fill `products` without changing the
  frontend contract.
- **Safety choices:** only `data/products/` is served publicly. Mounting
  all of `data/` would have exposed the `.db` file; I tested that `../`
  path tricks return 404. The database is opened read-only in P3.
- **Wording:** Home and About Us copy is paraphrased from
  yalebulldogblue.com and campuscustoms.com (founded 1975 across from
  campus, 57 Broadway, family-run, in-house printing and embroidery,
  officially licensed), rewritten in a shorter, plainer voice rather than
  copied.
- **Verified in the browser:**
  - all 102 product cards render, with 0 broken images
  - the single-item page shows the image on the left and text on the right
  - per-size stock matches the database (Yale Mom Hoodie XS 25 / S 8 / M 8
    / L 25 / XL 8 / XXL 2; sold-out sizes shown crossed out)
  - the chat round trip reaches the backend stub
  - the Log In and Create Account forms show a "coming soon" notice until P4
- **Setup:** `hw4/.venv` (Python 3.14), `requirements.txt`, `.env.example`
  (placeholders only), `.gitignore` (excludes `.env`, `data/`, `*.db`,
  `.venv`, `node_modules`), and a README explaining how to run the backend
  and frontend after placing the data pack.
