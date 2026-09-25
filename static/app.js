"use strict";

const API_PATH = "/api/verdict";
const TIMEOUT_MS = 15000;
const MSG_GENERIC = "Something went wrong — try again.";
const MSG_NETWORK = "Can't reach the server — check your connection.";
const MSG_TIMEOUT = "Took too long — try again.";
const POSITIVE = new Set(["Go for it", "You are right"]);
const MODES = {
  advisor: {
    questionLabel: "Your question",
    scenarioPlaceholder: "I have two job offers. A startup pays 20% more but could fold within a year. My current job is stable, but I've stopped learning there.",
    questionPlaceholder: "Should I take the startup job?",
  },
  judge: {
    questionLabel: "Your position",
    scenarioPlaceholder: "My roommate and I split rent 50/50. I have the bigger bedroom with a private bathroom.",
    questionPlaceholder: "Am I right that rent should stay 50/50?",
  },
};

const form = document.getElementById("verdict-form");
const controls = document.getElementById("controls");
const scenario = document.getElementById("scenario");
const question = document.getElementById("question");
const questionLabel = document.getElementById("question-label");
const submit = document.getElementById("submit");
const result = document.getElementById("result");

function clearResult() {
  result.replaceChildren();
}

function applyMode(mode) {
  const m = MODES[mode];
  questionLabel.textContent = m.questionLabel;
  scenario.placeholder = m.scenarioPlaceholder;
  question.placeholder = m.questionPlaceholder;
  clearResult();
}

function setBusy(busy) {
  controls.disabled = busy;
  submit.textContent = busy ? "Thinking…" : "Get verdict";
  result.setAttribute("aria-busy", String(busy));
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function showVerdict(verdict, confidence) {
  const pct = Math.round(confidence * 100);
  const card = el("div", `card ${POSITIVE.has(verdict) ? "positive" : "negative"}`);
  const bar = el("div", "bar");
  bar.setAttribute("aria-hidden", "true");
  const fill = el("div", "bar-fill");
  fill.style.width = `${pct}%`;
  bar.append(fill);
  card.append(el("p", "verdict", verdict), el("p", "sure", `${pct}% sure`), bar);
  result.replaceChildren(card);
}

function showError(message) {
  result.replaceChildren(el("p", "error", message));
}

async function requestVerdict(payload) {
  let resp;
  try {
    resp = await fetch(API_PATH, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch (err) {
    const timedOut = err.name === "TimeoutError" || err.name === "AbortError";
    throw new Error(timedOut ? MSG_TIMEOUT : MSG_NETWORK);
  }
  let body;
  try {
    body = await resp.json();
  } catch {
    throw new Error(MSG_GENERIC);
  }
  if (!resp.ok) {
    throw new Error(typeof body?.error === "string" && body.error ? body.error : MSG_GENERIC);
  }
  if (typeof body?.verdict !== "string" || typeof body?.confidence !== "number") {
    throw new Error(MSG_GENERIC);
  }
  return { verdict: body.verdict, confidence: body.confidence };
}

async function onSubmit(event) {
  event.preventDefault();
  // Read before setBusy: FormData skips disabled controls.
  const data = new FormData(form);
  const payload = { mode: data.get("mode"), scenario: data.get("scenario"), question: data.get("question") };
  setBusy(true);
  clearResult();
  try {
    const { verdict, confidence } = await requestVerdict(payload);
    showVerdict(verdict, confidence);
  } catch (err) {
    showError(err.message);
  } finally {
    setBusy(false);
  }
}

form.addEventListener("submit", onSubmit);
for (const radio of form.elements.mode) {
  radio.addEventListener("change", (event) => applyMode(event.target.value));
}
applyMode(form.elements.mode.value);
