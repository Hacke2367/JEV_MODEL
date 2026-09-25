# Session Log

## 2026-09-25
- `/kickoff` → `docs/project_context.md` written. Jev API researched (jevmodel.org, `choice`
  answer type, `/v1/systemone` endpoint). Interview covered framing, audience, scope, budget,
  stack, success signal, red lines.
- `/scaffold` → flat layout (Option A), tier `standard`. Created `.claude/devsystem.json`,
  `CLAUDE.md`, `.gitignore`, `.env.example`, `requirements.txt`, docs/ tree. `git init`,
  branch `chore/scaffold-project`.
- Jev API key added to `.env` (gitignored, verified not staged). Milestone 1 done.
- `/init` → rewrote `CLAUDE.md`: standard header, commands, request-flow architecture, `master`
  edit block. venv is Python 3.10.11, deps not yet installed.
- Scaffold PR #1 merged into `dev`. Next: milestone 2 (Jev smoke test) on `feature/jev-proxy`.

## 2026-09-26
- Spec and plan written for milestones 2+3 (`docs/specs/02_jev_proxy*.md`).
- Smoke test result: `confidence` is not `probabilities[choice]`, and one call costs 397 tokens
  (so the free tier is about 250 calls).
- Built `main.py` (the `/api/verdict` proxy and the cap) and `check_proxy.py` (offline, 15 cases,
  now the gate).
- Live results: Advisor answered in 2.0s. Judge answered "You are wrong" at 0.98. Invalid input
  returns 400. The key appears 0 times in the source and in responses.
- PR #2 merged into `dev` (proxy, cap, offline check). Next: milestone 5, frontend.
- Milestone 5: spec and plan written (`docs/specs/05_frontend*.md`). Built `static/` and the mount
  in `main.py`, and extended `check_proxy.py`. Gate OK.
- The Claude in Chrome extension was not connected (no browsers listed), so the owner chose to run
  the browser checks by hand. The server is running on :8000.
