# Project Context: Decision Game

## Problem
People want a quick, decisive nudge on a small dilemma ("should I…?") or a ruling on a
disagreement ("am I right?"), and most AI tools give them essays instead of a straight answer.
The owner also wants a portfolio piece that shows a real integration with a new typed-decision
AI API (Jev), not another chatbot wrapper.

## Objective
v1 is a public web page. The user picks a mode, types a short scenario and a question, and gets a
**binary verdict with a confidence %** from Jev.
- **Advisor mode:** "Go for it" / "Not go for it"
- **Judge mode:** "You are right" / "You are wrong"

## Who it's for
- **Portfolio piece.** Recruiters and visitors who open the link, with no instructions.
- **The owner.** Shows off the Jev integration.

## Scope
**In scope:**
- Two modes, switched in the UI, that share one Jev call shape.
- A verdict and a confidence % taken from Jev's probabilities.
- A server-side proxy that holds the API key, plus a usage cap.
- A public deployment on a free host.

**Out of scope (v1):**
- User accounts or login.
- Saved history of any kind, including localStorage.
- Explanation text ("why"). Jev returns only labels and probabilities, and adding a second LLM is out.
- Non-binary answers: no "maybe", no multi-option, no 1–10 scores.

## Constraints
- **Money: $0.** Free tier only (100,000 input tokens ≈ 500 calls). The proxy enforces a cap and
  shows a friendly "out of juice" message once it's hit.
- **Stack:** a Python backend (FastAPI) serves the proxy and the static HTML/JS. The owner is
  comfortable in Python, and a venv already exists.
- **Hosting:** must be a free tier. The exact host is picked at `/scaffold`.
- **Jev limits:**
  - 120 requests/min per key.
  - `state` ≤ 8,000 chars.
  - `instructions` ≤ 1,800 chars.
  - `criteria` ≤ 2,000 chars.

## What already exists that's close
- **`C:\decision_game`:** contains only an empty venv, with no code to reuse.
- **Official TypeSafe API** (`https://api.typesafe.ai/v1/systemone`): same request shape and the same
  Bearer auth. Switching to it later only means changing the base URL and the key.
- **Cloudflare Workers AI** (`typesafe/jev`): another route. Rejected because the stack constraint
  is Python.
- None of these is the app itself. They are only ways to reach the model.

## Success signal
All of the following:
- The public URL is live.
- A stranger gets a verdict in **under 3 s** with no instructions.
- **10 hand-picked test scenarios** (5 per mode) all get sensible verdicts.

## Red lines
- **The API key never reaches the browser.** It must not appear in HTML, JS, git, or any response
  body or header sent to the client. It lives only in a server environment variable.
- **Never a paid bill.** No card is attached to the Jev account, and the proxy stops before the
  free tokens run out.

## Known risk (accepted, not a red line)
A blind binary classifier will get harmful inputs ("should I stop my meds?") and may answer
"Go for it". The owner chose not to block these topics in v1. Cheap mitigation: a fixed footer
reading "For fun — not advice."

---

## How Jev fits this task
Jev (made by TypeSafe AI, launched 2026-09-15) is **not a chatbot**. You send it application state
plus typed questions, and it returns an answer your code can branch on. It has three answer
types: `choice`, `noul` (a yes/no probability) and `score`.

**We use `type: "choice"` with exactly 2 keys:**
- The output is limited to the keys we supply, so it can never produce free text or a third answer.
- It returns `probabilities` for both keys plus `confidence`. That gives us the confidence % for free.
- Mode only changes the `instructions` and the `criteria` keys. The call shape stays the same.

We use `noul` as the fallback only. It returns a single yes-probability, and we would have to map
it to labels ourselves.

Source: jevmodel.org, an **unofficial reseller** that is not affiliated with TypeSafe. The official
docs are at `https://docs.typesafe.ai/`.

## API request / response format

**Endpoint:** `POST https://jevmodel.org/v1/systemone`

**Headers:**
- `Authorization: Bearer $JEVMODEL_API_KEY` (keys start with `sk-`)
- `Content-Type: application/json`

**Request (Advisor mode):**
```json
{
  "model": "jev-latest",
  "state": {
    "scenario": "I have 2 offers: a startup paying 20% more, or my stable job...",
    "question": "Should I join the startup?"
  },
  "questions": {
    "verdict": {
      "type": "choice",
      "instructions": "The user describes a situation and asks whether to do something. Decide if doing it is the better choice.",
      "criteria": {
        "go_for_it": "Doing it is the better decision given the scenario.",
        "not_go_for_it": "Not doing it is the better decision given the scenario."
      }
    }
  }
}
```

**Judge mode** uses the same shape with different instructions and criteria:
- `instructions`: "The user describes a situation and states their position. Decide if their position is correct."
- `criteria`: `you_are_right` / `you_are_wrong`

**Response (200):**
```json
{
  "model": "jev-latest",
  "answers": {
    "verdict": {
      "type": "choice",
      "choice": "go_for_it",
      "probabilities": { "go_for_it": 0.82, "not_go_for_it": 0.18 },
      "confidence": 0.82
    }
  },
  "usage": { "input_tokens": 136, "output_tokens": 18 }
}
```
The response header `X-Tokens-Remaining` gives the token balance, and we use it for the cap.
Confirmed by the smoke test (2026-09-26): `confidence` is NOT `probabilities[choice]`. One call returned `confidence` 0.58 with probabilities 0.79 / 0.21, so `confidence` looks like the top-two margin. The UI uses `probabilities[choice]`. The response `model` field is the resolved version (e.g. `jev-1.13.0`). One call cost 397 input tokens, so the free tier is about 250 calls, not 500.

**Errors:** the body is `{"error":{"type":"...","message":"..."}}`.

| Code | Meaning | Handling |
|---|---|---|
| 401 | Bad key | Fix the key |
| 402 | Out of tokens | Show the "out of juice" message |
| 422 | Bad request | Check limits and request shape |
| 429 | Rate limited | Retry with backoff |
| 502 | Upstream error | Retry with backoff |

**Our proxy contract** (the browser talks only to this):
```
POST /api/verdict   {"mode": "advisor"|"judge", "scenario": "...", "question": "..."}
→ 200 {"verdict": "Go for it", "confidence": 0.82}
→ 429/503 {"error": "Out of juice for today — try tomorrow."}
→ 400 {"error": "..."}   (empty/too-long input)
```

## Planned UI (single page, plain HTML/JS)
```
┌─────────────────────────────────────────┐
│  Decision Game                          │
│  [ Advisor ]  [ Judge ]   ← mode toggle │
│  Scenario:  [ textarea, max ~1500 ch ]  │
│  Question:  [ one-line input         ]  │
│  [ Get verdict ]                        │
│  ┌───────────────────────────────────┐  │
│  │   GO FOR IT                        │  │
│  │   ██████████████░░░  82% sure      │  │
│  └───────────────────────────────────┘  │
│  For fun — not advice.                  │
└─────────────────────────────────────────┘
```
- **Files:** `index.html`, `app.js` and one CSS file.
- **Libraries:** none.
- **Behaviour:**
  - The button is disabled while waiting.
  - A spinner or "thinking…" state shows during the call.
  - Error text appears where the result card goes.
- The labels on the question field and the result card change with the mode.

## Step-by-step plan to start coding
1. **Key.**
   - Sign in at jevmodel.org to get the 100k free tokens.
   - Put `JEVMODEL_API_KEY=sk-...` in `.env`.
   - Add `.env` to `.gitignore` before the first commit.
   - Attach no card.
2. **Smoke test.**
   - Send one `curl` request with the Advisor payload above.
   - Confirm the response shape and check `confidence` against `probabilities`.
   - Note the `X-Tokens-Remaining` value.
3. **Proxy.** In FastAPI, build `POST /api/verdict`:
   - Validate the mode and the input lengths.
   - Build the Jev payload for the chosen mode.
   - Call Jev with `httpx`, retrying 429/502 once with backoff.
   - Map the returned key to a display label.
   - Return `{verdict, confidence}`.
4. **Cap.**
   - Refuse calls once `X-Tokens-Remaining` falls below a floor (e.g. 5,000).
   - Also refuse beyond a daily request count (in memory).
   - Either way, return the "out of juice" message.
5. **Frontend.** Build `index.html` and `app.js` per the UI above, served by FastAPI as static files.
6. **Test set.**
   - Write 10 scenarios (5 per mode) in a small script that hits `/api/verdict`.
   - Eyeball every verdict for sanity.
7. **Deploy.**
   - Deploy to a free Python host, with the key set as a host environment variable.
   - Check the page source and the browser's network tab to confirm the key is absent.
8. **Success check.** Confirm the live URL, the under-3 s response time and the 10/10 sensible
   verdicts (see *Success signal*).
