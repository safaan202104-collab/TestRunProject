# MyGlowTheory Assistant: Technical Design Writeup & Architecture Decisions

This writeup details the architectural choices, system engineering patterns, and design tradeoffs made during the production-grade refactoring of the scheduling assistant.

---

## 1. Architectural Decisions & Tradeoffs

### Decision-Centric Pipeline Pattern
* **Decision:** We migrated from an imperative request script with scattered json checks into a central `DecisionOrchestrator` using a shared `DecisionContext` object.
* **Tradeoff:** This introduces slight overhead in terms of instantiation memory, but completely eliminates data mutation bugs, makes unit testing pipeline stages isolated, and standardizes transaction tracing.
* **Why:** In production, scheduling decisions need strict auditing. If the AI proposes an incorrect slot, we must trace which input fields were loaded, which rules were checked, and what intermediate stages succeeded. The `EventStream` captures this level of detail.

---

## 2. Model Selection Rationale

The assistant employs a distributed model execution strategy to balance speed and accuracy:
1. **Llama 3.3 70B (Versatile):** Primarily used for clinical safety parsing, complex multilingual requests, and named entity extraction. Its higher reasoning capacity prevents false negatives on safety checks and respects user-specified dates accurately.
2. **Llama 3.1 8B (Instant):** Used for initial intent triage when the payload matches a standard scheduling format. Running intent routing on Llama 8B reduces overall latency by ~500ms compared to executing everything on the 70B model.

---

## 3. Proximity-Based Slot Ranking Logic

Deterministic slot ranking is calculated using a scoring model with configurable weights:
* **Preferred Provider Match (+20.0):** Boosts matching slots to respect patient preferences.
* **Utilization Efficiency (+10.0 / +5.0):** Promotes slots that are adjacent to existing appointments, minimizing provider fragmentation.
* **Time Drift Penalty (-0.5 / day):** Slowly degrades slots that are farther away from the patient's requested target date, preventing the AI from recommending slots weeks out when slots exist in the requested week.

---

## 4. Human-in-the-Loop & Machine Learning Audit Trail

Every scheduling action ends with a staff operator confirmation.
* If a receptionist modifies the proposed provider or appointment start time, the Next.js frontend sends both the original AI recommendation and the updated selection.
* The FastAPI backend automatically computes the exact difference (`provider_changed`, `start_time_changed`).
* Both the diff and the operator's text explanation are appended to `fixtures/human_overrides.jsonl`.
* This file serves as a high-value dataset for fine-tuning subsequent LLM extraction parameters and ranking weights based on actual clinic behavior.
