# Pending Work

**WIP:** `feature/jev-proxy` (base `dev` @ 3fc3d26) — Milestone 2+3. Spec + plan written (`docs/specs/02_jev_proxy*.md`).

- [x] Get JEVMODEL_API_KEY, put in `.env` (no card attached)
- [ ] Smoke-test call, confirm `confidence` vs `probabilities` relationship
- [ ] Build `/api/verdict` proxy (main.py)
- [ ] Token/request cap
- [ ] Frontend (static/)
- [ ] 10-scenario sanity check (scenarios.py)
- [ ] Deploy to free host, verify key not exposed
- [ ] Confirm success signal (live URL, <3s, 10/10 sane)

**Next up:**
1. `pip install -r requirements.txt`, then build `smoke_test.py` and run it (D6 gate in the plan)
2. Build `main.py`, then `check_proxy.py`
3. `/ship`
