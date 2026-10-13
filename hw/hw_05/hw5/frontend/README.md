# Campus Customs Desk (frontend)

React + Vite + TypeScript board for the HW5 agent team. See `../README.md`
for the full start order (MCP server → backend → this) and
`../output/design.md` for the design.

```bash
npm install
npm run dev     # http://localhost:5173, opens in your browser
```

`/api` is proxied to the FastAPI backend at `http://127.0.0.1:8000`
(override with `HW5_BACKEND`). `npm run build` type-checks and builds.
