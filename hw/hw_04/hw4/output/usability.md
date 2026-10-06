# Usability Improvements (P9)

Two front-end improvements and two agent/backend improvements, each
built and verified, plus the measured baseline of agent cost and speed
that the backend choices were based on.

## Front-end improvement 1: product pages open as a popup

**Problem.** Clicking a product replaced the whole page with a separate
single-item page. It felt like leaving the store: the grid, the category or
search you were in, and your scroll position all disappeared, and coming back
meant re-finding your place.

**Change.** The single-item view now opens as a large popup over the page you
clicked from. The page stays visible, grayed out, around the edges. The
content (image left; name, price, description, colors, and sizes with stock
on the right) is unchanged.

- **Close it** with the × button, the Esc key, or a click on the grayed-out
  area. Clicking inside the popup doesn't close it.
- Closing returns you to **exactly** where you were: same category tab or
  chat search results, same scroll position. The page behind was never
  unmounted.
- The page behind can't scroll while the popup is open, and keyboard focus
  moves into the popup (`role="dialog"`, `aria-modal`).
- The product still has its own URL (`/products/<id>`), so links can be
  shared. A pasted or reloaded product URL opens the popup over the full
  Products page, and closing it lands there.
- It works from every place a product appears: All products, a category tab,
  chat search results, the Home page's "Well stocked" cards, and the small
  cards in the chat panel.
- The chat panel stays on top of the popup, so you can ask "do you have this
  in blue?" while looking at the product.

**How it works.** When a card is clicked, the link carries the page it was
clicked on (`backgroundLocation`). `App.tsx` keeps rendering that page and
draws the product popup on top of it (`pages/ProductDetail.tsx`).

## Front-end improvement 2: category tabs

**Problem.** The only ways to narrow 102 products were scrolling or asking
the chat. Browsing by type ("just show me t-shirts") took typing a message
and waiting about 4 seconds for the AI.

**Change.** A row of category tabs across the top of the Products page, each
with a count: **All 102 · Hoodies 27 · Crewnecks 29 · T-Shirts 25 ·
Quarter-Zips 11 · Jackets 8 · Long Sleeves 2**. One click filters instantly,
with no AI call.

- The catalogue's 22 inconsistent `garment_type` labels (P2) are mapped to
  these 6 categories in the backend (`main.py`, `CATEGORY_RULES`). Every
  product gets a `category` field, so the website and the agent use the same
  groups. All 102 products land in a category, and none fall into "Other."
- The selected tab is in the URL (`/products?category=t-shirts`), so the
  Back button, reloads, and shared links keep it.
- When chat search results are showing, a "💬 Chat results" tab is
  highlighted. Clicking any category tab switches to that category.
- Tabs scroll sideways on narrow screens instead of wrapping into many rows
  (a Lecture 08 lesson).
- The agent knows which tab is open: on the Jackets tab, "which of these
  come in XXL?" returned the 5 jackets with XXL in stock, matching the
  database exactly.

## Verified

| Check | Result |
|---|---|
| Tabs and counts | All 102, Hoodies 27, Crewnecks 29, T-Shirts 25, Quarter-Zips 11, Jackets 8, Long Sleeves 2 (sum 102) |
| T-Shirts tab | 25 cards, all t-shirts; URL `?category=t-shirts` |
| Open a tee from the T-Shirts tab, scrolled 600 px | Popup over the tab; 25 cards still rendered behind; page scroll locked; focus in the dialog |
| Esc / × / click the gray area | All close to `?category=t-shirts`, scroll still at 600 px; a click inside the popup does not close it |
| Desktop 1280×800 | Popup 980 px wide, centered, with 150 px of grayed page visible on each side; chat button still clickable on top |
| Pasted URL `/products/champion-reverse-weave-crewneck` | Popup over All products (102 behind); closes to `/products` |
| Card in chat results ("Saybrook gear") | Popup over the 3 results; Esc returns to them |
| Agent on the Jackets tab: "which of these come in XXL?" | 5, matching the database |

## Agent/backend: measured baseline (before choosing improvements)

Four real chat messages through the live agent (`gpt-5.6-luna` via
Portkey), measured from PydanticAI's usage counters:

| Message | Time | Model round trips | Input tokens | Output tokens | Tools called |
|---|---|---|---|---|---|
| Guest: "How much is the Yale Mom hoodie?" | 6.4 s | 3 | 9,311 | 121 | `find_products`, `get_product_info` |
| Guest on a product page: "is this in stock in small?" | 3.8 s | 2 | 6,298 | 156 | `check_stock` |
| Guest: "show me hoodies" | 3.9 s | 2 | 7,133 | 352 | `find_products` |
| Woody (18 saved messages): "show me t-shirts" | 4.9 s | 2 | 8,949 | 383 | `find_products` |

What the numbers show:

- **Input dwarfs output, roughly 50–75 to 1.** The instructions alone
  (`prompt.md` is about 2,300 tokens, plus tool descriptions and the
  dynamic context) are re-sent on **every round trip**, so a 3-round-trip
  answer pays for them 3 times.
- **The simplest question was the most expensive.** "How much is X?" took 3
  round trips and 6.4 s, because the agent called `get_product_info` even
  though `find_products` had already returned the price.
- **Saved history is added to every request.** Woody's 18 messages added
  about 1,800 input tokens to each round trip.

## Agent/backend improvement 1: rate-limit the chat ✅

**Problem.** Every accepted chat message costs roughly 6,000–9,000 AI input
tokens, and `/api/chat` had no limit. Anyone, including an anonymous guest
or a script, could send unlimited messages and run up the bill. At scale,
this breaks first: the cost, not the servers.

**Change.** `main.py` checks limits **before** the agent runs, so a blocked
message costs nothing:

| Who | Limit | Keyed by |
|---|---|---|
| Guest | 5 messages per minute, 30 per day | IP address |
| Logged-in customer | 10 per minute, 200 per day | account |
| The whole site | 60 messages per minute total | everyone combined, which caps total spend even if someone rotates IPs or accounts |

Over a limit, the API returns **429 Too Many Requests** with a `Retry-After`
header and a message in the bulldog's voice ("Woof! You're chatting faster
than I can fetch. Try again in 53 seconds."). The chat panel shows it as-is
instead of "couldn't reach the store." Browsing, product pages, accounts,
and the idle tail-wag (no AI) are never limited.

**Verified.**

| Test | Result |
|---|---|
| Fake-clock test: 7 guest messages 1 s apart | 5 allowed, then 429 "wait 55 s"; allowed again after 60 s |
| Fake-clock test: a guest pacing 1 message every 13 s | Allowed 30, then blocked by the daily window |
| Another guest while one is blocked | Unaffected |
| Live: 6 quick guest messages | 1–5 → 200; 6th → 429 in 0.002 s (no AI call), `Retry-After: 53` |
| Live: logged-in Woody right after | 200 (separate limit) |
| Live: product list and the idle endpoint | 200 |

**Limits of this version.**
- Counts live in server memory, so they reset on restart and aren't shared
  between server processes. A multi-server deployment would keep them in a
  shared store like Redis.
- Behind a reverse proxy, every guest would appear to come from the proxy's
  address, so production would read the proxy's `X-Forwarded-For` header.
  (In local dev, Vite's proxy also makes all guests share one address.)
- Found while testing: identical repeated messages sometimes came back in
  under half a second, but **were still billed in full** (6,050 input tokens
  each). Portkey reported no cache hit, and the cause wasn't confirmed.
  Being fast doesn't mean being free, which is the case for limiting by
  count.

## Agent/backend improvement 2: one database read per fact, per message ✅

**Problem.** The agent made the same database lookup twice in one answer.
For "How much is the Yale Mom hoodie?" it searched (which already returned
the live price), then fetched the product again just to read the same
price: an extra model round trip that re-sent all ~3,000 tokens of
instructions. Even "hi" triggered a catalogue search. Requirement set by
Christopher: the same price may be read from the database **only once per
message**, and freshness must never be traded away. A returning customer
must never get yesterday's price.

**Change, in two layers:**

1. **Enforced in code: a per-message lookup record** (`MessageLookups`,
   inside `AgentDeps`). `main.py` creates a new, empty one for every chat
   message. Every tool reads through it. A product's catalogue row (price
   included) and its stock are read from the database at most once per
   message; any repeat request in that message is answered from the record.
   The next message starts empty, so nothing is reused across messages.
   Bonus: every number in one reply comes from one consistent snapshot.
2. **Guided by the prompt and tool descriptions:**
   - search results already carry the live price, so price questions can
     answer right away
   - `get_product_info` is only for description or colors, and
     `check_stock` only for per-size availability
   - no tool for greetings or small talk
   - "Using your tools" was rewritten tighter, so the prompt stayed about
     the same length (9,153 vs. 9,038 characters)

**Freshness guards (so "fewer lookups" never means "older data"):**
- The prompt says only lookups made *while answering the current message*
  count. Earlier messages, including the agent's own past replies, are
  never evidence for a price or stock count.
- Each saved reply in the agent's history is labeled with its time and
  "any price or stock in it may be out of date; look it up again."
- In the chat panel, reloaded history starts with a divider: "Earlier chat
  · Oct 6 · prices and stock may have changed since." Product cards under
  old replies were already re-read from the database.

**Before → after** (same messages, live `gpt-5.6-luna`):

| Message | Round trips | Input tokens | Time | Database reads |
|---|---|---|---|---|
| "How much is the Yale Mom hoodie?" | 3 → **2** | 9,311 → **6,290 (−32%)** | 6.4 s → **3.4 s** | search + a second read of the same row → **one read** |
| "hi" | 2 → **1** | 8,412 → **3,115 (−63%)** | — | a pointless search → **none** |
| "is this in stock in small?" (product page) | 2 → 2 | 6,298 → 6,484 | 3.8 s → 3.6 s | one |
| "show me hoodies" | 2 → 2 | 7,133 → 7,319 | 3.9 s → 4.1 s | one |
| Woody "show me t-shirts" (9 saved replies) | 2 → 2 | 8,949 → 9,981 | 4.9 s → 4.3 s | one |

The ~190-token rise on already-efficient messages is the new rules. The
~1,000-token rise for Woody is the time-stamp labels on his 9 saved replies:
a deliberate cost of the freshness guard.

**Acceptance test: no stale prices.** On a test copy of the database the
Yale Mom Hoodie was changed to **$74.00** with Medium **sold out**, while
Woody's real saved history still said "$68.00" and "8 available." Six runs:

| Question (asked twice each) | Answer, both times |
|---|---|
| "How much was the Yale Mom hoodie again?" | "$74.00 right now" |
| "Is it still available in medium?" | "sold out in Medium right now" (one database read for search + stock) |
| "You told me $68 earlier, right? Just confirm that price." | "I checked just now: … $74.00, not $68.00." |

6 of 6 fresh; 0 stale.

**Known limit.** Skipping the search on small talk is up to the model, and
it doesn't always comply. "hi" now skips it, but "hello!", "thanks," and
"where is your store?" still sometimes run one pointless search (2 round
trips, about 8,000 tokens, still one database read). Fixing that reliably
would take a code-level shortcut for obvious small talk rather than more
prompt wording.

## Agent/backend: other candidates (not built)

1. **A token budget for instructions and history.** History capped by size
   rather than message count; the provider's prompt caching for the
   unchanging first part of the instructions.
2. **Don't block the server on database calls.** The chat handler runs
   SQLite queries directly inside an async function, so under many
   simultaneous shoppers one slow query stalls everyone.
3. **Indexed search.** Search loads the whole catalogue once per message.
   That's fine at 102 products, slow at 100,000 (SQLite FTS5).
4. **Lighter pages.** The website downloads the full product list on every
   visit to Home or Products, and serves full-size images.
