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
