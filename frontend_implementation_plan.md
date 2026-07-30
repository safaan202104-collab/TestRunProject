# Frontend Implementation Plan: MyGlowTheory Operator Dashboard

This document details the updated blueprint for building an **enterprise-grade, operator-first** dashboard that integrates seamlessly with our existing granular branching scheduler backend. 

The focus is on AI explainability, high readability, and maximum staff productivity.

---

## 1. Product Philosophy & Visual Design
- **Operator-First, AI-Second:** The system assists the receptionist but keeps a human-in-the-loop at every critical decision.
- **Visual Aesthetic:** Inspired by Linear, Stripe, and Apple. We are dropping heavy glassmorphism in favor of layered surfaces, subtle depth, and ultra-high readability.
- **Typography:** **Inter** (or SF Pro Display) for crisp, enterprise-grade legibility.
- **Animations:** Minimal, focused on clarity and state transitions, not decoration.

---

## 2. Layout & Workflow
A structured three-column workspace designed for rapid triage without modals:

### Left Column: The Work Queue
Real clinics think in queues. Messages are organized by actionable states with smart shape-based hierarchy badges (not just colors):
- `[●] Needs Review` (Red/Gold)
- `[▲] Clarification Needed` (Amber)
- `[⚠] Escalation` (Crimson)
- `[★] VIP Waiting` (Purple)
- `[✓] Completed` (Green)
- `[ ] Archived` (Gray)

*Includes fast filtering and a command menu (`/` search).*

### Center Column: Workspace & Decision Lifecycle
- **Decision Lifecycle Visualization:** Staff instantly trust systems that show process. A real-time pipeline tracker shows the exact backend stages:
  *Receiving → Understanding → Checking Patient → Checking Calendar → Ranking Slots → Generating Recommendation → Ready*
- **Conversation Thread:** Clean message bubbles.
- **Action Composer:** Inline manual response input.
- **Inline Editing:** No modals. Click a proposed provider to see a dropdown; click a time to see the calendar inline.

### Right Column: Explainability, Slots & CRM
- **AI Explainability Panel:** Explicitly answers *"Why this recommendation?"* by surfacing backend logic (e.g., "Patient is VIP", "Requested provider was booked, proposing next available").
- **Ranked Candidate Slots:** The backend `slot_ranker.py` already computes multiple slots. We will display the top 3 ranked alternatives, not just the #1 choice.
- **Interactive Calendar:** A click-and-drag appointment adjustment view (the operator can drag a proposed slot to a new time to override the AI).
- **CRM Mini-Card:** Compact view of patient status, VIP tags, and historical visits.

---

## 3. Advanced Productivity & Feedback Loops

### Keyboard-Driven Workflow
Receptionists process hundreds of messages. Every action has a shortcut:
- `A` - Approve Booking
- `E` - Escalate to Human
- `C` - Send Clarification
- `↓ / ↑` - Next/Previous Message
- `Enter` - Open Message
- `/` - Search

### Decision Diff & Future-Proofing
When a receptionist inline-edits the AI's proposed slot or provider, the system stores the **Decision Diff** (AI proposed X → Human overrode to Y) along with a reason and timestamp. Even if the backend doesn't actively train on it today, this builds a goldmine dataset for future model fine-tuning.

### Observability & Evals Drawer
- **Admin Drawer:** Exposes backend latency, Groq API token usage, and routing metrics.
- **Evaluation Dashboard:** Surfaces the existing 55/55 `eval_harness.py` results directly in the UI, proving reliability to clinic managers.

---

## 4. Engineering Stack

As requested, we will use a modern, robust web application framework:
- **Core:** Next.js 15 (App Router) with TypeScript.
- **Styling:** Tailwind CSS v4 + shadcn/ui (customized for the Linear/Stripe aesthetic).
- **State & Data:** TanStack Query (for API fetching) and Zustand (for local UI state).
- **Forms:** React Hook Form + Zod (for validation matching backend Pydantic schemas).
- **Animations:** Framer Motion (strictly for micro-interactions like the Decision Lifecycle).

---

## 5. Backend Integration (API Layer)

The frontend will expose the existing backend state directly without inventing new logic. The FastAPI backend will be extended with the following endpoints:

- `GET /api/messages`: Retrieves the work queue.
- `POST /api/decide`: Feeds a message through the granular pipeline. Uses the existing Groq keys and models. Returns the full state: outcome, top 3 candidate slots, confidence score, and violated rules (if any).
- `POST /api/confirm`: Commits an approved or human-edited booking back to `crm.json`, including any override telemetry.
- `GET /api/evals`: Fetches the latest evaluation harness results for the dashboard.

---

## 6. Next Steps
1. Initialize the Next.js project in a `frontend/` directory.
2. Build out the three-column UI layout and the shadcn/ui components using the Inter font.
3. Wire up the FastAPI backend to serve the new `/api` routes that map to our existing logic.
