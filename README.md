# MyGlowTheory Scheduling Assistant & Operator Console

An enterprise-ready, agentic scheduling assistant built with **FastAPI** (Python 3.11+) and **Next.js 15 (App Router)**. This application routes, parses, validates, and recommends aesthetic medical appointments using live LLM models from Groq, fully backed by an automated 55-case evaluation test suite.

---

## 🛠 Architecture Overview

The system implements a **Decision-Centric Pipeline** pattern, strictly separating LLM inference logic (nondeterministic parsing and intent classification) from medical regulations, working hours, and clinic calendars (deterministic business logic).

```
[Inbound Message]
       │
       ▼
 ┌──────────┐      ┌─────────────────────────┐
 │ FastAPI  │ ───> │   DecisionOrchestrator  │
 └──────────┘      └─────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
  [AI Pipeline]                                 [Business Pipeline]
  - Message Triage (Spam, Out-Of-Office)        - Pre-scheduling clinical firewalls
  - Intent Classifier (Groq Llama 3)            - Registry validation (VIP, Do-Not-Book)
  - Named Entity Extractor                      - Working hours & calendar checking
                                                - Multi-factor candidate slot ranking
                                                        │
                                                        ▼
                                                [Decision outcome]
```

### 1. Domain Modeling (`app/domain/`)
* **`models.py`**: Pydantic models for core entities (`Patient`, `Provider`, `Service`, `Appointment`, `CandidateSlot`). Ensures type safety and validation at data boundaries.
* **`context.py`**: Holds metadata for tracking latency and token metrics, alongside an `EventStream` tracking execution stages in millisecond resolution.
* **`decision.py`**: Encapsulates the entire transaction state (`DecisionContext`) passed between pipeline components.

### 2. Decision-Centric Pipelines (`app/orchestrator.py`)
* **AI Pipeline**: Handles spam triage, routes scheduling vs. non-scheduling queries, and extracts entities (providers, services, dates).
* **Business Pipeline**: Applies strict rules (e.g. Do-Not-Book flags, clinical screening, working hours) and scores available slots using proximity-based candidate ranking algorithms.

---

## 🚀 Running the Project

### 1. Start the Backend API
1. Ensure your `.env` contains:
   ```env
   GROQ_API_KEY=gsk_...
   ```
2. Activate your virtual environment and start the Uvicorn server:
   ```bash
   .venv\Scripts\activate
   python -m uvicorn app.main:app --reload --port 8000
   ```

### 2. Start the Frontend Dashboard
1. Open a new terminal inside the `frontend` directory.
2. Build and start the Next.js server:
   ```bash
   npm.cmd run build
   npm.cmd run start
   ```
3. Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Testing & Evaluation

Run the automated 55-case test suite to confirm that LLM components and business rules pass with a 100% score:
```bash
python eval_harness.py
```
This runs real-time test assertions against multilingual requests, prompt injections, after-hours bookings, and conflicts.
