# Donna Design Spec — Handoff Package v1.0

Everything needed to implement Donna's UI so the backend can generate the right
card with the right content on the right surface. Read in this order:

1. `DESIGN_SYSTEM.md` — the laws. Pixel truth lives in `/reference`.
2. `tokens/tokens.json` — single source of truth. Compile to CSS variables +
   Tailwind theme. **No hex values in components, ever.**
3. `schema/card.schema.json` — the card block vocabulary. This is the contract.
4. `mocks/*.json` — six validated example payloads. These are the spec for both
   the `Card` renderer (frontend) and the `render_card` tool (backend). All six
   validate against the schema and against `schema/models.py` (Pydantic).
5. `SURFACES.md` — how one payload projects to dashboard / notification / island.
6. `reference/*.html` — open in a browser at phone width. These are the approved
   mocks; the implemented app must match them.

## Build order (frontend)

1. Tokens → CSS vars + `tailwind.config` theme. (½ day)
2. Primitives from the inventory in DESIGN_SYSTEM.md §3, each with
   loading/empty/error states, demoed in a gallery route. 
3. The `Card` renderer: theme shell (dark/light/settled) + the ten block
   components. **Acceptance: the six payloads in `/mocks` render pixel-equal to
   their counterparts in `/reference`.**
4. Screens: Live → History → Dashboard (+ drawer). Wire to a single `src/api/`
   module returning the mocks, per the delivery spec.
5. Week-one spike: test backdrop-blur, grain, and the call-screen morph on a
   real Android WebView. If janky, flat-color fallbacks (tokens already define
   solid equivalents).

## Division of labor

- Frontend (this package): everything above, in React 18 + Vite + Tailwind,
  static `dist/`, per FRONTEND_DELIVERY_SPEC.
- Backend (Arnav): `render_card` tool definition, Pydantic validation
  (`schema/models.py`), action resolution, surface projection (SURFACES.md).
- Native iOS package (Arnav, separate): Dynamic Island, Live Activities,
  notification actions — consumes the same projections. Not WebView work.

## Drift control

`card.schema.json` is the single schema source. Frontend TS types and backend
Pydantic models are both checked against it in CI (json-schema-to-typescript on
one side; the included validation script pattern on the other). A payload that
validates must render; a payload that doesn't validate must fall back to text.
