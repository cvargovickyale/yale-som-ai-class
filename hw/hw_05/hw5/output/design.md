# Campus Customs Desk — dashboard design

The React board in `frontend/` (React + Vite + TypeScript) where a person
watches the agent team work tickets and approves anything that moves money.
Start it with `npm run dev` in `frontend/`; it opens at
http://localhost:5173 and talks to the P7 backend through Vite's `/api`
proxy.

## Christopher's guidance (P8)

- Let you **pick which ticket to start with**.
- Show the **agents and their feeds**, each **ticket's status**, and a
  **summary of what the agents did on each ticket**.
- **Approval for payments.**
- A **prominent checking balance that stays updated**.
- **Spread out and a little more minimalist** than the dense views built
  before. It should look **calm and inviting, not overwhelming**.
- **Popups** people can click for more info.
- Focus on creativity and enjoyment: for example, **tickets having a
  satisfying closed animation that turns them green and pushes them into a
  done pile**.

## Final decisions

### Overall feel

| Decision | Choice | Why |
|---|---|---|
| Style | Calm, spacious, paper-and-card. Not the workspace's Gateway 2000 look | Christopher asked for calmer and less dense than earlier views. Gateway 2000's bevels and gray panels read as busy at this size. (`desk_tickets.html` keeps Gateway 2000; it's a document, not a workspace.) |
| Background | Warm paper `#f6f3ee`; white cards with 18 px corners and a soft two-layer shadow | Feels like a desk with papers on it, and keeps cards visually separate without borders everywhere |
| Color | One accent: **Yale blue** `#00356b` for actions and "needs you." **Green** only for done and paid. **Amber** only for money warnings and risks | With few colors, each one means something: blue = act, green = finished, amber = look carefully |
| Agents | Each agent has its own quiet color: Boss navy, Inventory sage, Accounting ochre, Facilities lavender, Customer Service rose | Easy to follow who's doing what across the panel, feeds, and popups |
| Type | **Fraunces** (serif) for the title, panel names, and big numbers; **Inter** for everything else | The serif makes the balance and headings feel warm and readable; Inter keeps the UI plain |
| Spacing | 40–48 px page padding, 28 px between panels, 18 px between tickets | "Spread out": nothing touches, and every panel has room to breathe |
| Words | Plain sentences instead of tool names ("Accounting proposed a payment", not `propose_payment`) | Calm for a non-technical reader; tool names still appear in popups and the audit trail |

### Layout (desktop, then smaller screens)

1. **Header:** title and shop date (from `desk.date_today`, not the
   computer's clock), an **"Approving as"** name field (remembered in the
   browser and recorded on every approval), **How it works** (popup), and
   **Reset** (popup confirmation).
2. **Hero row:** the **checking balance** card (the biggest thing on the
   page) and **Today on the desk** (open / waiting on you / done counts).
3. **Three columns:**
   - **On the desk:** open tickets.
   - **The team:** the five agents with live feeds.
   - **Done:** the done pile.
4. **Recent activity:** the last 8 events, as plain sentences.

Below 1180 px the Done pile moves under the other two columns, and below
760 px everything is a single column. Checked with no sideways overflow at
320, 375, 600, 760, 900, 1180, 1280, and 1440 px.

### How the checking balance shows up

- **Big and first.** A 64 px serif number, top left, labelled "Checking
  balance," straight from `cash_accounts` via `GET /api/cash`.
- **Stays current.** The board polls the event feed (every 1.2 s while the
  team works, every 3 s otherwise) and refetches the balance whenever a
  payment, decision, run, or reset event arrives.
- **Counts, doesn't jump.** When a payment is approved, the number counts
  down over about a second (eased), and a chip floats up beside it
  (**−$840.00** in amber, or **+** in green after a reset), then fades.
- **What's coming:** under the balance, "Waiting for your approval" (sum of
  pending payment requests) and "After those are paid." The second turns
  amber when it falls under $500, so a thin cushion, like the $160 left
  after the invoice and rent, is visible before you approve.
- A one-line note says where the number comes from and that money moves
  only when you approve.

### How tickets move: open → working → needs you → done

| State | What you see |
|---|---|
| **Open** | Type icon (shirt, key, tag), requester, the request, the ticket's own note in quotes, and **Start the team**. You pick any ticket, in any order. |
| **Team at work** | A blue "Team at work" pill, a slow breathing outline, and one live line ("**Accounting** proposed a payment…") that updates as events arrive. Other tickets show "Another ticket is being worked. One at a time." The backend enforces this. |
| **Needs you** | A blue **"2 need you"** pill (pending payments plus the decision) and **The Boss suggests** box: the outcome, the Boss's summary, and avatars of every agent that worked on it. Buttons: **Review and approve** and **Details**. |
| **Stopped** | "The run stopped (error). You can try again." in red, with **Try again**. Nothing is half-approved; any pending records the agents created stay visible in Details. |
| **Done** | Moves to the Done pile (below). |

### The closing animation (the satisfying part)

Approving a decision in the review popup (**Approve and close ticket**,
green, enabled only after every payment on the ticket is approved or
rejected):

1. The popup closes and the card **washes green** (0.6 s background fade).
2. A green **check stamp** pops in on the right with a little overshoot,
   and the check mark **draws itself**.
3. After about 1.1 s the card **lifts slightly, tilts, shrinks, and flies
   right**, toward the Done pile (0.65 s). On a phone it drops downward
   instead.
4. It **lands in the Done pile** with a short bounce and settles at its own
   slight tilt (stable per ticket, so the pile looks like real paper). A
   toast says "Ticket 101 is done." The Done counter and "Today on the
   desk" update.

Done cards are pale green with a solid green check, the ticket number,
type, and requester. Hovering straightens a card. Clicking opens the same
review popup in read-only form: who closed it, what was paid and by whom,
the draft, and what each agent did. With an empty pile there's a dashed
tray and "Closed tickets land here." With no open tickets left, the desk
says "All clear."

If the visitor has **reduced motion** turned on, every animation is
reduced to an instant change: the card just turns green and moves to the
pile.

### Agents and their feeds

- **The team** panel lists all five agents with an avatar, name, and status
  (**idle**, or **on #102** with a pulsing ring and a soft blue row while
  it's working).
- Under each: its role when it hasn't done anything yet, otherwise its
  **last three steps**, newest first, with times ("checked the shelf",
  "asked Customer Service for help", "finished").
- **Click an agent** for a popup with its full recent feed: every step on
  every ticket, the exact task it was handed in a delegation, its
  recommendation when it finished, and any tool refusal.

### Popups (click for more)

| Popup | Opens from | Contents |
|---|---|---|
| **Review** | Review and approve / Details / a Done card | The Boss's call and outcome; **Why** (expandable reasoning); **Worth knowing before you approve** (risks, in amber); **Payments**, each with amount, payee, reason, "Checking after this: $…", and **Approve payment** / **Reject**; the **draft** shown as a letter, labelled "Draft only. Nothing is ever sent."; stock holds and reprints; **What each agent did** (who asked whom, time, tokens, the recommendation, the tools it used, refusals in amber); and team totals ("all on gpt-6-luna"). |
| **Agent** | An agent row | That agent's full feed |
| **Start fresh?** | Reset | What a reset does; the audit trail is kept |
| **How it works** | Header | Four steps: pick, watch, review, approve |

Popups close with Esc, the ×, or a click outside, and focus returns to
where you were.

### Approvals and safety in the UI

- Every approve or reject needs a name in **Approving as**. Without one,
  the buttons stay disabled with a hint. The name is sent to the backend
  and stored in `payments.approved_by` and the audit trail.
- **Approve and close ticket** stays disabled until the ticket's payments
  are handled ("Approve or reject the payments above first"). The backend
  refuses it too.
- Refusals from the backend (cash would go below $0, already paid, a run
  already in progress) appear as a calm brown toast with the backend's own
  message.
- **Reset** is disabled while a run is going.
- There is **no send button** for drafts, anywhere. That's by design.

### Accessibility

- Live regions announce the balance and the working ticket's progress.
- Popups are labelled dialogs that take and return focus.
- Every button has a text label, and agent rows describe their state for
  screen readers.
- Focus outlines are visible.
- Color is never the only signal: pills and stamps carry text or icons.

## How it was checked (P8)

- `npm run build`: type-checks and builds with no errors.
- **Live, in the browser, on the working copy:**
  1. Started ticket 101 from the board. The first three tries hit
     temporary Azure errors (fixed with retries in the backend; see harness
     section 6), and the board showed "The run stopped … try again" each
     time.
  2. The next try: ok in 81 s. The card showed "2 need you" and the Boss's
     "waiting" suggestion, and the feeds updated during the run.
  3. In Review, approved the $840: the balance counted from $3,400 to
     **$2,560**, with a −$840.00 chip, and the payment showed "Paid ·
     Christopher."
  4. Approved and closed the ticket: green wash → stamp → flight → landed
     in Done (class sequence checked frame by frame).
  5. Done counter 1; Reset → $3,400, three open, empty pile.
- **Width sweep, 320–1440 px:** no sideways overflow, the popup fits, Esc
  closes it, and a real mouse click opens it. A phone-width overflow (a
  long feed line stretching the column) was found and fixed.
