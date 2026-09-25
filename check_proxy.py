"""Offline check for main.py: Jev is mocked, so no network and no tokens. Prints OK or raises."""
import os

DUMMY_KEY = "sk-dummy-check-proxy-key"
os.environ["JEVMODEL_API_KEY"] = DUMMY_KEY  # before import main; overrides any real key from .env

from unittest.mock import AsyncMock, patch  # noqa: E402

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

client = TestClient(main.app)
ADVISOR = {"mode": "advisor", "scenario": "Two offers, one pays more.", "question": "Take it?"}
OK_BODY = {"answers": {"verdict": {"type": "choice", "choice": "go_for_it", "confidence": 0.58,
                                   "probabilities": {"go_for_it": 0.79, "not_go_for_it": 0.21}}}}


def jev(status, body=None, remaining="90000"):
    return httpx.Response(status, json=body or {}, headers={"X-Tokens-Remaining": remaining},
                          request=httpx.Request("POST", main.JEV_URL))


def call(body, jev_responses):
    main._cap_state.update(date=main._utc_today(), count=0, tokens_remaining=None)
    post = AsyncMock(side_effect=jev_responses)
    with patch.object(httpx.AsyncClient, "post", post), patch.object(main.asyncio, "sleep", AsyncMock()):
        return client.post("/api/verdict", json=body), post


# Invalid input -> 400 with an "error" key, Jev never called.
for bad in ({**ADVISOR, "scenario": "   "}, {**ADVISOR, "mode": "nonsense"},
            {**ADVISOR, "question": "x" * (main.MAX_QUESTION_LEN + 1)}, {"mode": "advisor"}):
    r, post = call(bad, [])
    assert r.status_code == 400 and "error" in r.json(), (bad, r.status_code, r.text)
    assert post.call_count == 0

# Happy path: label mapped, confidence = probabilities[choice] (not the top-level `confidence`).
r, post = call(ADVISOR, [jev(200, OK_BODY)])
assert r.status_code == 200 and r.json() == {"verdict": "Go for it", "confidence": 0.79}, r.text
assert main._cap_state["count"] == 1 and main._cap_state["tokens_remaining"] == 90000

# Judge mode labels.
judge_body = {"answers": {"verdict": {"choice": "you_are_wrong",
                                      "probabilities": {"you_are_right": 0.3, "you_are_wrong": 0.7}}}}
r, _ = call({**ADVISOR, "mode": "judge"}, [jev(200, judge_body)])
assert r.json() == {"verdict": "You are wrong", "confidence": 0.7}, r.text

# Daily cap full -> 429, Jev never called.
main._cap_state.update(count=main.DAILY_LIMIT)
post = AsyncMock()
with patch.object(httpx.AsyncClient, "post", post):
    r = client.post("/api/verdict", json=ADVISOR)
assert r.status_code == 429 and r.json() == {"error": main.OUT_OF_JUICE}, r.text
assert post.call_count == 0

# Token floor -> 429, Jev never called.
main._cap_state.update(count=0, tokens_remaining=main.TOKEN_FLOOR - 1)
with patch.object(httpx.AsyncClient, "post", post):
    r = client.post("/api/verdict", json=ADVISOR)
assert r.status_code == 429 and post.call_count == 0, r.text

# Retry: 429 then 200 -> 200 after exactly 2 calls.
r, post = call(ADVISOR, [jev(429), jev(200, OK_BODY)])
assert r.status_code == 200 and post.call_count == 2, r.text

# Retry exhausted: 429 twice -> 502, no third call.
r, post = call(ADVISOR, [jev(429), jev(502)])
assert r.status_code == 502 and post.call_count == 2, r.text

# Network error -> 502.
r, _ = call(ADVISOR, [httpx.ConnectError("down")])
assert r.status_code == 502, r.text

# Jev 401 -> 500, generic message, key never leaks.
r, _ = call(ADVISOR, [jev(401, {"error": {"type": "authentication_error", "message": DUMMY_KEY}})])
assert r.status_code == 500 and DUMMY_KEY not in r.text and DUMMY_KEY not in str(r.headers), r.text

# Jev 402 -> treated as out of juice.
r, _ = call(ADVISOR, [jev(402)])
assert r.status_code == 429 and r.json() == {"error": main.OUT_OF_JUICE}, r.text

# Jev 422 -> 500.
r, _ = call(ADVISOR, [jev(422)])
assert r.status_code == 500, r.text

# Malformed Jev body -> 502.
r, _ = call(ADVISOR, [jev(200, {"answers": {}})])
assert r.status_code == 502, r.text

# Key is sent to Jev, and only there.
r, post = call(ADVISOR, [jev(200, OK_BODY)])
assert post.call_args.kwargs["headers"]["Authorization"] == f"Bearer {DUMMY_KEY}"
assert DUMMY_KEY not in r.text

print("OK")
