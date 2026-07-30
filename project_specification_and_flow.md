# MyGlowTheory Scheduling Assistant: Project Architecture & Flow Specification

This document provides a comprehensive technical overview of the MyGlowTheory "Inbox to Appointment" AI Assistant system. It is designed to be fed directly into an LLM for system architecture, performance, or override telemetry analysis.

---

## 1. Project Philosophy & Design Paradigm
- **Operator-First, AI-Second:** The dashboard is a staff console for a clinic coordinator (not a patient chat interface). The AI acts as a triaging copilot, proposing actions, explanations, and alternative choices, but the coordinator has final one-click approval or inline modification control.
- **Visual Aesthetic:** High-readability dark slate theme inspired by Linear, Stripe, and Apple. Minimalist animations focused on status changes. Typography is styled using the **Inter** font.
- **Granular Branching Engine:** The backend is built as a pipeline of independent modules. This decouples intent routing, entity extraction, calendar logic, and reasoning, permitting early termination of edge cases (spam, complaints) to minimize API latency and token cost.

---

## 2. File & Directory Structure

```text
E:\Test Run\
├── .env                              # Groq API keys and client config
├── requirements.txt                  # Python dependencies
├── eval_harness.py                   # Testing suite running 55 test cases
├── project_specification_and_flow.md # This architecture file
├── walkthrough.md                    # Verification log
├── task.md                           # Task checklist tracker
├── fixtures/
│   ├── crm.json                      # In-memory mock database of providers, patients, & appts
│   ├── eval.jsonl                    # 55 test cases with assertions
│   └── human_overrides.jsonl         # Telemetry log of manual receptionist overrides
├── app/                              # FastAPI Backend Modules
│   ├── main.py                       # FastAPI entry point, wrappers, CORS, and API endpoints
│   ├── client.py                     # Groq LLM client client setup and model fallbacks
│   ├── intent_router.py              # Zero-shot intent classifier & non-scheduling router
│   ├── entity_extractor.py           # Structuring entities (service, provider, date constraints)
│   ├── business_rules.py             # Strict checking logic (specialty check, DNB check, VIP flags)
│   ├── calendar_math.py              # Resolves temporal texts into exact UTC boundaries
│   ├── interval_tree.py              # In-memory interval tree searches for slot gaps
│   ├── slot_ranker.py                # Computes and scores alternative slot candidates
│   ├── rationale_generator.py        # Generates human-explainable notes for the proposed slot
│   └── schema_validator.py           # Pydantic schemas (DecideRequest, DecideResponse, Proposal)
└── frontend/                         # Next.js 15 Client Project
    ├── package.json                  # Next dependencies (React 19, Zustand, Framer Motion)
    ├── tsconfig.json                 # TypeScript rules
    ├── postcss.config.mjs            # PostCSS tailwind configuration
    └── app/
        ├── layout.tsx                # Root layout applying Google Inter font
        ├── globals.css               # Global dark Obsidian variables & theme setup
        └── page.tsx                  # Dashboard Single Page Application (Client Component)
```

---

## 3. Backend Implementation & Execution Flow

### Step-by-Step Backend Pipeline (`/decide` route)
When a request hits `POST /decide`, it executes the following sequential steps inside `app/main.py`:

```
 [Inbound Message JSON]
          │
          ▼
1. Triage Checks (Garbled/Short check) ──► (ask_clarification / exit)
          │
          ▼
2. Resolve Patient (Lookup by phone/email)
          │
          ▼
3. Impersonation/Medical Safety/Complaints Check ──► (escalate_to_human / exit)
          │
          ▼
4. Fast Intent Classification (intent_router.py) ──► NON_SCHEDULING ──► (escalate_to_human / exit)
          │
          ▼ (SCHEDULING)
5. Do-Not-Book Validation (business_rules.py) ──► patient.do_not_book == True ──► (escalate_to_human / exit)
          │
          ▼
6. Entity Extraction (entity_extractor.py) ──► requested_service, provider, time_boundary
          │
          ▼
7. Service Mapping (crm_indexer.py) ──► Synonyms resolved. Fallback to "usual" from history.
          │
          ▼
8. Provider Specialty Verification (business_rules.py) ──► Specialty Mismatch ──► (ask_clarification / exit)
          │
          ▼
9. Time Boundary & Slot Search (calendar_math.py & interval_tree.py)
          │
          ▼
10. Candidates Computation (slot_ranker.py) ──► Rank top slots based on provider utilization
          │
          ▼
11. Rationale Generation (rationale_generator.py) ──► Explains selection to operator
          │
          ▼
12. Telemetry Wrapping & Enrichment (enrich_response in main.py)
```

### Response Object Schema (`DecideResponse`)
The FastAPI endpoint enriches the baseline logic with telemetry and UI metadata:

```json
{
  "outcome": "propose_booking", // propose_booking | ask_clarification | escalate_to_human | no_action
  "booking_proposal": {
    "provider_id": "prov_2",
    "provider_name": "Jordan Patel, RN",
    "service_id": "svc_filler_undereye",
    "service_name": "Under-eye filler",
    "start_time": "2026-05-21T16:30:00-07:00",
    "duration_minutes": 30,
    "price_usd": 600.0,
    "rescheduled_appointment_id": null
  },
  "rationale": "Patient request for under-eye filler with Jordan scheduled...",
  "question": null, // Present on ask_clarification
  "reason": null,    // Present on escalate_to_human
  
  // Extended UI telemetry
  "alternative_proposals": [
    {
      "provider_id": "prov_2",
      "provider_name": "Jordan Patel, RN",
      "start_time": "2026-05-21T15:00:00-07:00",
      "price_usd": 600.0
    }
  ],
  "confidence_score": 0.98,
  "violated_rules": [],
  "decision_stages": ["Receiving", "Understanding", "Checking Patient", "Checking Calendar", "Ranking Slots", "Ready"],
  "metadata": {
    "latency_ms": 124.5,
    "model": "llama-3.3-70b-versatile / llama-3.1-8b-instant",
    "api_provider": "Groq",
    "timestamp": "2026-07-15T02:50:14.517307"
  }
}
```

---

## 4. Frontend Implementation & Tech Stack

### Frameworks & Libraries
- **Framework:** Next.js 15 (App Router, Turbopack, static build targets).
- **Language:** TypeScript (strict interfaces matching Pydantic schemas).
- **Styling:** Tailwind CSS v4.
- **Icons:** `lucide-react` (clean svg icons).

### Three-Column Operator Workspace Layout
1. **Left Feed (Work Queues):**
   - Renders incoming messages streamed directly from `eval.jsonl` dynamically.
   - Filter tabs: `All`, `Review Needed`, `Escalated`, `Completed` (Zustand state).
   - Search bar (`/` key focus shortcut) for real-time text matching.
   - Badges with shapes for scanning visual priority: `● Needs Review`, `▲ Clarification`, `⚠ Escalated`, `★ VIP`.
2. **Center Panel (Interactive Workspace):**
   - **Decision Lifecycle Tracker:** Renders horizontal stages highlighting the live path computed in the backend (`decision_stages`).
   - **Conversation Box:** Shows patient bubble vs. AI outcome console (proposals, warnings).
   - **Manual Composer:** Compose text overrides directly.
   - **Keyboard Shortcuts Engine:** Handles arrow navigation (`↑` / `↓`), confirmation (`A` for approve, `E` for escalate, `C` for clarify).
3. **Right Panel (Details & Overrides):**
   - **AI Explain Tab:** Shows metadata latency, API provider, and alternative candidate slots.
   - **CRM Tab:** Patient meta-file containing preferred provider, marketing status, tags, and coordinator notes.
   - **Calendar Tab:** Renders the day's timeline (busy/free slots) with custom inputs to inline-adjust (override) proposed provider or times.
   - **Decision Diff Logger:** Compares AI proposed values with human adjustments and records the diff + manual override reason back to `POST /api/confirm`.

---

## 5. Live Groq API Core Optimization & Rate-Limiting

- **Load-Balanced Model Selection:**
  - Intent classification and fast triage routing are handled by `llama-3.1-8b-instant` (low latency, separate rate limit pool).
  - Heavy entity extraction, temporal boundaries reasoning, and explanation notes are mapped to `llama-3.3-70b-versatile`.
- **Failover Safe Client:**
  - The API client in `app/client.py` includes a retry failover loop. If a `429 (Rate Limit)` is encountered on the primary model, it automatically degrades gracefully to `llama-3.1-8b-instant` rather than crashing.
- **Lexical Collision Rules:**
  - Spanish service synonyms are sorted by key length descending before resolution. This guarantees longer patterns (e.g. `"retoque de relleno de labios"`) match before shorter subsets (e.g. `"relleno"`).
- **Working Hours Checker:**
  - Sunday and weekday after-hours slot checks use `calendar_math.is_range_outside_working_hours` to direct customers immediately to the nearest slot, instead of asking for clarification.
