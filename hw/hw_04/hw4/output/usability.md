# Usability Improvements (P9)

Two front-end improvements (built and verified), plus a measured baseline
of agent/backend cost and speed to choose the two agent/backend
improvements from.

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

## Agent/backend improvements: *to choose*

Candidates, ranked by what would hurt first if the site grew:

1. **Fewer model round trips.** Biggest win for both time and tokens. Let
   simple price/stock answers finish in 2 round trips instead of 3 (use the
   price `find_products` already returns, or one combined
   "details + stock" tool).
2. **Rate-limit the chat.** The first thing that breaks at scale is the
   bill. `/api/chat` has no limit, and anyone, including guests, can send
   unlimited messages at about 6,000–9,000 tokens each.
3. **A token budget for instructions and history.** A shorter prompt;
   history capped by size rather than message count; and the provider's
   prompt caching for the unchanging first part of the instructions.
4. **Don't block the server on database calls.** The chat handler runs
   SQLite queries directly inside an async function, so under many
   simultaneous shoppers one slow query stalls everyone. Longer term,
   SQLite allows one writer at a time for chat history.
5. **Indexed search.** `find_products` scans every product in Python on
   each call. That's fine at 102 products, slow at 100,000 (SQLite FTS5).
6. **Lighter pages.** The website downloads the full product list on every
   visit to Home or Products, and serves full-size images.
