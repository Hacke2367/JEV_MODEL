# Spec: Frontend (single page)
**Version:** 1.0.0 | **Component:** frontend (`static/`) + static serving in `main.py`
**Status:** Approved, built (PR pending)

## 1. Problem Statement
The backend (`POST /api/verdict`, PR #2) works, but only through `curl`. The product is a public
portfolio piece: a stranger opens a link and should get a verdict without instructions
(`project_context.md`, Success signal). That needs a page, served by the same process as the
API, so there is one deploy and the key stays on the server.

## 2. Objective
Opening `/` shows a single page. A visitor picks a mode, types a scenario and a question, and
sees the verdict plus "NN% sure" from `/api/verdict`. Every error state shows a readable message
instead of a blank or broken page.

## 3. Scope & Constraints
**Will Do:**
- `static/index.html`, `static/app.js`, and one CSS file.
- Serve `static/` from `main.py` at `/`. `POST /api/verdict` keeps working unchanged.
- Mode toggle (Advisor / Judge), scenario textarea, question input, "Get verdict" button,
  result card, and the footer "For fun — not advice."
- Mode-specific labels and placeholder examples, so a first-time visitor knows what to type.
- A loading state, and error display for every response `/api/verdict` can return.

**Will NOT Do:**
- No framework, no library, no CDN, no build step (`project_context.md`: "Libraries: none").
- No history, no localStorage, no accounts (v1 scope).
- No explanation text. Jev returns only a label and probabilities.
- No dark mode, no animations beyond a simple loading indicator, no sharing or social buttons.
- No change to the `/api/verdict` contract or to the cap logic.
- No deploy (milestone 7).

**Hard Rules:**
- **Red line:** the page contains no API key and calls nothing but the relative path
  `/api/verdict`. The browser never talks to Jev directly.
- Server text (verdict labels and error messages) is shown as plain text, never parsed as HTML.
- Accessibility basics:
  - Every input has a visible label.
  - All controls are reachable and usable with the keyboard alone.
  - The result is announced to screen readers when it appears.
  - The verdict is never shown by colour alone; the words are always there.
- Usable at phone width (375px) with no horizontal scrolling.

## 4. Core Design
**Layout** (from `project_context.md`, "Planned UI"), top to bottom:
1. Title "Decision Game".
2. Mode toggle: two options, Advisor selected by default.
3. Scenario textarea: at most 1,500 characters, required.
4. Question input: one line, at most 300 characters, required.
5. "Get verdict" button.
6. Result area: empty at first. It shows either a verdict card or an error message.
7. Footer: "For fun — not advice."

**Mode-specific text:**

| | Advisor | Judge |
|---|---|---|
| Question label | "Your question" | "Your position" |
| Scenario placeholder | a dilemma, e.g. two job offers | a disagreement, e.g. splitting rent with a roommate |
| Question placeholder | "Should I take the startup job?" | "Am I right that rent should stay 50/50?" |
| Possible verdicts | "Go for it" / "Not go for it" | "You are right" / "You are wrong" |

The API field is still called `question` in both modes; only the on-screen label changes.

**Verdict card:**
- The verdict text, large.
- "NN% sure", where NN is `confidence × 100` rounded to a whole number.
- A bar filled to NN%.
- The positive verdicts ("Go for it", "You are right") and the negative ones get different
  colours, but the text is always shown (see Hard Rules).

**Flow:**
1. The visitor submits, with the button or with Enter in the question field.
2. While waiting, the button and every input, including the mode toggle, are disabled, and a
   "Thinking…" state is shown. This prevents double submits, and a verdict can't arrive for a
   mode that has since been switched.
3. The page sends `POST /api/verdict` with `{mode, scenario, question}` as JSON.
4. On 200, the verdict card is shown. On any other status, the `error` text from the response
   body is shown in the result area.
5. Controls are re-enabled.

Switching mode clears the result area. The scenario and question text stay.

**Serving:** `/` returns `index.html`, and the CSS and JS are served from the same origin. The
static mount must not shadow `/api/verdict`.

## 5. Edge Cases & Error Handling
| Case | What the visitor sees |
|---|---|
| Scenario or question empty | The browser's native "required" prompt. No request is sent |
| Text longer than the limit | The field stops accepting input at the limit. No request is sent |
| 400 from the API (e.g. whitespace-only input that passed the browser check) | The server's `error` text in the result area |
| 429 "Out of juice for today — try tomorrow." | That exact text in the result area |
| 500 or 502 from the API | The server's `error` text ("Server misconfiguration" / "Jev unavailable, try again") |
| Response body is not JSON, or has no `error` field (e.g. a host error page) | "Something went wrong — try again." |
| Network failure (offline, server down) | "Can't reach the server — check your connection." |
| No response within 15 seconds | Request cancelled, then "Took too long — try again." Controls re-enabled |
| Visitor switches mode after a verdict | Result area cleared. No stale verdict left under the new mode's labels |

The 15-second limit sits above the backend's worst case: a Jev call that times out at 5s, a 1s
wait, then a retry that also times out, which comes to about 11s.

## 6. Acceptance Criteria
1. `GET /` returns 200 with HTML containing the mode toggle, the scenario textarea, the question
   input and the "Get verdict" button.
2. `GET` on the CSS and JS files returns 200.
3. After the static mount, `POST /api/verdict` still behaves exactly as before:
   `check_proxy.py` passes.
4. **Advisor flow, in a real browser against the running server:**
   - Submitting the example scenario shows "Go for it" or "Not go for it", "NN% sure", and a bar
     filled to NN%.
   - NN matches the `confidence` in the network response × 100, rounded.
5. **Judge flow:** after switching to Judge, the label reads "Your position", and submitting shows
   "You are right" or "You are wrong".
6. **While a request is in flight:**
   - The button and every input are disabled.
   - "Thinking…" is visible.
   - Everything is re-enabled once the response arrives.
7. Submitting with an empty field sends no request (the network log shows nothing).
8. A 429 response makes the result area read exactly "Out of juice for today — try tomorrow.".
9. With the server stopped, submitting shows "Can't reach the server — check your connection."
10. `grep -rc "sk-" static/` → 0 in every file. The network log shows requests only to the same
    origin.
11. At 375px width there is no horizontal scrollbar, and every control is visible and usable.
12. The whole flow (tab to each control, type, submit) works with the keyboard only. The result
    area is an `aria-live` region.

## 7. UI/UX Behavior
- The result card appears in place. The page doesn't jump to a new view.
- The labels and the button text stay plain and short: a stranger should need no instructions.
- No character counter; the `maxlength` limit is enough (YAGNI).
