# Plan: Jev Smoke Test + Verdict Proxy
**Spec:** `02_jev_proxy.md` | **Status:** Built, in review

## 1. Files
| Action | File | Reason |
|---|---|---|
| CREATE | `smoke_test.py` | Spec §4, criterion 1: one raw Jev call that confirms the real response shape before the proxy depends on it |
| CREATE | `main.py` | Spec §4: FastAPI app with `POST /api/verdict` |
| CREATE | `check_proxy.py` | Spec criteria 4, 6, 7: offline check with Jev mocked. No network, no tokens spent |
| MODIFY | `.claude/devsystem.json` | Adds `gate.commands: ["venv/Scripts/python check_proxy.py"]` so `/ship` runs the check |
| MODIFY | `CLAUDE.md` | The Commands section currently says "`scenarios.py` is the only check". Add `check_proxy.py` and `smoke_test.py` |
| — | `requirements.txt` | Already has `fastapi`, `uvicorn`, `httpx`, `python-dotenv`. No change |
| — | `.env` | Already holds `JEVMODEL_API_KEY`. Read only |

## 2. Architecture Decisions

**D1: Validate with Pydantic constraints, and map validation errors to 400.**
- The spec requires 400 for:
  - empty or whitespace-only input
  - over-length input
  - an unknown mode
- `VerdictRequest` uses these field types:
  - `Literal["advisor", "judge"]` for `mode`.
  - `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=N)]` for
    `scenario` and `question`.
- FastAPI returns 422 on its own. One `RequestValidationError` handler changes that to 400,
  with body `{"error": "<field>: <msg>"}`.
- This covers malformed and missing-field bodies too.
- Rejected: hand-written checks inside the handler. They duplicate what Pydantic already does and
  add more code.

**D2: Uniform `{"error": "..."}` body.**
- Background: `HTTPException(detail=...)` serializes as `{"detail": ...}`, which breaks the proxy
  contract in `project_context.md`.
- Decision: one `HTTPException` exception handler returns
  `JSONResponse(status_code=exc.status_code, content={"error": exc.detail})`, where `detail` is
  always a plain string.
- Rejected: returning `JSONResponse` by hand at every error site. That spreads the same body shape
  across 7 call sites.

**D3: Cap state lives in memory, in a module-level dict.**
- The spec wants a single-process daily counter plus the last token balance seen.
- A database or a file is not needed. Nothing requires the cap to survive a restart.
- Mark it in the source as `# chisle: in-memory cap resets on restart; fine for a single-instance demo`.
- Rejected: persisting the cap to disk or a database.

**D4: No static mount yet.**
- The frontend is milestone 5, and `static/` doesn't exist.
- `StaticFiles(directory="static")` raises at startup if the directory is missing.
- Milestone 5 adds the mount.

**D5: Retry once on Jev 429/502, after a fixed 1s `asyncio.sleep`.**
- This is exactly what the spec §4 asks for.
- Rejected: a retry library such as `tenacity`. It adds a dependency for a single sleep call.

**D6: `confidence` comes from `probabilities[choice]`.**
- CLAUDE.md says confidence is read from `probabilities`. That value is the probability of the
  label actually chosen.
- The top-level `confidence` field is UNVERIFIED (see `project_context.md`).
- **Build gate:** run `smoke_test.py` first.
  - If `probabilities` is missing, or its meaning differs from what we assumed, update D6 before
    writing `main.py`.
  - Log whatever changes with `/log_decision`.

**D7: A `choice` → label dict per mode (`MODE_CONFIG[mode]["labels"]`).**
- It is a direct lookup with no branching.

## 3. Data Structures

**Module constants**

| Constant | Value | Notes |
|---|---|---|
| `JEV_URL` | `"https://jevmodel.org/v1/systemone"` | |
| `JEV_MODEL` | `"jev-latest"` | |
| `API_KEY` | `os.environ["JEVMODEL_API_KEY"]` | A missing key raises `KeyError` at import. Fail fast |
| `TOKEN_FLOOR` | `5000` | Spec §4 default |
| `DAILY_LIMIT` | `40` | Spec §4 default |
| `RETRY_DELAY_S` | `1` | |
| `MAX_SCENARIO_LEN` | `1500` | Matches the `project_context.md` UI sketch; well under Jev's 8,000-char `state` limit |
| `MAX_QUESTION_LEN` | `300` | Same reasoning as `MAX_SCENARIO_LEN` |

**`MODE_CONFIG: dict[str, dict]`**

```
"advisor": {
  "instructions": <Advisor text from project_context.md>,
  "criteria": {"go_for_it": str, "not_go_for_it": str},
  "labels":   {"go_for_it": "Go for it", "not_go_for_it": "Not go for it"},
},
"judge": {
  "instructions": <Judge text from project_context.md>,
  "criteria": {"you_are_right": str, "you_are_wrong": str},
  "labels":   {"you_are_right": "You are right", "you_are_wrong": "You are wrong"},
}
```

The `Literal` values in `VerdictRequest.mode` must match these keys exactly.

**`VerdictRequest(BaseModel)`**

| Field | Type | Enforces |
|---|---|---|
| `mode` | `Literal["advisor", "judge"]` | "Unknown mode" → 400 (via D1) |
| `scenario` | `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_SCENARIO_LEN)]` | "Empty / too long" → 400 |
| `question` | Same as `scenario`, with `MAX_QUESTION_LEN` | Same |

**`VerdictResponse(BaseModel)`**: `verdict: str` and `confidence: float`.

**`_cap_state: dict`**

| Key | Type | Enforces |
|---|---|---|
| `date` | UTC `date`, initialized to `datetime.now(timezone.utc).date()` | Reset at UTC midnight (spec §4) |
| `count` | `int`, starts at 0 | `DAILY_LIMIT` |
| `tokens_remaining` | `int` or `None` | `TOKEN_FLOOR`. `None` means unknown, so the floor doesn't block yet |

## 4. Function Specifications

**`_utc_today() -> date`**
- Returns `datetime.now(timezone.utc).date()`.
- It is a separate function so `check_proxy.py` can patch the clock.

**`_check_cap() -> None`**
1. If `_cap_state["date"] != _utc_today()`, set `date` to today and `count` to 0.
2. Raise `HTTPException(429, "Out of juice for today — try tomorrow.")` if either is true:
   - `count >= DAILY_LIMIT`
   - `tokens_remaining is not None` and `tokens_remaining < TOKEN_FLOOR`

**`_record_usage(tokens_remaining: int | None) -> None`**
- Adds 1 to `count`.
- If `tokens_remaining` is not `None`, stores it.

**`_build_jev_payload(mode: str, scenario: str, question: str) -> dict`**
- Returns this dict:
  ```
  {"model": JEV_MODEL,
   "state": {"scenario": scenario, "question": question},
   "questions": {"verdict": {"type": "choice",
                             "instructions": MODE_CONFIG[mode]["instructions"],
                             "criteria": MODE_CONFIG[mode]["criteria"]}}}
  ```
- Never raises. `mode` has already been validated by D1.

**`async def _call_jev(payload: dict) -> httpx.Response`**
- Uses `httpx.AsyncClient` with its default 5s timeout.
- Sends `POST JEV_URL` with the headers `Authorization: Bearer {API_KEY}` and `Content-Type: application/json`.
- If the status is 429 or 502, it sleeps `RETRY_DELAY_S` and makes one more attempt.
- It raises `HTTPException(502, "Jev unavailable, try again")` in two cases:
  - the second attempt is also 429 or 502
  - `httpx.RequestError` is raised on either attempt, including timeouts
- Otherwise it returns the response whatever the status. The caller handles 401, 402 and 422,
  because those are not retryable.

**`_parse_jev_response(body: dict, mode: str) -> tuple[str, float]`**
- Reads `choice = body["answers"]["verdict"]["choice"]` and
  `p = body["answers"]["verdict"]["probabilities"][choice]`.
- Returns `(MODE_CONFIG[mode]["labels"][choice], float(p))`.
- Raises `HTTPException(502, "Unexpected response from Jev")` in any of these cases:
  - a `KeyError` or `TypeError` while reading the body
  - `choice` is not one of the mode's labels

**`async def verdict(req: VerdictRequest) -> VerdictResponse`**
- Route: `POST /api/verdict`.
- Orchestrates the steps in §5.

**Exception handlers** (both registered on `app`):
- `http_exception_handler(request, exc: HTTPException)` returns `JSONResponse(exc.status_code, {"error": exc.detail})`.
- `validation_exception_handler(request, exc: RequestValidationError)` takes `err = exc.errors()[0]`
  and returns `JSONResponse(400, {"error": f"{err['loc'][-1]}: {err['msg']}"})`.

## 5. Logic Flow: `POST /api/verdict`

0. FastAPI and Pydantic parse the body.
   - If it is invalid, FastAPI raises `RequestValidationError`, the handler returns 400, and no Jev call is made.
1. `_check_cap()`.
   - If the cap is exceeded, return 429 and make no Jev call.
2. `payload = _build_jev_payload(req.mode, req.scenario, req.question)`.
   - The strings are already stripped, by `strip_whitespace`.
3. `resp = await _call_jev(payload)`.
   - This may raise 502.
4. If the status is 401:
   - Log `"Jev auth failed (401)"`. Never log the key or the user's text.
   - Raise `HTTPException(500, "Server misconfiguration")`.
5. If the status is 402, raise `HTTPException(429, "Out of juice for today — try tomorrow.")`.
6. If the status is 422:
   - Log `"Jev rejected payload (422)"`.
   - Raise `HTTPException(500, "Server misconfiguration")`.
7. If the status is any other non-2xx, raise `HTTPException(502, "Jev unavailable, try again")`.
8. `_record_usage(int(h) if (h := resp.headers.get("X-Tokens-Remaining", "")).isdigit() else None)`.
9. `label, confidence = _parse_jev_response(resp.json(), req.mode)`.
   - This may raise 502.
   - If `resp.json()` itself fails (the body is not JSON), catch `ValueError` and raise 502.
10. Return `VerdictResponse(verdict=label, confidence=confidence)`.

## 6. Edge Case Implementation Map
| Spec edge case | Mechanism | Location |
|---|---|---|
| Empty or whitespace-only scenario or question | `StringConstraints(strip_whitespace=True, min_length=1)` → 400 | `VerdictRequest` + `validation_exception_handler` |
| Too long | `StringConstraints(max_length=...)` → 400 | Same |
| Unknown mode | `Literal[...]` → 400 | Same |
| Cap exceeded | `_check_cap()` raises 429 before any Jev call | `verdict()` step 1 |
| Jev 401 | Status branch, 500, generic message | `verdict()` step 4 |
| Jev 402 | Status branch, same 429 as the cap | `verdict()` step 5 |
| Jev 422 | Status branch, 500, generic message | `verdict()` step 6 |
| Jev 429/502 | One retry, then 502 | `_call_jev()` |
| Missing fields in the Jev response | `KeyError`/`TypeError` → 502 | `_parse_jev_response()` |
| Response body is not JSON | `ValueError` → 502 | `verdict()` step 9 |

## 7. File Layout

**`main.py`**
1. Imports:
   - stdlib: `os`, `asyncio`, `logging`, `datetime` (`date`, `datetime`, `timezone`), `typing` (`Annotated`, `Literal`)
   - `fastapi`: `FastAPI`, `HTTPException`, `Request`, `RequestValidationError`, `JSONResponse`
   - `pydantic`: `BaseModel`, `StringConstraints`
   - `httpx`
   - `dotenv.load_dotenv`
2. `load_dotenv()`, then the constants.
3. `MODE_CONFIG`.
4. `VerdictRequest`, `VerdictResponse`.
5. `_cap_state`, `_utc_today`, `_check_cap`, `_record_usage`.
6. `_build_jev_payload`, `_call_jev`, `_parse_jev_response`.
7. `app = FastAPI()` and the two exception handlers.
8. `@app.post("/api/verdict")` → `verdict()`.

**`smoke_test.py`**

It stands alone and does not import `main`, so it can run before `main.py` exists.
1. Imports: `os`, `json`, `httpx`, `load_dotenv`.
2. Loads the key and hardcodes one Advisor payload, in the same shape as §4.
3. Sends the POST, then prints the status code, the `X-Tokens-Remaining` header and the
   pretty-printed body.
4. Prints `confidence` next to `probabilities[choice]` so the relationship is visible (D6).
5. Exits 1 on a non-2xx response.

**`check_proxy.py`**

It is offline and needs no framework: plain `assert` statements plus `fastapi.testclient.TestClient`
and `unittest.mock`.
1. Sets a dummy `JEVMODEL_API_KEY` in `os.environ` before `import main`, so no real key is
   needed or spent.
2. A helper builds fake `httpx.Response` objects. It attaches `request=` so that `.json()` works.
3. Cases, each of which resets `main._cap_state` first:
   - The input is invalid (empty scenario, bad mode, or too long) → 400 with an `error` key. Jev
     is never called: the patched `post` asserts it is not called.
   - The cap is full → 429, and Jev is not called.
   - Jev answers 200 → 200 with the correct label and `confidence == probabilities[choice]`.
   - Jev answers 429, then 200 → 200, and `post` is called 2 times.
   - Jev answers 429 twice → 502, and `post` is called 2 times.
   - Jev answers 401 → 500, and the response contains no dummy key.
   - Jev answers 402 → 429.
4. `asyncio.sleep` is patched to a no-op, so the check runs instantly.
5. Prints `OK` and exits 0 when all cases pass. Any failure raises `AssertionError` with a non-zero exit.

## 8. Dependencies
- All packages are already in `requirements.txt`.
  - `fastapi.testclient` needs `httpx`, which is present.
  - `StringConstraints` needs pydantic v2. Current `fastapi` pulls in v2.
- `.env` (milestone 1) is used by `main.py` and `smoke_test.py`. `check_proxy.py` does not use it.
- Build order:
  1. `smoke_test.py`, then run it. This is the D6 gate.
  2. `main.py`
  3. `check_proxy.py`
  4. The gate config and the CLAUDE.md update.
- No conflicts with existing code. All three `.py` files are new.
- `venv` has no packages installed yet, so run `pip install -r requirements.txt` first.

## 9. Hard Boundaries
- [x] The API key never appears in any response body, response header or log line. Only the
      `Authorization` header sent to Jev carries it.
- [x] Never log the user's scenario or question text. Log lines name only the Jev status.
- [x] No `static/` mount (D4).
- [x] `_call_jev()` is never reached before `_check_cap()` passes.
- [x] At most one retry.
- [x] A Jev error body is never forwarded to the client. The client gets only a generic message.
- [x] `check_proxy.py` never hits the network and never uses the real key. It does read `.env`, because `import main` calls `load_dotenv()`, but the dummy key is set first and `load_dotenv` does not override existing variables.
- [x] `smoke_test.py` never writes its output to a file.

## 10. Acceptance Criteria (runnable)

Setup: `venv/Scripts/python -m pip install -r requirements.txt`

| # | Command | Pass |
|---|---|---|
| 1 | `venv/Scripts/python smoke_test.py` | Exit 0. Output shows `answers.verdict.choice`, `probabilities`, `confidence`. D6 is confirmed or updated |
| 2 | Start the server: `venv/Scripts/python -m uvicorn main:app --port 8000` (in the background). Then: `curl -s -X POST localhost:8000/api/verdict -H "Content-Type: application/json" -d '{"mode":"advisor","scenario":"Two job offers, one pays more but is less stable.","question":"Should I take the higher-paying one?"}'` | `{"verdict":"Go for it"\|"Not go for it","confidence":<0..1>}` |
| 3 | Same as 2, with `"mode":"judge"` and a question that states a position | `"verdict"` is `"You are right"` or `"You are wrong"` |
| 4 | `curl -s -w " %{http_code}" -X POST localhost:8000/api/verdict -H "Content-Type: application/json" -d '{"mode":"nonsense","scenario":"x","question":"y"}'` | `{"error":"..."} 400`. The check script also covers empty and too-long input |
| 5 | `grep -c "$(grep JEVMODEL_API_KEY .env \| cut -d= -f2)" main.py smoke_test.py check_proxy.py` and `curl -si ... \| grep -c "sk-"` on the call from 2 | Every count is `0` |
| 6, 7 | `venv/Scripts/python check_proxy.py` | Prints `OK`, exit 0. Covers the cap, the retry, the error mapping and invalid input, all offline |
