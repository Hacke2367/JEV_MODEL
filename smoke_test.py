"""One raw Jev call: confirms the real response shape before main.py depends on it."""
import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

JEV_URL = "https://jevmodel.org/v1/systemone"

payload = {
    "model": "jev-latest",
    "state": {
        "scenario": "I have two job offers. A startup pays 20% more but could fold within a year. "
                    "My current company is stable but I've stopped learning there.",
        "question": "Should I join the startup?",
    },
    "questions": {
        "verdict": {
            "type": "choice",
            "instructions": "The user describes a situation and asks whether to do something. "
                            "Decide if doing it is the better choice.",
            "criteria": {
                "go_for_it": "Doing it is the better decision given the scenario.",
                "not_go_for_it": "Not doing it is the better decision given the scenario.",
            },
        }
    },
}

resp = httpx.post(
    JEV_URL,
    json=payload,
    headers={"Authorization": f"Bearer {os.environ['JEVMODEL_API_KEY']}"},
    timeout=15,
)
print("status:", resp.status_code)
print("X-Tokens-Remaining:", resp.headers.get("X-Tokens-Remaining"))
body = resp.json()
print(json.dumps(body, indent=2))

if not resp.is_success:
    sys.exit(1)

verdict = body["answers"]["verdict"]
choice = verdict.get("choice")
print(f"\nconfidence={verdict.get('confidence')}  probabilities[{choice}]={verdict.get('probabilities', {}).get(choice)}")
