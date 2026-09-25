# Pending Work

**WIP:** `feature/jev-proxy` (base `dev` @ 3fc3d26). Milestones 2+3 built. Offline check and live acceptance pass. Ready to `/ship`.

- [x] Get JEVMODEL_API_KEY, put in `.env` (no card attached)
- [x] Smoke-test call, confirm `confidence` vs `probabilities` relationship
- [x] Build `/api/verdict` proxy (main.py)
- [x] Token/request cap
- [ ] Frontend (static/)
- [ ] 10-scenario sanity check (scenarios.py)
- [ ] Deploy to free host, verify key not exposed
- [ ] Confirm success signal (live URL, <3s, 10/10 sane)

**Next up:**
1. `/ship` feature/jev-proxy → PR into `dev`
2. `/start_work` milestone 5 (frontend, `static/`)
