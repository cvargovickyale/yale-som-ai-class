# Design (P10)

Goal: make the site feel like a real Yale merch shop, professional and
polished, with a few touches that are fun to use and cheap to run.

## What people will like

- **It looks like a real Yale shop.** Classic serif headings (Libre
  Baskerville) over a clean modern body font (Inter), Yale blue `#00356B`
  on warm white, a slim announcement bar ("Officially licensed Yale apparel
  · Family-run in New Haven since 1975"), and a proper footer with the
  store's address.
- **Real products, front and center.** The home page opens with a floating
  collage of actual catalogue photos, followed by "Shop by category" photo
  tiles. Black borders are trimmed off the 73 of 102 product photos that
  had them, so the grid looks like one consistent photo shoot instead of a
  mix.
- **"Find your fit."** Tap the hood, zip collar, chest, sleeves, or outer
  layer on a simple figure to shop that kind of item (Hoodies, Quarter-Zips,
  Crewnecks, T-Shirts, Long Sleeves, Jackets). It's on the home page and
  pinned beside the Products grid. It's quicker and more playful than a
  dropdown, and built from a single small SVG: no illustrations, no extra
  downloads.
- **Motion that feels alive.**
  - cards lift and their photos zoom slightly on hover
  - product grids fade in with a short ripple
  - the menu underline slides
  - the product popup scales in, and the × spins on hover
  - chat bubbles pop in, with "typing" dots while Handsome Dan fetches
  - placeholders shimmer while products load
  - the hero photos drift gently
- **Honest, useful signals.** "Only 9 left" badges come from live stock in
  the database (8 products have 25 or fewer units). Products with no
  written description say "Description coming soon" instead of showing
  placeholder text.
- **Handsome Dan.** The chat assistant is now named for Yale's bulldog,
  with the same honest, database-backed answers.
- **Works on a phone.** At 375 px wide there's no sideways scrolling,
  category tiles go two per row, tabs swipe, and the popup fits the screen.

## Built to be cheap to run

- **Motion uses only `transform` and `opacity`.** The browser hands those
  to the graphics chip, so animations stay smooth on low-end phones and
  never force the page layout to be recalculated. There's no animation
  library; it's all CSS.
- **Reduced motion is respected.** Visitors whose device asks for less
  motion get none.
- **Small pages.** The whole stylesheet is 5 KB compressed and the
  JavaScript 90 KB. Fonts are self-hosted (no requests to Google), and
  browsers download only the character sets they need.
- **Photo cleanup happens in the browser.** Each photo's borders are
  measured once from a 64 px copy and clipped off with CSS, which costs
  almost nothing to draw.

## Deliberately left out

- **Lifestyle photos of people in Yale merch,** like the real
  yalebulldogblue.com. There are no licensed photos to use, and AI-generated
  people wouldn't wear these exact products. A real launch would add a
  licensed photo shoot. For now, the products themselves are the imagery.
- **A full "dress the model" visualizer.** It would need real illustration
  work to look professional. The tap-the-figure picker delivers the same
  idea for a fraction of the effort.
