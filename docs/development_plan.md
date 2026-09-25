# Development Plan

Source: `project_context.md` → "Step-by-step plan to start coding".

## Milestones
1. **Key** — sign up at jevmodel.org, `.env` holds `JEVMODEL_API_KEY`, no card attached.
2. **Smoke test** — one raw `curl` call, confirm response shape + `confidence` semantics.
3. **Proxy** — `POST /api/verdict` in FastAPI: validate input, build Jev payload per mode,
   call Jev (retry 429/502), map choice → label, return `{verdict, confidence}`.
4. **Cap** — refuse once `X-Tokens-Remaining` < floor or daily request count exceeded.
5. **Frontend** — `static/index.html` + `app.js` per the UI sketch in project_context.md.
6. **Test set** — `scenarios.py`, 10 cases (5/mode) against `/api/verdict`, eyeball sanity.
7. **Deploy** — free Python host, key as host env var, verify key absent from page source/network tab.
8. **Success check** — live URL, <3s response, 10/10 sane verdicts.

## Status
Milestones 1–4 done (2+3+4 on `feature/jev-proxy`: smoke test, proxy, cap). Next: ship it, then milestone 5 (frontend).
