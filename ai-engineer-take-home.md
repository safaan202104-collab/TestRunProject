# AI Engineer — Take-Home Project

**Time budget:** 48–72 hours of calendar time (we expect ~14–18 hours of actual work). Quality > completeness — a well-built core beats a sprawling half-done system.

**Self-contained:** Everything you need is in this package — see §0. You provide your laptop, your language/framework of choice, and your own model API key. Do **not** ask us for additional fixtures, schemas, or access to a real CRM — there isn't one to give you, and a strong submission won't need one.

**What we're hiring for:** Someone who can introduce AI capabilities into our CRM end-to-end — prompt design, tool use, evals, latency/cost trade-offs, and production concerns (safety, observability, failure modes). This take-home is a small slice of that work, designed to surface how you think, not just whether you can call an API.

---

## 0. What's in this package

| File | What it is |
|---|---|
| `ai-engineer-take-home.md` | This brief. |
| `fixtures/crm.json` | The mock CRM world: **8 providers, 15 services, 260 patients, ~4,150 appointments** spanning 16 prior weeks plus 3 future weeks. ~1.2 MB. This is the source of truth for your service. |
| `fixtures/eval.jsonl` | **45 labeled eval cases** across 27 categories (happy path, ambiguity, medical, complaint, conflict, prompt injection, VIP, do-not-book, multilingual, multi-intent, etc.). You will add ≥10 more of your own. |
| `tools/generate_fixtures.py` | The deterministic generator that produced `crm.json`. **You don't need to run it.** Provided so you can see how the data was built and (optionally) generate variations for stress-testing. |

The reference clock for every eval case is **`now = 2026-05-18T14:30:00-07:00`** (a Monday afternoon in `America/Los_Angeles`). Treat that as wall-clock — do **not** read your system clock.

---

## 1. Context

MyGlowTheory is a CRM for medical-aesthetic practices. The eventual AI roadmap includes:

- **AI scheduling** — propose & book appointments from natural-language inbox messages (SMS, email, web chat).
- **Performance insights** — let staff ask questions like *"which providers are underbooked next week?"* in plain English.
- **Marketing campaigns** — generate audience segments + draft copy from a single prompt like *"reach lapsed Botox patients with a May promo."*

You're being given **one slice** of the first one. We deliberately scoped this small so you can go deep instead of wide.

---

## 2. The Task — "Inbox → Appointment" AI Assistant

Build a service that ingests an inbound patient message and decides what to do with it. The happy path is: **propose a concrete appointment booking that a human can one-click confirm.** The unhappy paths matter more than the happy path — see §4.

### 2.1 Inputs you'll receive (per request)

This matches the shape used in `fixtures/eval.jsonl`:

```jsonc
{
  "message": {
    "channel": "sms" | "email" | "webchat",
    "from": "+15555550101",                // SMS number, email address, or webchat session id
    "body": "Hi, can I get my lip filler touch-up sometime next Tuesday afternoon? - Sarah"
  },
  "patient_id": "pat_001",                 // null if no match in CRM; your service is responsible
                                           // for looking up the full record in crm.json
  "now": "2026-05-18T14:30:00-07:00"       // wall-clock — do NOT read your system clock
}
```

### 2.2 The CRM "world" you're booking against

`fixtures/crm.json` contains:

- **`providers[]`** (8) — id, name, title, `specialties[]`, weekly `hours` (per-weekday windows like `"tue": ["09:00-17:00"]`; days absent = not working).
- **`services[]`** (15) — id, name, `duration_minutes`, `required_specialty`, `price_usd`. A provider can perform a service only if its `required_specialty` is in their `specialties[]`.
- **`patients[]`** (260) — id, name, phone, email, `last_visit` (nullable), `preferred_provider_id` (nullable), `tags[]` (treatment history hints). Some have `opted_out_marketing`, `do_not_book` (with reason), or `vip` (with `notes`) flags. **Treat these flags as load-bearing.**
- **`appointments[]`** (~4,150) — id, provider_id, patient_id, start, end (ISO 8601 with offset), service_id, status (`booked` | `completed` | `no_show` | `cancelled`). 16 weeks of history + 3 weeks of future. This is what you'll query for availability **and** for the analytics stretch.

Important: do not assume the fixture is small enough to stuff into a prompt. It isn't. Designing how the LLM accesses this data is part of the problem.

You may extend the fixture if you need extra fields — just commit your extensions and note what you added.

### 2.3 Required output

Return a structured decision. Your schema, but it must distinguish at least these outcomes:

| Outcome | When |
|---|---|
| `propose_booking` | You're confident enough to suggest a specific slot. Include provider, service, start time, duration, and a one-sentence rationale shown to staff. |
| `ask_clarification` | The message is ambiguous in a way an LLM shouldn't guess about. Include the question to send back to the patient. |
| `escalate_to_human` | Out-of-scope (complaint, medical question, refund, etc.) or risky. Include a reason. |
| `no_action` | Spam, autoresponder, "thanks!" follow-up, etc. |

**Who reads this output:** a front-desk staff member who one-click confirms, edits, or escalates. Nothing you produce is auto-sent to the patient without a human in the loop. Design your `rationale` / `question` / `reason` strings for that staff reader, not for the patient.

---

## 3. Required deliverables

1. **A runnable service.** HTTP endpoint or CLI — your call. README with one command to start it.
2. **`POST /decide`** (or equivalent) that takes the input in §2.1 and returns your decision schema.
3. **Eval harness.** A script that runs your system against a labeled test set (we're giving you **45 cases** in `fixtures/eval.jsonl` across 27 categories; you must add **at least 10 more of your own**, including adversarial ones we didn't think of). It should print per-case pass/fail, group results by category, and produce an aggregate score. Define what "pass" means — that's part of the assignment, and the `must:` field on each case is a hint, not a spec. Cases like `e08`, `e12`, `e17`, `e19`, `e35`, `e38` deliberately have multiple acceptable outcomes — your scoring logic should reflect that.
4. **Write-up** (`WRITEUP.md`, 1–3 pages) covering:
   - Architecture sketch and why.
   - Prompting / tool-use strategy. Show the actual prompts.
   - Trade-offs you made under the time budget — what you'd build next with another week.
   - Cost & latency estimate per request (back-of-envelope is fine; show the math).
   - Failure modes you're aware of and how you'd detect them in production.

### Stack guidance

- **Language:** Python or TypeScript. Pick what's faster for you.
- **Model provider:** Anthropic (Claude) preferred. OpenAI or any other major provider is fine if you already have credits. A well-designed system shouldn't burn more than a few dollars of API spend over the whole take-home; if you find yourself spending a lot, that itself is a signal worth investigating in your write-up.
- No need to use our actual codebase, framework, or DB. Treat this as a greenfield service.

---

## 4. What we're actually evaluating

In rough order of weight:

1. **Judgment under ambiguity.** Does your system ask when it should ask, escalate when it should escalate, and act when it should act? Confident wrong answers are worse than "I don't know."
2. **Eval thinking.** Did you build a way to *measure* your system, not just demo it? Did you write adversarial cases? Did you measure regressions when you changed the prompt?
3. **Prompt & tool design.** Is the LLM doing what it's good at (language understanding) and is structured code doing what *it's* good at (availability lookup, conflict detection, time math)? Watch out for asking the model to do arithmetic on calendars.
4. **Production-mindedness.** Logging, structured outputs, schema validation, retries, graceful degradation when the model returns garbage, cost/latency awareness.
5. **Communication.** The write-up. We'd rather read "I cut X because Y, and here's how I'd add it back" than discover undocumented missing pieces.

### Things that will impress us

- A real eval loop with regression detection and per-category breakdowns.
- An access pattern for the 4,150-appointment dataset that doesn't stuff everything into context every request.
- Catching at least one case where the model would hallucinate a slot that isn't actually available.
- Distinguishing "ambiguous date" (next Tuesday → which Tuesday?) from "ambiguous service" (touch-up of what?).
- Respecting `do_not_book` / `vip` / `opted_out_marketing` flags correctly — these have different consequences.
- Acknowledging the safety bar: this is healthcare-adjacent. Don't book medical consults. Don't answer medical questions.
- A clean, opinionated decision schema. Less is more.

### Things that will *not* impress us

- A 12-step LangChain agent that takes 40 seconds to respond.
- A perfect demo with no eval harness.
- Using GPT/Claude to do timezone arithmetic instead of your language's date library.
- "I would have added tests if I had more time." Add three tests instead of saying this.

---

## 5. Stretch goals (optional, only if core is solid)

Pick **at most one**. We genuinely mean it — a polished core with one stretch is stronger than a rushed pass at all three. Stretch goals are bonus only; they do not compensate for a weak core.

- **(A) Conversational follow-up.** After `ask_clarification`, accept the patient's reply and converge on a booking. Show how you maintain state without re-paying for the whole context every turn.
- **(B) Analytics question-answering.** A second endpoint `POST /ask` that answers a question like *"who hasn't been in for >90 days and is due for filler?"* against the same fixture. Show how you'd keep the LLM from inventing numbers.
- **(C) Campaign draft.** Given a one-line prompt (*"May promo for lapsed Botox patients"*), produce a segment (patient IDs from the fixture) and a draft SMS. Show how you'd prevent it from blasting opted-out patients.

---

## 6. Constraints & rules

- **No real PHI.** Use only the fixtures we provide or synthetic data you generate. If you accidentally use anything that looks like real patient data, we have to throw the submission out. (Everything in `crm.json` is fictional and was generated deterministically — see `tools/generate_fixtures.py`.)
- **No vendor lock-in to magic.** If you use a framework (LangGraph, LlamaIndex, Vercel AI SDK), we still want to see your prompts and your decision logic. Don't hide behind abstractions.
- **Use of AI tooling is encouraged.** Cursor, Claude Code, Copilot — all fine, expected even. We care about the output and your ability to defend every decision in it.
- **Cite your sources.** If you copied a prompt pattern from a blog post or paper, drop a link in the write-up. That's a plus, not a minus.

---

## 7. Submission

- Push to a private GitHub repo and add `@<reviewer-github>` as a collaborator.
- README must include:
  - Setup (one command ideal).
  - How to run the eval harness.
  - Estimated time you actually spent.
- Reply to the email thread with the repo link when ready.

We'll review within 3 business days and follow up either way. The next round is a 60-minute walkthrough where you'll demo the system, we'll throw two new test cases at it live, and we'll talk about how you'd extend this toward the broader roadmap in §1.

---

## 8. Questions

Email `<hiring-contact>` — questions are welcome and won't count against you. We'd rather you ask than guess wrong about scope.

Good luck. We're excited to see how you think.
