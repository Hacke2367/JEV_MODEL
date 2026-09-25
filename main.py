"""Decision Game backend: proxies POST /api/verdict to Jev so the API key never reaches the browser."""
import asyncio
import logging
import os
from datetime import date, datetime, timezone
from typing import Annotated, Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StringConstraints

load_dotenv()

JEV_URL = "https://jevmodel.org/v1/systemone"
JEV_MODEL = "jev-latest"
API_KEY = os.environ["JEVMODEL_API_KEY"]
TOKEN_FLOOR = 5000
DAILY_LIMIT = 40
RETRY_DELAY_S = 1
MAX_SCENARIO_LEN = 1500
MAX_QUESTION_LEN = 300
OUT_OF_JUICE = "Out of juice for today — try tomorrow."
JEV_UNAVAILABLE = "Jev unavailable, try again"
MISCONFIGURED = "Server misconfiguration"

log = logging.getLogger("decision_game")

MODE_CONFIG = {
    "advisor": {
        "instructions": "The user describes a situation and asks whether to do something. "
                        "Decide if doing it is the better choice.",
        "criteria": {
            "go_for_it": "Doing it is the better decision given the scenario.",
            "not_go_for_it": "Not doing it is the better decision given the scenario.",
        },
        "labels": {"go_for_it": "Go for it", "not_go_for_it": "Not go for it"},
    },
    "judge": {
        "instructions": "The user describes a situation and states their position. "
                        "Decide if their position is correct.",
        "criteria": {
            "you_are_right": "The user's position is correct given the scenario.",
            "you_are_wrong": "The user's position is incorrect given the scenario.",
        },
        "labels": {"you_are_right": "You are right", "you_are_wrong": "You are wrong"},
    },
}


class VerdictRequest(BaseModel):
    mode: Literal["advisor", "judge"]
    scenario: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_SCENARIO_LEN)]
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION_LEN)]


class VerdictResponse(BaseModel):
    verdict: str
    confidence: float


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


# chisle: in-memory cap resets on restart; fine for a single-instance demo.
_cap_state = {"date": _utc_today(), "count": 0, "tokens_remaining": None}


def _check_cap() -> None:
    today = _utc_today()
    if _cap_state["date"] != today:
        _cap_state["date"] = today
        _cap_state["count"] = 0
    tokens = _cap_state["tokens_remaining"]
    if _cap_state["count"] >= DAILY_LIMIT or (tokens is not None and tokens < TOKEN_FLOOR):
        raise HTTPException(429, OUT_OF_JUICE)


def _record_usage(tokens_remaining: int | None) -> None:
    _cap_state["count"] += 1
    if tokens_remaining is not None:
        _cap_state["tokens_remaining"] = tokens_remaining


def _build_jev_payload(mode: str, scenario: str, question: str) -> dict:
    return {
        "model": JEV_MODEL,
        "state": {"scenario": scenario, "question": question},
        "questions": {
            "verdict": {
                "type": "choice",
                "instructions": MODE_CONFIG[mode]["instructions"],
                "criteria": MODE_CONFIG[mode]["criteria"],
            }
        },
    }


async def _call_jev(payload: dict) -> httpx.Response:
    headers = {"Authorization": f"Bearer {API_KEY}"}
    async with httpx.AsyncClient() as client:
        for attempt in range(2):
            try:
                resp = await client.post(JEV_URL, json=payload, headers=headers)
            except httpx.RequestError:
                raise HTTPException(502, JEV_UNAVAILABLE)
            if resp.status_code not in (429, 502):
                return resp
            if attempt == 0:
                await asyncio.sleep(RETRY_DELAY_S)
    raise HTTPException(502, JEV_UNAVAILABLE)


def _parse_jev_response(body: dict, mode: str) -> tuple[str, float]:
    try:
        answer = body["answers"]["verdict"]
        choice = answer["choice"]
        label = MODE_CONFIG[mode]["labels"][choice]
        # probabilities[choice], not `confidence`: the latter is the top-two margin (smoke test, D6).
        return label, float(answer["probabilities"][choice])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(502, "Unexpected response from Jev")


app = FastAPI()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    err = exc.errors()[0]
    return JSONResponse(status_code=400, content={"error": f"{err['loc'][-1]}: {err['msg']}"})


@app.post("/api/verdict")
async def verdict(req: VerdictRequest) -> VerdictResponse:
    _check_cap()
    resp = await _call_jev(_build_jev_payload(req.mode, req.scenario, req.question))
    if resp.status_code == 401:
        log.error("Jev auth failed (401)")
        raise HTTPException(500, MISCONFIGURED)
    if resp.status_code == 402:
        raise HTTPException(429, OUT_OF_JUICE)
    if resp.status_code == 422:
        log.error("Jev rejected payload (422)")
        raise HTTPException(500, MISCONFIGURED)
    if not resp.is_success:
        raise HTTPException(502, JEV_UNAVAILABLE)
    remaining = resp.headers.get("X-Tokens-Remaining", "")
    _record_usage(int(remaining) if remaining.isdigit() else None)
    try:
        body = resp.json()
    except ValueError:
        raise HTTPException(502, "Unexpected response from Jev")
    label, confidence = _parse_jev_response(body, req.mode)
    return VerdictResponse(verdict=label, confidence=confidence)
