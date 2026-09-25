# Decisions

## 2026-09-25: Kickoff decisions (owner)
- Two modes, chosen in the UI: Advisor (Go for it / Not go for it) and Judge (You are right / You are wrong).
- Audience: public portfolio piece.
- v1 shows the verdict plus a confidence %. No explanation text, no history, no accounts, no non-binary answers.
- Budget: $0. Free tier only, with a hard usage cap.
- Backend: Python FastAPI proxy that holds the key and serves the static HTML/JS.
- Red lines: the key never reaches the browser, and never a paid bill.
- Harmful-topic filtering was declined for v1. Accepted as a known risk, mitigated by a "For fun — not advice" footer.

## 2026-09-25: Jev `choice` over `noul` (Claude)
`choice` limits the output to our 2 labels and returns probabilities for both, so the label and the confidence % need no extra mapping. `noul` stays as the fallback.

## 2026-09-26: Bootstrap onto existing GitHub repo (owner)
Owner supplied an existing public repo (`Hacke2367/JEV_MODEL`, `main` with only a LICENSE commit).
Rebased the local scaffold commits onto its `main`, created `dev` from `main`, pushed `dev`.
Scaffold branch now ships as a normal PR into `dev` instead of a local-only bootstrap.
Verified before pushing: the real Jev API key is not in git history or any tracked file
(only the `sk-...` placeholder appears, in `.env.example` and docs).

## 2026-09-26: Confidence comes from `probabilities[choice]`, confirmed by the smoke test (Claude)
The smoke test returned `confidence` 0.58 with `probabilities` 0.79 / 0.21, so `confidence` looks
like the top-two margin rather than how sure Jev is of its answer. `main.py` returns
`probabilities[choice]` as the confidence %. Recorded as D6 in `specs/02_jev_proxy_impl.md`.

## 2026-09-26: Free tier is about 250 calls, not 500. Cap defaults unchanged (owner's call)
One call cost 397 input tokens, against the ~200 that jevmodel.org implies. That makes 100k
free tokens about 250 calls. At `DAILY_LIMIT` 40 (about 16k tokens a day) the free tier lasts
about 6 days, and `TOKEN_FLOOR` 5000 still stops calls before the balance reaches 0, so the
"never a paid bill" red line holds. If more runway is wanted, lower `DAILY_LIMIT` in `main.py`.

## 2026-09-26: Accepted residual risk: a restart resets the in-memory cap (Claude)
After a restart, `DAILY_LIMIT` counts from 0 again, and the first call runs before
`TOKEN_FLOOR` has a balance to check. This was accepted as part of the in-memory cap
decision (D3 in `specs/02_jev_proxy_impl.md`). It cannot produce a bill: jevmodel only sells
prepaid tokens, no card is attached, and when the tokens run out Jev returns a 402, which the
proxy turns into "out of juice". Revisit if the host restarts often, for example a free tier
that sleeps when idle.
