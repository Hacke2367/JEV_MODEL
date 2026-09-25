# Decision Game

Binary-verdict web app on the Jev API (jevmodel.org). Two modes: Advisor
(Go for it / Not go for it) and Judge (You are right / You are wrong).

Full context: `docs/project_context.md`
Plan: `docs/development_plan.md`
Decisions: `docs/decision.md`

## Shape
- `main.py` — FastAPI: serves `static/`, proxies `POST /api/verdict` to Jev, enforces the token cap.
- `static/` — plain HTML/JS/CSS, no framework, no build step.
- `scenarios.py` — 10-case sanity check against `/api/verdict`.

## Red lines (see `.claude/devsystem.json`)
- Jev API key never reaches the browser.
- Never a paid bill — cap enforced before free tokens run out.

## Conventions
- Key lives only in `.env` (`JEVMODEL_API_KEY`), read via `os.environ`. Never hardcode it.
- Jev call always uses `type: "choice"` with exactly 2 criteria keys — see project_context.md
  for the exact request/response shape.
- No accounts, no saved history, no explanation text, no non-binary answers (v1 scope).
