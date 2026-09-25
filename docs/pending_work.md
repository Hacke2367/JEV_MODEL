# Pending Work

**WIP:** `feature/jev-proxy` (base `dev` @ 3fc3d26) — Milestone 2 (smoke test) + 3 (proxy). Spec next.

- [x] Get JEVMODEL_API_KEY, put in `.env` (no card attached)
- [ ] Smoke-test call, confirm `confidence` vs `probabilities` relationship
- [ ] Build `/api/verdict` proxy (main.py)
- [ ] Token/request cap
- [ ] Frontend (static/)
- [ ] 10-scenario sanity check (scenarios.py)
- [ ] Deploy to free host, verify key not exposed
- [ ] Confirm success signal (live URL, <3s, 10/10 sane)

**Next up:**
1. `/spec` for milestone 2+3 → `docs/specs/02_jev_proxy.md`
2. Smoke test the Jev API
3. Build `main.py`
