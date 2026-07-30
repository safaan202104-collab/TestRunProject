import json
from typing import Dict, Any
from app.client import get_llm_client

import time
from typing import Dict, Any, List, Optional
from app.session_memory import get_session_history, add_session_turn

from app import crm_indexer

def handle_ask_assistant(
    context: Dict[str, Any],
    question: str,
    session_id: Optional[str] = None,
    ui_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Handles questions from the clinic receptionist about the current decision.
    Refuses any action-oriented questions.
    Uses database-backed ReAct loop and session memory.
    """
    question_lower = question.lower()
    
    # Update conversational memory state if ui_context is passed
    active_state = {}
    if session_id:
        if ui_context:
            updates = {}
            if getattr(ui_context, "selected_patient_id", None):
                updates["active_patient_id"] = ui_context.selected_patient_id
            if getattr(ui_context, "selected_provider_id", None):
                updates["active_provider_id"] = ui_context.selected_provider_id
            if getattr(ui_context, "selected_appointment_id", None):
                updates["active_appointment_id"] = ui_context.selected_appointment_id
            if getattr(ui_context, "operator_role", None):
                updates["operator_role"] = ui_context.operator_role
            if getattr(ui_context, "current_view", None):
                updates["current_view"] = ui_context.current_view
            if updates:
                from app.session_memory import update_session_state
                update_session_state(session_id, updates)
                
        from app.session_memory import get_session_state
        active_state = get_session_state(session_id)
    
    # 1. Action prevention check
    forbidden_keywords = [
        "book", "override", "confirm", "delete", "cancel", "ignore", 
        "schedule", "reschedule", "bypass", "modify", "update", "send message"
    ]
    
    is_forbidden = False
    for kw in forbidden_keywords:
        if kw in question_lower:
            is_forbidden = True
            break
            
    if any(p in question_lower for p in ["change ", "set ", "make appointment", "make booking"]):
        is_forbidden = True
        
    if is_forbidden:
        refusal_msg = "I can explain the recommendation, but appointment actions must be performed through the operator interface."
        if session_id:
            add_session_turn(session_id, "user", question)
            add_session_turn(session_id, "assistant", refusal_msg)
        return {
            "answer": refusal_msg,
            "tool_calls": [],
            "reasoning_summary": "Refused action request",
            "sources": [],
            "grounded_confidence": "Refused (safety policy)",
            "rich_cards": []
        }
        
    # 2. Check if LLM client is in mock mode or has keys
    client = get_llm_client()
    client_type = client.get_client_type()
    
    if client_type == "mock":
        # Grounded mock responses for common questions
        outcome = context.get("outcome", "no_action")
        confidence = context.get("confidence_score", 1.0)
        rules = context.get("violated_rules", [])
        reason = context.get("reason", "")
        rationale = context.get("rationale", "")
        
        mock_reply = ""
        if "why did you recommend" in question_lower or "why was" in question_lower:
            if outcome == "propose_booking":
                proposal = context.get("booking_proposal") or {}
                prov_name = proposal.get("provider_name", "the requested provider")
                time_str = proposal.get("start_time", "the requested time")
                mock_reply = f"I recommended {prov_name} at {time_str} because it matches the requested service and fits within the provider's open calendar slots without violating any clinical constraints."
            elif outcome == "escalate_to_human":
                mock_reply = f"I escalated this case to a human because: {reason or 'The request requires clinical verification or contains issues.'}"
            else:
                mock_reply = "The case did not match any standard booking criteria or was non-scheduling."
        elif "why is confidence" in question_lower or "confidence score" in question_lower:
            mock_reply = f"The confidence score is {int(confidence * 100)}%. Factors that affected this include matching confidence on intent classification, entity extraction parser score, and rule compliance checks."
        elif "rules" in question_lower or "business rule" in question_lower:
            if rules:
                mock_reply = f"The following business rules were triggered/violated: {', '.join(rules)}."
            else:
                mock_reply = "No clinical business rules were violated for the recommended slot."
        elif "alternative" in question_lower or "closest" in question_lower:
            alts = context.get("alternative_proposals", [])
            if alts:
                alt_desc = []
                for a in alts:
                    alt_desc.append(f"{a.get('provider_name')} at {a.get('start_time')}")
                mock_reply = f"The closest alternative slots are: {', '.join(alt_desc)}."
            else:
                mock_reply = "No alternative slots were ranked or available."
        elif "summarize" in question_lower or "history" in question_lower:
            patient = context.get("patient") or {}
            pat_name = patient.get("name", "Unknown Patient")
            notes = patient.get("clinical_notes", "No clinical notes available.")
            mock_reply = f"Patient summary for {pat_name}: {notes}"
        else:
            mock_reply = f"Regarding your question: '{question}'. Based on the current context, the decision outcome is '{outcome}' with confidence {int(confidence * 100)}%. Rationale: {rationale or 'N/A'}."
            
        if session_id:
            add_session_turn(session_id, "user", question)
            add_session_turn(session_id, "assistant", mock_reply)
            
        return {
            "answer": mock_reply,
            "tool_calls": [],
            "reasoning_summary": "Mock Mode — direct lookup",
            "sources": [],
            "grounded_confidence": "Medium (mock registry)",
            "rich_cards": []
        }

    # 3. Ask AI 2.0 - ReAct Tool Loop (5 steps max)
    from app.tools.registry import TOOLS_REGISTRY, TOOLS_DESCRIPTION
    
    system_prompt = (
        "You are the MyGlowTheory Staff AI Assistant (Ask AI 2.0).\n"
        "Your purpose is to answer the clinic receptionist's questions about the current decision context AND the clinic's CRM data.\n"
        "You have access to the following tools to look up real-time information:\n"
        f"{TOOLS_DESCRIPTION}\n\n"
        "If explaining why a provider or slot failed, why the score is low, or why a decision was escalated:\n"
        "- Traced rules (e.g. do_not_book, specialty_mismatch, schedule_conflict) and explain details.\n"
        "- Ground your arguments on real-time data retrieved from tools (e.g. provider profile specialties, calendar, patient tags).\n\n"
        "If you need to use a tool to answer the question, output EXACTLY ONE raw JSON object in this format (and NOTHING ELSE):\n"
        '{"tool": "tool_name", "args": {"arg_name": "arg_value"}}\n\n'
        "If you DO NOT need a tool (or if you have the observation and are ready to answer), output your final answer directly in plain text.\n"
        "NEVER execute booking actions, overrides, or state changes. You are read-only.\n"
    )
    
    # Context and session history prep
    context_str = json.dumps(context, indent=2, default=str)
    
    history_str = ""
    if session_id:
        history = get_session_history(session_id)
        if history:
            history_str = "Session Conversation History:\n"
            for turn in history:
                role = "User" if turn["role"] == "user" else "Assistant"
                history_str += f"{role}: {turn['content']}\n"
            history_str += "\n"
            
    active_context_str = ""
    if active_state:
        active_details = []
        if active_state.get("active_patient_id"):
            pat = crm_indexer.get_patient_by_id(active_state["active_patient_id"])
            if pat:
                active_details.append(f"- Active Selected Patient: {pat['name']} (ID: {pat['id']})")
        if active_state.get("active_provider_id"):
            prov = crm_indexer.get_provider_by_id(active_state["active_provider_id"])
            if prov:
                active_details.append(f"- Active Selected Provider: {prov['name']} (ID: {prov['id']})")
        if active_state.get("active_appointment_id"):
            active_details.append(f"- Active Selected Appointment ID: {active_state['active_appointment_id']}")
        if active_state.get("operator_role"):
            active_details.append(f"- Current Operator Role: {active_state['operator_role']}")
        if active_state.get("current_view"):
            active_details.append(f"- Current Page View: {active_state['current_view']}")
            
        if active_details:
            active_context_str = "UI Context Selections:\n" + "\n".join(active_details) + "\n\n"

    conversation_history = (
        f"Current Decision Context:\n```json\n{context_str}\n```\n\n"
        f"{active_context_str}"
        f"{history_str}"
        f"Receptionist Question:\n{question}\n"
    )
    
    model = None
    if client_type == "groq":
        model = "llama-3.1-8b-instant"
    elif client_type == "anthropic":
        model = "claude-3-haiku-20240307"
    elif client_type == "openai":
        model = "gpt-4o-mini"
        
    tool_calls_meta = []
    try:
        for step in range(5): # Max 5 steps for multi-tool chaining
            response = client.chat_completion(
                system_prompt=system_prompt,
                prompt=conversation_history + "\nProvide your response:",
                model=model,
                temperature=0.0,
                max_tokens=600
            )
            response_text = response.strip()
            
            # Check if it's a tool call
            try:
                import re
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    tool_call = json.loads(json_match.group(0))
                else:
                    tool_call = json.loads(response_text)
                    
                if "tool" in tool_call and "args" in tool_call:
                    tool_name = tool_call["tool"]
                    args = tool_call["args"]
                    
                    t_start = time.time()
                    if tool_name in TOOLS_REGISTRY:
                        func = TOOLS_REGISTRY[tool_name]
                        observation = func(**args)
                    else:
                        observation = {"error": f"Tool '{tool_name}' not found."}
                    t_elapsed = round((time.time() - t_start) * 1000, 1)
                    
                    # Record tool call metadata
                    tool_calls_meta.append({
                        "tool": tool_name,
                        "args": args,
                        "duration_ms": t_elapsed,
                        "observation_preview": str(observation)[:200] + ("..." if len(str(observation)) > 200 else ""),
                        "observation": observation
                    })
                    
                    conversation_history += f"\nAssistant Action: {json.dumps(tool_call)}\nObservation: {json.dumps(observation, default=str)}\n"
                    continue # Loop back to let the LLM parse observation
            except Exception:
                pass # Non-JSON final answer
                
            # Log turn to session history
            if session_id:
                add_session_turn(session_id, "user", question)
                add_session_turn(session_id, "assistant", response_text)
                
            # Build sources, grounded_confidence, and rich_cards
            sources = list(set([tc["tool"] for tc in tool_calls_meta]))
            grounded_confidence = f"High (verified via {len(sources)} live tools)" if len(sources) > 0 else "Medium (conversational context)"
            
            rich_cards = []
            for tc in tool_calls_meta:
                t_name = tc["tool"]
                obs = tc.get("observation", {})
                if not isinstance(obs, dict) or "error" in obs:
                    continue
                
                if t_name in ["get_provider_daily_schedule", "get_provider_weekly_schedule", "check_availability"]:
                    rich_cards.append({
                        "type": "schedule_card",
                        "data": {
                            "provider_name": tc["args"].get("provider_name") or tc["args"].get("service_name") or "Schedule",
                            "date": tc["args"].get("date_str") or tc["args"].get("start_date_str") or "Selected Date",
                            "slots": obs.get("slots") or obs.get("appointments") or []
                        }
                    })
                elif t_name in ["get_provider_profile", "get_provider_supported_services"]:
                    rich_cards.append({
                        "type": "provider_card",
                        "data": {
                            "name": obs.get("name", tc["args"].get("provider_name")),
                            "specialties": obs.get("specialties", []),
                            "hours": obs.get("hours", {})
                        }
                    })
                elif t_name in ["clinic_revenue_summary", "no_show_rate", "cancellation_rate", "daily_bookings_count", "weekly_bookings_count"]:
                    rich_cards.append({
                        "type": "analytics_card",
                        "data": obs
                    })
                
            return {
                "answer": response_text,
                "tool_calls": tool_calls_meta,
                "reasoning_summary": f"Used {len(tool_calls_meta)} tool(s) to resolve the query.",
                "sources": sources,
                "grounded_confidence": grounded_confidence,
                "rich_cards": rich_cards
            }
            
        err_msg = "Error: Exceeded maximum tool execution steps."
        return {
            "answer": err_msg,
            "tool_calls": tool_calls_meta,
            "reasoning_summary": "Tool execution limit exceeded",
            "sources": list(set([tc["tool"] for tc in tool_calls_meta])),
            "grounded_confidence": "Low (limit exceeded)",
            "rich_cards": []
        }
    except Exception as e:
        err_msg = f"Error communicating with AI assistant: {str(e)}"
        return {
            "answer": err_msg,
            "tool_calls": tool_calls_meta,
            "reasoning_summary": "API Connection Error",
            "sources": [],
            "grounded_confidence": "Error (execution failed)",
            "rich_cards": []
        }
