# Pending Work

**WIP:** none. Milestone 5 merged (PR #3).

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
1. Milestone 6, OpenAI side-by-side, on `feature/openai-compare`. Run `/start_work`, then the spec (research which cheap OpenAI model returns logprobs). No pending H-/P- items; H 2026-09-26 is decided.
2. Before building milestone 6, the owner adds `OPENAI_API_KEY=...` to `.env` directly (not in chat) and keeps auto-recharge off.
