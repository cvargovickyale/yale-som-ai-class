# Yale SOM Virtual: Evans Hall, Floor 2

A first-person walk-through of the 2nd floor of Edward P. Evans Hall (Yale School of Management), built with React, Vite, three.js, and @react-three/fiber.

It includes the blue classroom drums you can walk into, the curvy glass cloister around the courtyard, Ross Library on the west side, the Beinecke Terrace Room and its outdoor terrace on the east side, the small glass meeting rooms, and paintings above the stairwells.

**Walk it in your browser:** https://zlisto.github.io/yale_som_virtual/

## Run it locally

```bash
npm install
npm run dev
```

Open http://localhost:5173 and click **Click to walk in**.

**Keyboard + mouse** (works like a PC shooter):

| Key | Action |
| --- | --- |
| W A S D / arrows | walk |
| Mouse | look |
| Shift | sprint |
| Space | jump |
| C | crouch |
| M | toggle map |
| Esc | pause |

**Phone / tablet:** tap **Tap to walk in**. The left-thumb joystick walks (push it all the way to sprint), dragging anywhere else looks around, and there are on-screen jump and pause buttons. On a laptop, click **Use on-screen joystick** to try the phone controls. WASD still works in that mode.

## How it's built

- `src/layout.js`: the floor plan in meters (+x east, -z north). It holds the drums, library, Beinecke, stairs, meeting rooms, wall colliders, and room lookup. Each classroom faces the courtyard, with the whiteboard and podium on the inner side and stadium-seating rows (32 cm risers) stepping up toward the outer wall; its two doors are at the front corners. You climb the center-aisle steps one riser at a time.
- `src/World.jsx`: all the meshes. Walls use instanced boxes and the drums use partial cylinders.
- `src/textures.js`: procedural canvas textures (carpet, navy drum glass, wood slats, mural, signs, stairwell paintings).
- `src/Player.jsx`: walking (pointer lock or touch), jump/crouch, circle-vs-wall collision.
- `src/TouchControls.jsx`: on-screen joystick, drag-to-look, jump and pause buttons.
- `src/Minimap.jsx`: the black-and-pink map in the corner.
- `src/Labubu.jsx`: a customizable Labubu built from primitives: `fur`, `expression` (grin / happy / surprised / sleepy / mischief), `shirt` ('yale', 'stripes', or any color), `pants`, `overalls`, `hat`, `sitting`, `anim`.
- `src/LabubuParty.jsx`: the crew playing in the courtyard plus Labubus in meetings in every glass room.
- `src/slides.js`: lecture slides for eight Fall 2026 MBA courses (MGT 409, 404, 403, 887, 402, 538, 800, 541) on the classroom screens and meeting-room monitors.
- `src/LabubuCrowd.jsx`: 30 seated Labubu students per classroom, drawn with shared instanced meshes.
- `src/Professor.jsx` + `src/Faculty.jsx`: cartoon Hogwarts professors teaching most classes (Dumbledore, McGonagall, Trelawney, Slughorn, Lockhart, Moody, Flitwick), an AI avatar of Prof. Tauhid Zaman in 2200, and Hagrid in the courtyard.
- `src/HandsomeDan.jsx`: Handsome Dan touring a loop of 1000 randomly chosen classrooms (blue dot on the map).
- `src/talk.js` + `src/ChatPanel.jsx`: click-to-talk. Aim the crosshair at an AI avatar (it turns into a pink ring), click, and chat in the black-and-pink panel on the right.

## Talk to people (backend)

Classroom 2200 now has an **AI avatar of Prof. Tauhid Zaman** teaching MGT 409. Each avatar is clearly an AI (the chat header says "AI avatar", and so does the avatar if you ask). It never pretends to be the real person. Every avatar is a [PydanticAI](https://ai.pydantic.dev) agent served by a small FastAPI backend in `backend/`.

**Run it** (from this folder, in a second terminal next to `npm run dev`):

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
backend/.venv/bin/python -m uvicorn main:app --app-dir backend --port 8000
```

On Windows use `py -3.13 -m venv backend/.venv` and `backend/.venv/Scripts/python`.

**Keys:** put `PORTKEY_API_KEY=...` in `backend/.env` (see `backend/.env.example`). The backend also loads a `.env` from this folder or up to three folders above it. Calls go through Portkey (`https://api.portkey.ai/v1`) to `gpt-6-luna` with the OpenAI Responses API. Set `OPENAI_MODEL` to override the model. Never commit a real key.

Vite proxies `/api` to `http://127.0.0.1:8000`. To point the chat at another backend, set `VITE_API_URL`. The GitHub Pages site has no backend: the game still works, and the chat says it can't reach the backend.

**Routes**

| Method | Path | What |
| --- | --- | --- |
| GET | `/api/health` | `{ok, model, people}` |
| GET | `/api/people` | `[{id, name, title, room, course}]` |
| POST | `/api/people/{id}/chat` | `{message, session_id}` → `{reply, session_id}` (404 unknown person, 502 model error) |

Conversation memory lives on the server, keyed by person and `session_id` (at most 200 sessions and about 40 messages each).

**Files**

- `backend/main.py`: the FastAPI app, CORS, and session memory.
- `backend/people.py`: the `Person` list and `agent_for(id)`. Its instructions are the persona prompt plus the course facts from the catalog. Every agent has two tools: `search_courses(keyword)` and `course_info(course_number)`.
- `backend/courses.py`: read-only queries on `data/yale_som.db`. It skips PhD courses and never returns faculty emails.
- `backend/prompts/zaman.md`: the persona.

**Add an avatar**

1. Write `backend/prompts/<id>.md`, starting with "You are an AI avatar of Professor ...".
2. Add a `Person` to `PEOPLE` in `backend/people.py`.
3. Add an entry to `PEOPLE_INFO` in `src/talk.js`.
4. Add a preset to `PROFESSORS` in `src/Professor.jsx` (`casual: true` for the hoodie look), and put it in a classroom in `ROOM_PROFESSOR` (`src/Faculty.jsx`). For matching slides, add a course and deck in `src/slides.js` and point the room's `course` at it in `src/layout.js`.

Dev helper: `document.body.dataset.talk = "zaman"` opens the chat without pointer lock.

The layout is estimated from the wayfinding plan posted on the floor, so room sizes are approximate. The Stair G painting comes from a photo; the other stairwell paintings are made up.

Made for MGT 409: AI Foundations for Managers, Lecture 13.
