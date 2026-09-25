# Pending Work

**WIP:** `feature/frontend` (base `dev` @ 4b8ef47). Milestone 5 in review: gate OK, owner's browser checks passed.

- [x] Get JEVMODEL_API_KEY, put in `.env` (no card attached)
- [x] Smoke-test call, confirm `confidence` vs `probabilities` relationship
- [x] Build `/api/verdict` proxy (main.py)
- [x] Token/request cap
- [x] Frontend (static/)
- [ ] OpenAI side-by-side classifier (milestone 6)
- [ ] 10-scenario sanity check (scenarios.py)
- [ ] Deploy to free host, verify key not exposed
- [ ] Confirm success signal (live URL, <3s, 10/10 sane)

**Next up:**
1. Owner reviews and merges the frontend PR (`/merge_pr`)
2. Owner adds `OPENAI_API_KEY=...` to `.env` directly (not in chat), with auto-recharge off in OpenAI billing
3. `/start_work` milestone 6 (OpenAI side-by-side) → spec, including researching which cheap OpenAI model returns logprobs
