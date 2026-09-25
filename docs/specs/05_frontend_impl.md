# Plan: Frontend (single page)
**Spec:** `05_frontend.md` | **Status:** Ready for Build

## 1. Files
| Action | File | Reason |
|---|---|---|
| CREATE | `static/index.html` | Spec §4, the page layout |
| CREATE | `static/app.js` | Spec §4 and §5: mode switching, submit, loading state, error display |
| CREATE | `static/style.css` | Spec §3 hard rules: 375px width, colour not the only signal, visible focus |
| MODIFY | `main.py` | Add the `StaticFiles` mount at `/`. It must come last (D1) |
| MODIFY | `check_proxy.py` | Criteria 1–3 and 10 run inside the gate: page and assets served, API not shadowed, no key or external URL in `static/` |
| MODIFY | `CLAUDE.md` | Update the Status line, and record that the mount must stay last |

**Conflicts with existing code:**
- `main.py` has no static mount on purpose. That was D4 in `02_jev_proxy_impl.md`, deferred to
  this milestone, and this plan reverses it.
- `CLAUDE.md` line 15 says `static/` is not written yet.
- Nothing else conflicts.

## 2. Architecture Decisions

**D1: Mount `StaticFiles(directory=..., html=True)` at `/`, as the last thing in `main.py`.**
- Why: the spec asks for one origin with `/` serving the page. Starlette matches routes in
  registration order, and a mount at `/` matches every path. So it has to be registered after
  `@app.post("/api/verdict")`, or it swallows the API (spec §4: "must not shadow").
- `html=True` makes `/` serve `index.html`.
- The directory is resolved from the location of `main.py`
  (`Path(__file__).resolve().parent / "static"`), not from the current working directory. That
  way the app works however uvicorn or the host is started.
- Side effect: `GET /api/verdict` becomes 404 from `StaticFiles` instead of 405. Only `POST` is in
  the contract, so this is acceptable.
- Rejected: mounting under `/static` plus a separate `GET /` route that returns `index.html`.
  That is more code, and the asset URLs in the page would need a `/static/` prefix.

**D2: Mode toggle uses two native radio inputs inside a `<fieldset>`/`<legend>`.**
- Why: the spec's accessibility rules. Radios come with keyboard support (arrow keys), a group
  label, and their state exposed to screen readers.
- Styling turns them into a two-button segmented control. The inputs are visually hidden but
  still focusable, and the focus ring is drawn on their label.
- Rejected: `<button aria-pressed>` pairs. They need hand-written keyboard and ARIA handling.

**D3: All controls sit inside one `<fieldset id="controls">`, and `controls.disabled = true`
disables them all at once.**
- Why: spec flow step 2, disable everything while waiting. A disabled fieldset disables every
  input inside it, including the nested mode fieldset, without code per element.
- Catch: controls inside the **first `<legend>`** of a disabled fieldset stay enabled. So
  `#controls` has no `<legend>`, and in the nested mode fieldset the legend holds only the text
  "Mode", with the radios outside it. Also reset the default fieldset border and padding in CSS.

**D4: Native `required` and `maxlength` handle empty and over-long input.**
- Why: spec §5 rows 1–2. The browser blocks the `submit` event before any JavaScript runs, so no
  request is sent (criterion 7).
- Whitespace-only input passes this check. The server's 400 then covers it, as the spec says.

**D5: Timeout uses `AbortSignal.timeout(15000)`.**
- Why: spec §5, the 15s limit. This is native and needs no `setTimeout`/`AbortController`
  bookkeeping.
- On expiry it rejects with `err.name === "TimeoutError"`.
- Supported in every current browser (Chrome 103+, Firefox 100+, Safari 16+).

**D6: Every piece of server text goes through `textContent`.**
- Why: spec hard rule. Nothing in `static/` uses `innerHTML`; a grep enforces this in §10.

**D7: Tests happen in two layers.**
- **Gate (`check_proxy.py`):** checks that files are served and scans them for the key and for
  external URLs. It is offline and fast.
- **Real browser (Claude in Chrome, running against `uvicorn`):** checks UI behaviour.
- Why: the spec's UI criteria (4–9, 11, 12) need a real DOM. Adding a JavaScript test framework
  or headless browser dependency to the gate isn't warranted for one page (YAGNI), and
  `/ship` step 4 requires a real-browser check anyway.

## 3. Data Structures

**`app.js` constants**

| Name | Value | Enforces |
|---|---|---|
| `API_PATH` | `"/api/verdict"` | Relative path only (red line) |
| `TIMEOUT_MS` | `15000` | Spec §5 timeout |
| `MSG_GENERIC` | `"Something went wrong — try again."` | Spec §5, non-JSON / no `error` |
| `MSG_NETWORK` | `"Can't reach the server — check your connection."` | Spec §5, network failure |
| `MSG_TIMEOUT` | `"Took too long — try again."` | Spec §5, timeout |
| `POSITIVE` | `new Set(["Go for it", "You are right"])` | Spec §4, verdict colour class |
| `MODES` | see below | Spec §4, mode-specific text table |

```
MODES = {
  advisor: { questionLabel: "Your question",
             scenarioPlaceholder: <dilemma example: two job offers>,
             questionPlaceholder: "Should I take the startup job?" },
  judge:   { questionLabel: "Your position",
             scenarioPlaceholder: <disagreement example: rent with a roommate>,
             questionPlaceholder: "Am I right that rent should stay 50/50?" },
}
```
The keys `advisor` and `judge` must match the radio `value`s and `main.py`'s
`Literal["advisor", "judge"]`.

**DOM IDs** (`app.js` depends on these; `check_proxy.py` asserts some of them):

| ID or name | Element | Purpose |
|---|---|---|
| `verdict-form` | `<form>` | Submit handler |
| `controls` | `<fieldset>` | D3, disabled while busy |
| `name="mode"` | 2 × `<input type="radio">` | Values `advisor` (checked) and `judge` |
| `scenario` | `<textarea>` | `maxlength="1500" required` |
| `question` | `<input type="text">` | `maxlength="300" required` |
| `question-label` | `<label for="question">` | Text swaps per mode |
| `submit` | `<button type="submit">` | Text: "Get verdict" / "Thinking…" |
| `result` | `<section>` | `aria-live="polite"`; holds either the card or the error |

## 4. Function Specifications (`app.js`)

**`applyMode(mode: "advisor" | "judge"): void`**
- Sets the `question-label` text and both placeholders from `MODES[mode]`.
- Clears the result by calling `clearResult()`.
- Called on each radio's `change` event, and once at load for the checked radio. The load call
  keeps the page right if the browser restores a Judge selection on reload.

**`clearResult(): void`**
- Empties `#result` with `replaceChildren()`.

**`setBusy(busy: boolean): void`**
- Sets `controls.disabled = busy`.
- Sets the `submit` text to "Thinking…" when busy and "Get verdict" when not.
- Sets `result.setAttribute("aria-busy", busy)`.

**`showVerdict(verdict: string, confidence: number): void`**
- Computes `pct = Math.round(confidence * 100)`.
- Builds a card: `<div class="card positive|negative">` containing:
  - `<p class="verdict">` with the verdict as `textContent`
  - `<p class="sure">` with `` `${pct}% sure` `` as `textContent`
  - `<div class="bar" aria-hidden="true"><div class="bar-fill" style.width = pct + "%"></div></div>`
- The card gets the `positive` class if `POSITIVE.has(verdict)`, otherwise `negative`.
- Replaces the contents of `#result` with the card.

**`showError(message: string): void`**
- Replaces the contents of `#result` with `<p class="error">`, with `message` as `textContent`.

**`async requestVerdict(payload: {mode, scenario, question}): Promise<{verdict, confidence}>`**
- Calls `fetch(API_PATH, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload), signal: AbortSignal.timeout(TIMEOUT_MS) })`.
- Throws `Error(<user-facing message>)` in these cases (§5):
  - `fetch` rejects with name `TimeoutError` or `AbortError` → `MSG_TIMEOUT`
  - `fetch` rejects with anything else → `MSG_NETWORK`
  - `resp.json()` rejects → `MSG_GENERIC`
  - `!resp.ok` → `body.error` if it is a non-empty string, otherwise `MSG_GENERIC`
  - `resp.ok`, but `verdict` is not a string or `confidence` is not a number → `MSG_GENERIC`
- Returns `{verdict, confidence}`.

**`async onSubmit(event: SubmitEvent): void`**
- The flow in §5. Registered on `verdict-form`'s `submit` event.

## 5. Logic Flow

**Submit** (`onSubmit`):
1. `event.preventDefault()`. The native `required`/`maxlength` checks have already passed, or
   this event would not have fired (D4).
2. Read `payload` from `new FormData(form)`: `mode`, `scenario`, `question`. This must happen
   **before** `setBusy(true)`, because `FormData` skips disabled controls.
3. `setBusy(true)`, then `clearResult()`.
4. Call `requestVerdict(payload)` inside `try`.
   - On success, call `showVerdict(verdict, confidence)`.
   - In `catch (err)`, call `showError(err.message)`.
5. In `finally`, call `setBusy(false)`.

**Mode change:** radio `change` → `applyMode(event.target.value)`. The textarea and input
values are left as they are (spec §4).

**Load:** `applyMode(<checked radio value>)` at startup. The script has `defer`, so the DOM is
ready when it runs.

## 6. Edge Case Implementation Map
| Spec edge case | Mechanism | Location |
|---|---|---|
| Empty scenario or question | `required` → native prompt, no `submit` event | `index.html` attributes |
| Over the length limit | `maxlength` → input stops at the limit | `index.html` attributes |
| 400 (e.g. whitespace-only input) | `!resp.ok` → `body.error` | `requestVerdict()` |
| 429 out of juice | `!resp.ok` → `body.error` (the exact server text) | `requestVerdict()` |
| 500 / 502 | `!resp.ok` → `body.error` | `requestVerdict()` |
| Non-JSON response or no `error` field | `resp.json()` rejects, or `error` missing → `MSG_GENERIC` | `requestVerdict()` |
| Network failure | `fetch` rejects (not a timeout) → `MSG_NETWORK` | `requestVerdict()` |
| No response within 15s | `AbortSignal.timeout` → `TimeoutError` → `MSG_TIMEOUT`. `finally` re-enables the controls | `requestVerdict()`, `onSubmit()` |
| Mode switched after a verdict | `applyMode()` → `clearResult()` | `applyMode()` |
| Mode switched mid-request | Not possible: the whole fieldset is disabled (D3) | `setBusy()` |
| Double submit | Not possible: the button is disabled while busy (D3) | `setBusy()` |

## 7. File Layout

**`static/index.html`**
1. `<!doctype html>`, `<html lang="en">`.
2. `<head>`:
   - `<meta charset="utf-8">`
   - `<meta name="viewport" content="width=device-width, initial-scale=1">` (criterion 11)
   - `<title>Decision Game</title>`
   - `<link rel="stylesheet" href="style.css">`
   - `<script src="app.js" defer></script>`
3. `<main>` containing:
   - `<h1>Decision Game</h1>`
   - `<form id="verdict-form">` containing `<fieldset id="controls">`, which holds:
     - the mode `<fieldset>` with `<legend>Mode</legend>` and 2 radios (each wrapped in a `<label>`)
     - the scenario label and textarea
     - the question label and input
     - the submit button
   - `<section id="result" aria-live="polite">`
4. `<footer>For fun — not advice.</footer>`.

**`static/app.js`**
1. Constants (§3).
2. DOM lookups.
3. Functions, in this order: `clearResult`, `applyMode`, `setBusy`, `showVerdict`, `showError`,
   `requestVerdict`, `onSubmit`.
4. Event wiring:
   - `form` submit
   - each radio's `change`
   - the initial `applyMode` call

**`static/style.css`**
1. `:root` colour and spacing tokens. Positive and negative colours must meet 4.5:1 contrast
   against the card background.
2. Base: `box-sizing: border-box`, the body font, `main` capped at about 560px, centred, with a
   16px side gutter.
3. Form: full-width textarea and input, visible labels.
4. Mode toggle: the radios are visually hidden but focusable. `input:focus-visible + span` draws
   the outline, and `:checked + span` draws the selected state.
5. Button, including its `:disabled` style.
6. Result card, the `.positive`/`.negative` modifiers, the bar, and `.error`.
7. Footer.

## 8. Dependencies
- **Nothing new in `requirements.txt`.** `fastapi.staticfiles.StaticFiles` ships with fastapi
  (through Starlette).
- **New imports in `main.py`:** `from pathlib import Path` and
  `from fastapi.staticfiles import StaticFiles`.
- **`StaticFiles` checks the directory at construction.** If `static/` is missing, `import main`
  raises. So `static/` has to exist before the mount is added, and before `check_proxy.py` runs.
- **Build order:**
  1. The `static/` files.
  2. The mount in `main.py`.
  3. The additions to `check_proxy.py`, then run it.
  4. `CLAUDE.md`.
  5. The browser checks.
- **`app.js` depends on the DOM IDs in §3.** `check_proxy.py` asserts the key IDs, which catches
  a renamed ID early.

## 9. Hard Boundaries
- [ ] Nothing in `static/` contains `sk-`, an absolute `http://` or `https://` URL, `innerHTML`,
      `outerHTML`, `insertAdjacentHTML`, `localStorage`, or `sessionStorage`.
- [ ] `app.js` makes no request except `POST` to `API_PATH`.
- [ ] No external script, stylesheet or font. Everything is served from `static/`.
- [ ] The mount stays the last route registration in `main.py`, after `@app.post("/api/verdict")`.
- [ ] No change to the `/api/verdict` handler, the cap, or the error body contract.
- [ ] The verdict is never shown by colour alone.

## 10. Acceptance Criteria (runnable)

**Gate and grep checks:**

| # | Command | Pass |
|---|---|---|
| 1, 2, 3 | `venv/Scripts/python check_proxy.py` | Prints `OK`. The new checks are:<br>• `GET /` → 200, `text/html`, and the body contains `id="scenario"`, `id="question"`, `name="mode"` and `Get verdict`<br>• `GET /app.js` and `GET /style.css` → 200<br>• every existing `POST /api/verdict` case still passes with the mount in place |
| 10 | `grep -rcE "sk-\|https?://\|innerHTML\|outerHTML\|insertAdjacentHTML\|localStorage\|sessionStorage" static/` | Every file reports `0`. `check_proxy.py` also asserts `sk-` and `http` are absent |

**Real browser** (Claude in Chrome, against `venv/Scripts/python -m uvicorn main:app --port 8000`
opened at `http://localhost:8000/`):

| # | Steps | Pass |
|---|---|---|
| 4 | Advisor mode: type the example scenario and question, submit | The card shows "Go for it" or "Not go for it" and "NN% sure". The bar-fill width is NN%. NN = round(`confidence` × 100) from the `/api/verdict` response in the network log |
| 5 | Pick Judge, then check the label and submit a rent-split example | Label reads "Your position". The card shows "You are right" or "You are wrong" |
| 6 | Use `javascript_tool` to wrap `window.fetch` so it waits 3s, then submit | While waiting, `#controls` is disabled and the button reads "Thinking…". Afterwards both are back to normal |
| 7 | Clear the scenario, then submit | The network log shows no new `/api/verdict` request |
| 8 | Use `javascript_tool` to make `window.fetch` return `new Response('{"error":"Out of juice for today — try tomorrow."}', {status: 429})`, then submit | `#result` text is exactly "Out of juice for today — try tomorrow." |
| 9 | Stop uvicorn, then submit | `#result` reads "Can't reach the server — check your connection." |
| 11 | `resize_window` to 375 wide | `document.documentElement.scrollWidth <= clientWidth` is true, and every control is visible |
| 12 | Using the keyboard only: Tab to the mode (arrow to Judge), the scenario, the question and the button, then press Enter | A verdict appears. `#result` has `aria-live="polite"` |

**Token cost:** criteria 4, 5 and 12 each make one real Jev call, about 400 tokens each and 1.2k
tokens in total. Criteria 6 and 8 fake the network response, and 7 and 9 never reach Jev.
