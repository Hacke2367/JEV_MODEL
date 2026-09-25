# Spec: Jev Smoke Test + Verdict Proxy
**Version:** 1.0.0 | **Component:** backend (main.py)
**Status:** Approved, built (PR pending)

## 1. Problem Statement
The browser must never hold the Jev API key (red line, `.claude/devsystem.json`). Before any
frontend work, the app needs a server-side endpoint that takes a scenario/question, calls Jev,
and returns a verdict — and Jev's actual response shape (specifically how `confidence` relates
to `probabilities`) is unconfirmed (see `docs/project_context.md`, "UNVERIFIED").

## 2. Objective
One raw call confirms Jev's real response shape. Then `POST /api/verdict` on a running FastAPI
server takes `{mode, scenario, question}` and returns `{verdict, confidence}`, refusing before
the free token budget or a daily request cap is exhausted.

## 3. Scope & Constraints
**Will Do:**
- A one-off smoke-test script/call against `https://jevmodel.org/v1/systemone`.
- `main.py`: FastAPI app exposing `POST /api/verdict`.
- Input validation, Jev payload construction for both modes (Advisor / Judge), the Jev call with
  retry on 429/502, response mapping, and the usage cap.
- Load `JEVMODEL_API_KEY` from `.env`.

**Will NOT Do:**
- Frontend (`static/`) — milestone 5, separate spec.
- `scenarios.py` sanity script — milestone 6.
- Deployment — milestone 7.
- Accounts, saved history, explanation text, non-binary answers (out of v1 scope per
  `project_context.md`).

**Hard Rules (red lines):**
- The Jev key is read only from `.env` / a server env var. It must never appear in a response
  body, response header, or any code path reachable by the client.
- The proxy must refuse calls before the free-tier token budget or the daily cap is exhausted —
  never let a call risk a charge.

## 4. Core Design
- **Endpoint:** `POST /api/verdict`, body `{"mode": "advisor"|"judge", "scenario": str, "question": str}`.
- **Flow:** validate → build Jev `state`/`questions` payload for the mode (labels per
  `project_context.md`: `go_for_it`/`not_go_for_it` or `you_are_right`/`you_are_wrong`) → call Jev
  → map the returned `choice` key to its display label → return `{verdict, confidence}`.
- **Cap (two independent limits, either one blocks the call):**
  - Token floor: if the last-seen `X-Tokens-Remaining` is below a floor, refuse. Default floor:
    5,000 tokens (enough for ~25 more calls at ~200 tokens/call, so the app degrades before it
    can hit 0).
  - Daily request count: an in-memory counter reset at UTC midnight. Default: 40 requests/day
    (free tier is ~500 calls total; this gives ~12 days of demo headroom before a manual top-up
    decision, well inside the $0 constraint).
  - Both numbers live as constants at the top of `main.py`, easy to change without a spec update.
- **Retry:** on Jev 429/502, retry once after a short fixed delay (e.g. 1s). A second failure
  is surfaced as an error, not retried again (keeps worst-case latency low, matches the <3s
  success-signal target).

## 5. Edge Cases & Error Handling
| Case | Handling |
|---|---|
| Empty/whitespace-only scenario or question | 400, `{"error": "..."}, ` no Jev call made |
| `scenario` or `question` over Jev's limits (8,000 / part of `state`) | 400 before calling Jev |
| Unknown `mode` | 400 |
| Cap exceeded (token floor or daily count) | 429, `{"error": "Out of juice for today — try tomorrow."}`, no Jev call made |
| Jev 401 | 500 to the client (server misconfig, not a client error), logged server-side |
| Jev 402 | Treat as cap exceeded — same 429 response as above |
| Jev 422 | 500 to the client, logged (should not happen if our request-building is correct) |
| Jev 429/502 | Retry once; if it fails again, 502 to the client |
| Jev response missing expected `choice`/`probabilities` fields | 502 to the client, logged |

## 6. Acceptance Criteria
1. A raw smoke-test call against `https://jevmodel.org/v1/systemone` succeeds and the actual
   response JSON is captured (confirms or corrects the `confidence` assumption in
   `project_context.md`).
2. `POST /api/verdict` with a valid Advisor-mode body returns 200 with `{"verdict": "Go for it"|"Not go for it", "confidence": <0..1>}`.
3. Same for Judge mode, returning `"You are right"|"You are wrong"`.
4. Empty `scenario`, empty `question`, or an unknown `mode` returns 400 and makes no Jev call
   (verified by call count / mock).
5. `grep`-ing `main.py` and every response the endpoint returns for the literal API key string
   finds nothing.
6. Forcing the token floor or daily counter below/at the limit returns 429 with no Jev call made.
7. A single injected Jev 429 is retried and still succeeds; two in a row surface a 502.
