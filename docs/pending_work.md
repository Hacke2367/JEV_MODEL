# Pending Work

**WIP:** `feature/frontend` (base `dev` @ 4b8ef47). Milestone 5, frontend. Spec + plan written (`docs/specs/05_frontend*.md`).

- [x] Get JEVMODEL_API_KEY, put in `.env` (no card attached)
- [x] Smoke-test call, confirm `confidence` vs `probabilities` relationship
- [x] Build `/api/verdict` proxy (main.py)
- [x] Token/request cap
- [ ] Frontend (static/)
- [ ] 10-scenario sanity check (scenarios.py)
- [ ] Deploy to free host, verify key not exposed
- [ ] Confirm success signal (live URL, <3s, 10/10 sane)

**Next up:**
1. Build: `static/` files → mount in `main.py` → extend `check_proxy.py` → `CLAUDE.md`
2. Browser checks via Claude in Chrome (criteria 4–9, 11, 12; about 1.2k tokens)
3. `/ship`
