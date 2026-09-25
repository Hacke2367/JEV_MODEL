# Pending Work

**WIP:** `feature/frontend` (base `dev` @ 4b8ef47). Milestone 5 built (`4ce54f0`). Gate OK, grep checks 0. Waiting on the owner's manual browser checks (criteria 4–9, 11, 12).

- [x] Get JEVMODEL_API_KEY, put in `.env` (no card attached)
- [x] Smoke-test call, confirm `confidence` vs `probabilities` relationship
- [x] Build `/api/verdict` proxy (main.py)
- [x] Token/request cap
- [x] Frontend (static/), browser checks pending
- [ ] 10-scenario sanity check (scenarios.py)
- [ ] Deploy to free host, verify key not exposed
- [ ] Confirm success signal (live URL, <3s, 10/10 sane)

**Next up:**
1. Owner reports the result of each browser check (the Claude in Chrome extension was not connected, so the owner is testing by hand)
2. Fix any failures, then `/ship`
