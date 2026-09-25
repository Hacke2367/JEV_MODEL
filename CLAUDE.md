# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project
Decision Game: binary-verdict web app on the Jev typed-decision API (jevmodel.org, an unofficial
reseller of TypeSafe AI's Jev). It has two modes:
- **Advisor:** "Go for it" / "Not go for it"
- **Judge:** "You are right" / "You are wrong"

- Context, scope, and the exact Jev request/response shapes: `docs/project_context.md`
- Milestones and current status: `docs/development_plan.md`
- Decisions: `docs/decision.md`

**Status:** backend proxy (`main.py`) and frontend (`static/`) built. `scenarios.py` is not written yet.

## Commands (Windows, Python 3.10 venv)
```
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload                    # main.py loads .env itself
python check_proxy.py                        # offline check, Jev mocked; this is the /ship gate
python smoke_test.py                         # one REAL Jev call (~400 tokens): prints the raw response
python scenarios.py                          # 10-case live sanity run (milestone 6); needs server running
```
There is no test framework and no linter. `check_proxy.py` is plain asserts with a single entry
point, so run the whole file; there is no way to run one case alone.

## Architecture
The browser never talks to Jev directly. Request flow:
1. `static/app.js` sends `POST /api/verdict` with `{mode, scenario, question}`.
2. `main.py` (FastAPI) handles it:
   - validates the input
   - builds the Jev payload
   - calls `POST https://jevmodel.org/v1/systemone`
3. `main.py` returns `{verdict, confidence}` to the browser.

- **One process:** `main.py` also serves `static/` (plain HTML/JS/CSS, no framework, no build step), so there is one process and one deploy.
  The `StaticFiles` mount at `/` must stay the **last** registration in `main.py`, because it
  matches every path and shadows any route added after it.
- **Jev call:** always `type: "choice"` with exactly 2 criteria keys. Mode changes only
  `instructions` and the key names.
- **Confidence %:** read from the Jev response's `probabilities`.
- **Usage cap:** lives in `main.py`. It refuses calls when the Jev response header
  `X-Tokens-Remaining` drops below a floor, or when an in-memory daily counter is exceeded.
  There is no database.
- **Key:** `JEVMODEL_API_KEY` in `.env` (gitignored). The host sets it as an env var in deploy.

## Red lines (also in `.claude/devsystem.json`, checked by `/ship`)
- The Jev key never reaches the browser, in any HTML, JS, or response header or body.
- Never a paid bill. The free tier is about 100k input tokens, and the cap must stop calls before
  they run out.

## v1 scope limits
No accounts, no saved history (not even localStorage), no explanation text, no non-binary answers.

## Workflow
The devsystem plugin blocks edits on `master`. Work on a branch (`/start_work`) and ship via `/ship`.
