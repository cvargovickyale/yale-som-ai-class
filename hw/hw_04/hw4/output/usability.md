# Usability Improvements (P9)

Four improvements: two on the website (front end) and two in the agent and
backend. For each one: what was added, why, how it helps the shopper and
the business, how to see it in the running app, and how it was verified.

## At a glance

| # | Improvement | Helps the shopper | Helps the business | See it in the app |
|---|---|---|---|---|
| 1 | Product pages open as a popup | Keeps their place; browsing feels quick, not jarring | More products viewed per visit; fewer shoppers lost between pages | Click any product card |
| 2 | Category selection: tabs + "Find your fit" figure | One click to "T-Shirts", or tap the part of the outfit you want; no typing, no waiting | Browsing by type costs $0 in AI; the messy catalogue labels become clean categories; a memorable, playful way to shop | Products page (tabs on top, figure on the left); Home page "Find your fit" section |
| 3 | Chat rate limit | The chat stays available; a clear "try again in N seconds" | Caps AI spending; bots and abusers can't run up the bill | Send 6 chat messages within a minute as a guest |
| 4 | One database read per fact, per message | Faster answers; never yesterday's price | 32% fewer AI tokens on price questions; fewer database reads | The backend terminal line for each chat message; "Earlier chat" divider when logged in |

How to run the app: see `README.md` (backend on port 8000, website on port
5173). Test login: `test@campuscustoms.yale.edu` / `password`.

---

## 1. Product pages open as a popup (front end)

**What was added.** Clicking a product opens its page (image on the left;
name, price, description, colors, and stock by size on the right) as a
large popup **over** the page you were on. That page stays visible, grayed
out, around the edges. The product content itself is unchanged.

**Why.** Before, a product replaced the whole page. It felt like leaving
the store: the grid, the category or search you were in, and your scroll
position all disappeared, and coming back meant finding your place again.

**How it helps.**
- **Shopper:** open a product, look, close, and you're exactly where you
  were (same category tab or chat results, same scroll position).
  Comparing several products becomes open-close-open-close instead of
  navigate-back-scroll-find. Closing is forgiving: ×, Esc, or a click on
  the gray area. The chat stays on top, so you can ask "do you have this in
  blue?" while looking at the item.
- **Business:** less friction means more products viewed per visit, and
  more product views is the step before a purchase. Shoppers don't get lost
  between pages, and each product still has its own shareable link
  (`/products/<id>`).

**See it in the app.**
1. Go to **Products**, scroll down a bit, and click any card. The popup
   opens with the grid grayed out around it.
2. Press **Esc** (or ×, or click the gray area). You're back at the same
   spot.
3. Also try it from a category tab, from chat search results, and from the
   small product cards inside the chat.
4. Paste a product link directly (e.g. `http://localhost:5173/products/yale-mom-hoodie`).
   It opens as a popup over All products.

**How it's built.** The card link carries the page it was clicked on
(`backgroundLocation`). `App.tsx` keeps rendering that page and draws the
product (`pages/ProductDetail.tsx`) on top as a dialog: `role="dialog"`,
focus moved into it, and the page behind locked from scrolling.

**Verified.**

| Check | Result |
|---|---|
| Open a tee from the T-Shirts tab, scrolled 600 px | Popup over the tab; all 25 cards still rendered behind it; scroll locked; focus in the dialog |
| Esc / × / click the gray area | Each returns to `?category=t-shirts` at 600 px; a click *inside* the popup doesn't close it |
| Desktop 1280×800 | Popup 980 px wide and centered, with 150 px of grayed page on each side; chat button still usable on top |
| Pasted product URL | Popup over All products; closes to `/products` |
| Card in chat search results | Popup over the results; Esc returns to them |

## 2. Category selection: tabs + "Find your fit" figure (front end)

**What was added.** Two ways to pick a category, sharing one category
system:

- **Category tabs** across the top of the Products page, each with a count:
  **All 102 · Hoodies 27 · Crewnecks 29 · T-Shirts 25 · Quarter-Zips 11 ·
  Jackets 8 · Long Sleeves 2** (P9).
- **"Find your fit"** (added in P10 on top of the same categories): a simple
  figure where you tap the part of the outfit you're shopping for. Hood →
  Hoodies, zip collar → Quarter-Zips, chest → Crewnecks, short sleeves →
  T-Shirts, long sleeves → Long Sleeves, outer layer → Jackets.
  - Hovering a zone turns it Yale blue, and a caption names it ("Chest →
    Crewnecks · 29").
  - Tapping it filters the page.
  - It's pinned beside the product grid on wide screens and has its own
    section on the Home page. On narrow screens the tabs take over.

**Why.** Before, the only ways to narrow 102 products were scrolling or
asking the chat. "Just show me t-shirts" meant typing a message and waiting
about 4 seconds for the AI. The catalogue's own `garment_type` labels were
too messy to filter on directly: 22 different labels for about 6 kinds of
garment (P2). The tabs fixed the speed; the figure makes choosing visual,
for shoppers who think "something with a hood," not "the Hoodies
category."

**How it helps.**
- **Shopper:** one click (or tap) to the kind of item they want, with an
  instant result and a count shown first. The figure is quicker to read
  than a list of garment names, and fun to use. The selection is in the
  URL, so the Back button, reloads, and shared links keep it. Tabs swipe
  sideways on a phone instead of wrapping into several rows.
- **Business:** category browsing uses **no AI at all**. A chat search for
  "hoodies" costs about 7,000 tokens; a tab or figure tap costs nothing, so
  routine browsing is free and the chat is left for real questions. The
  figure is a distinctive touch that makes the shop memorable. The
  backend's clean category mapping is shared with the agent, which knows
  which tab is open ("which of these come in XXL?" on the Jackets tab
  works), and can feed reports and merchandising later.

**See it in the app.**
1. Products page → click **T-Shirts**: 25 cards, and the address bar shows
   `?category=t-shirts`.
2. On the left, hover the figure's **chest**. It turns blue, and the caption
   reads "Chest → Crewnecks · 29." Click it: 29 crewnecks, with the
   Crewnecks tab highlighted.
3. Home page → "Find your fit" section: tap the **hood** to jump to
   Hoodies.

Screenshots: `output/app_check.html`, check 3.

**How it's built.**
- `backend/main.py` maps each product's `garment_type` to one of six
  categories (`CATEGORY_RULES`) and adds a `category` field to every
  product. All 102 products are covered, and none fall into "Other."
- The tabs and the figure (`frontend/src/components/FitPicker.tsx`) both
  read that field and set the same `?category=` filter, so they always
  agree.
- The figure is one small SVG drawing whose zones are keyboard-accessible
  buttons: no images, no extra downloads.

**Verified.**

| Check | Result |
|---|---|
| Tab counts | 27 + 29 + 25 + 11 + 8 + 2 = 102 ✓ |
| T-Shirts tab | Exactly 25 cards, all t-shirts; URL `?category=t-shirts` |
| Hover the figure's chest | Zone filled Yale blue (`rgb(0, 53, 107)`); caption "Chest → Crewnecks · 29" |
| Click the chest | `?category=crewnecks`, 29 cards, Crewnecks tab and legend highlighted |
| Click the zip collar | `?category=quarter-zips`, 11 cards |
| Agent on the Jackets tab: "which of these come in XXL?" | 5, matching the database |

## 3. Chat rate limit (agent/backend)

**What was added.** Limits on how many chat messages anyone can send,
checked **before** the AI is called:

| Who | Limit | Counted by |
|---|---|---|
| Guest | 5 per minute, 30 per day | IP address |
| Logged-in customer | 10 per minute, 200 per day | account |
| The whole site | 60 per minute total | everyone combined |

Over a limit, the chat replies in the bulldog's voice: "🐾 Woof! You're
chatting faster than I can fetch. Try again in 42 seconds." The server
returns HTTP 429 with a `Retry-After` header. Browsing, product pages,
accounts, and the idle tail-wag (which uses no AI) are never limited.

**Why.** Every chat message costs roughly 6,000–9,000 AI tokens, and the
chat had no limit. Anyone, including an anonymous guest or a script, could
send unlimited messages. If the site grew, this would break first: the
bill, not the servers.

**How it helps.**
- **Business:** puts a ceiling on AI spending. A blocked message costs
  nothing because the AI is never called. The site-wide cap bounds total
  spend even if someone rotates IP addresses or creates many accounts.
  Logged-in customers get higher limits than guests, which rewards signing
  up.
- **Shopper:** one heavy user or bot can't make the chat slow or
  unavailable for everyone else. A real shopper never comes close to 5
  messages a minute. If they do hit it, they get a clear, friendly "try
  again in N seconds" instead of an error, and browsing keeps working.

**See it in the app.** As a guest (logged out), send 6 chat messages within
a minute. The 6th gets the "chatting faster than I can fetch" reply. Wait
until the time it gives, and chat works again. A logged-in account has its
own separate allowance.

**How it's built.** `RateLimiter` and `enforce_chat_rate_limit()` in
`backend/main.py`: sliding-window counts per guest IP, per account, and
site-wide, checked at the top of `POST /api/chat`.

**Verified.**

| Check | Result |
|---|---|
| Fake-clock test: 7 guest messages 1 s apart | 5 allowed, then "wait 55 s"; allowed again after 60 s |
| Fake-clock test: one guest every 13 s | Allowed 30, then blocked for the day |
| Another guest while one is blocked | Unaffected |
| Live, website on port 5173: guest messages 1–5, then a 6th typed in the chat | 1–5 answered; the 6th showed "🐾 Woof! You're chatting faster than I can fetch. Try again in 42 seconds." The page didn't change. |
| Live: logged-in customer right after a guest was blocked | Answered (separate limit) |

**Limits of this version.**
- Counts are kept in the server's memory, so they reset on restart and
  aren't shared between servers. A multi-server deployment would keep them
  in a shared store such as Redis.
- Behind a reverse proxy, every guest appears to come from the proxy's
  address. Production would read the proxy's `X-Forwarded-For` header
  instead. In local development all guests share one address.
- Found while testing: identical repeated messages sometimes came back in
  under half a second but **were still billed in full** (6,050 input tokens
  each; Portkey reported no cache hit, and the cause is unconfirmed). Fast
  isn't free, which is the case for limiting by count.

## 4. One database read per fact, per message (agent/backend)

**What was added.**
- **A per-message lookup record, enforced in code** (`MessageLookups`
  inside `AgentDeps`). Each chat message starts with an empty record. The
  first time a tool needs a product's price or stock, it reads the
  database. Any repeat in the **same message** is answered from the record.
  The next message starts empty, so nothing is ever reused across messages.
- **Tighter tool rules in `prompt.md` and the tool descriptions.** Search
  results already carry the live price, so a price question can be
  answered right away. Product info is only for description or colors;
  stock only for per-size questions; no tools for greetings.
- **Freshness guards.**
  - Only lookups made while answering the current message count as
    evidence.
  - Saved replies in a customer's history are labeled with their time and
    "may be out of date."
  - Reloaded chats start with a divider: "Earlier chat · Oct 6 · prices and
    stock may have changed since."
- **A one-line summary per chat message in the backend terminal**: model
  round trips, tokens, and database queries.

**Why.** Measuring the agent showed it looking up the same thing twice in
one answer. For "How much is the Yale Mom hoodie?" it searched (which
already returned the price), then fetched the product again to read the
same price. That's an extra model round trip that re-sends ~3,000 tokens of
instructions. Christopher's requirement: read the same price from the
database **only once per message**, and never trade away freshness. A
returning customer must never be quoted yesterday's price.

**How it helps.**
- **Shopper:** faster answers (the price question went from 6.4 s to
  3.4 s). Every number in one reply comes from the same moment, so a reply
  can't contradict itself. And a returning customer always gets today's
  price and stock, even if an old reply in their chat said something else;
  the "Earlier chat" divider tells them old numbers are old.
- **Business:** 32% fewer AI tokens on price questions and 63% fewer on a
  plain "hi," which saves money on every message. Fewer database reads per
  message means the site handles more shoppers. Quoting only current prices
  protects trust (and avoids honoring a stale price). The per-message log
  line makes cost visible, so the next improvement can be measured rather
  than guessed.

**See it in the app.**
1. Ask the chat "How much is the Yale Mom hoodie?" The backend terminal
   prints a line like
   `chat guest: 2 model round trips, 6804 input / 88 output tokens, 2 DB queries (0 reused from this message)`.
   The 2 queries are the one read of the catalogue and inventory for that
   message.
2. Log in as the test user (or any account with past chats) and open the
   chat. Older messages appear under "Earlier chat · <date> · prices and
   stock may have changed since."

**Before → after** (same messages, live `gpt-5.6-luna`):

| Message | Model round trips | Input tokens | Time | Database reads |
|---|---|---|---|---|
| "How much is the Yale Mom hoodie?" | 3 → **2** | 9,311 → **6,290 (−32%)** | 6.4 s → **3.4 s** | search + a 2nd read of the same row → **one read** |
| "hi" | 2 → **1** | 8,412 → **3,115 (−63%)** | — | a pointless search → **none** |
| "is this in stock in small?" (product page) | 2 → 2 | 6,298 → 6,484 | 3.8 s → 3.6 s | one |
| "show me hoodies" | 2 → 2 | 7,133 → 7,319 | 3.9 s → 4.1 s | one |
| Woody "show me t-shirts" (9 saved replies) | 2 → 2 | 8,949 → 9,981 | 4.9 s → 4.3 s | one |

The ~190-token rise on already-efficient messages comes from the new rules;
the ~1,000-token rise for Woody comes from the freshness labels on his 9 saved
replies. That's a deliberate trade: slightly more tokens for a guarantee of
current prices.

**Acceptance test: no stale prices.** On a test copy of the database, the
Yale Mom Hoodie was changed to **$74.00** with Medium **sold out**, while
Woody's real saved history still said "$68.00" and "8 available." Six
runs:

| Question (asked twice each) | Answer, both times |
|---|---|
| "How much was the Yale Mom hoodie again?" | "$74.00 right now" |
| "Is it still available in medium?" | "sold out in Medium right now" (one database read for search + stock) |
| "You told me $68 earlier, right? Just confirm that price." | "I checked just now: … $74.00, not $68.00." |

6 of 6 fresh; 0 stale.

**Known limit.** Skipping the search on small talk is up to the model, and
it doesn't always comply. "hi" now skips it, but "hello!" and "thanks"
sometimes still run one pointless search (one extra round trip, still a
single database read). Fixing it reliably would take a code-level shortcut
for obvious small talk, not more prompt wording.

---

## Appendix: how the agent/backend improvements were chosen

Four real messages were measured through the live agent before choosing
(PydanticAI usage counters):

| Message | Time | Model round trips | Input tokens | Output tokens | Tools called |
|---|---|---|---|---|---|
| Guest: "How much is the Yale Mom hoodie?" | 6.4 s | 3 | 9,311 | 121 | `find_products`, `get_product_info` |
| Guest on a product page: "is this in stock in small?" | 3.8 s | 2 | 6,298 | 156 | `check_stock` |
| Guest: "show me hoodies" | 3.9 s | 2 | 7,133 | 352 | `find_products` |
| Woody (18 saved messages): "show me t-shirts" | 4.9 s | 2 | 8,949 | 383 | `find_products` |

- **Input dwarfs output, roughly 50–75 to 1.** The instructions (about
  2,300 tokens of `prompt.md`, plus tool descriptions and context) are
  re-sent on **every** round trip, so cutting round trips is the biggest
  lever (→ improvement 4).
- **Nothing limited how many messages anyone could send.** At scale, the
  bill breaks first (→ improvement 3).

Other candidates, not built:
1. **A token budget for instructions and history.** History capped by
   size rather than message count; the provider's prompt caching for the
   unchanging first part of the instructions.
2. **Don't block the server on database calls.** Under many simultaneous
   shoppers, one slow query in the async chat handler stalls everyone.
3. **Indexed search.** Search loads the whole catalogue once per message.
   That's fine at 102 products, slow at 100,000 (SQLite FTS5).
4. **Lighter pages.** The full product list is downloaded on every visit to
   Home or Products, and images are served full size.
