# Development Plan

Source: `project_context.md` → "Step-by-step plan to start coding".

## Milestones
1. **Key** — sign up at jevmodel.org, `.env` holds `JEVMODEL_API_KEY`, no card attached.
2. **Smoke test** — one raw `curl` call, confirm response shape + `confidence` semantics.
3. **Proxy** — `POST /api/verdict` in FastAPI: validate input, build Jev payload per mode,
   call Jev (retry 429/502), map choice → label, return `{verdict, confidence}`.
4. **Cap** — refuse once `X-Tokens-Remaining` < floor or daily request count exceeded.
5. **Frontend** — `static/index.html` + `app.js` per the UI sketch in project_context.md.
6. **OpenAI side-by-side** (added 2026-09-26) — an OpenAI model classifies the same input using
   the same `MODE_CONFIG` roles; confidence from `logprobs`; both verdicts shown side by side;
   OpenAI calls capped. Needs `OPENAI_API_KEY` in `.env`.
7. **Test set** — `scenarios.py`, 10 cases (5/mode) against `/api/verdict`, eyeball sanity.
8. **Deploy** — free Python host, keys as host env vars, verify keys absent from page source/network tab.
9. **Success check** — live URL, <3s response, 10/10 sane verdicts.

## Status
Milestones 1–5 done: scaffold (PR #1), smoke test + proxy + cap (PR #2), frontend (PR #3). Next: milestone 6 (OpenAI side-by-side).
