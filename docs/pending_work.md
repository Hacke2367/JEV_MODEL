# Pending Work

**WIP:** `feature/frontend` (base `dev` @ 4b8ef47). Milestone 5 built (`4ce54f0`). Gate OK, grep checks 0. Waiting on the owner's manual browser checks (criteria 4–9, 11, 12).

- [x] Get JEVMODEL_API_KEY, put in `.env` (no card attached)
- [x] Smoke-test call, confirm `confidence` vs `probabilities` relationship
- [x] Build `/api/verdict` proxy (main.py)
- [x] Token/request cap
- [x] Frontend (static/), browser checks pending
- [ ] OpenAI side-by-side classifier (milestone 6)
- [ ] 10-scenario sanity check (scenarios.py)
- [ ] Deploy to free host, verify key not exposed
- [ ] Confirm success signal (live URL, <3s, 10/10 sane)

**Next up:**
1. Owner finishes the browser checks for milestone 5, then `/ship` `feature/frontend`
2. Owner adds `OPENAI_API_KEY=...` to `.env` directly (not in chat), with auto-recharge off in OpenAI billing
3. `/start_work` milestone 6 (OpenAI side-by-side) → spec, including researching which cheap OpenAI model returns logprobs
