import os
import re
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Depends
from app.services.auth import Permission

def check_permission(required_permission: Permission):
    def dependency(authorization: Optional[str] = Header(None)):
        token = authorization or "dev-token-developer"
        from app.services.auth import verify_permission
        verify_permission(token, required_permission)
    return dependency
from app.schema_validator import DecideRequest, DecideResponse, BookingProposal, AskRequest, SimulateRequest
from app import crm_indexer
from app import intent_router
from app import entity_extractor
from app import business_rules
from app import calendar_math
from app import slot_ranker
from app import rationale_generator
from app import interval_tree
from app.ask_assistant import handle_ask_assistant
from app.dynamic_config import load_dynamic_config, save_dynamic_config
from app.analytics_helper import get_aggregated_analytics, log_request_telemetry, log_human_override
from app.simulation_engine import generate_simulated_message, clear_simulation_queue, QUEUE_FILE



from app.orchestrator import DecisionOrchestrator
from fastapi.middleware.cors import CORSMiddleware
import json
import sys

app = FastAPI(title="MyGlowTheory Inbox Scheduling Assistant")

# Enable CORS for Next.js dev server on port 3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    from app.database import init_db
    init_db()

@app.get("/api/messages")
def get_messages_endpoint():
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures", "eval.jsonl"))
    messages = []
    
    # Read simulation queue first
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    msg = json.loads(line)
                    msg["queue_type"] = "Simulation"
                    messages.append(msg)
                    
    if not os.path.exists(file_path):
        return messages
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                msg = json.loads(line)
                msg["queue_type"] = "Evaluation"
                messages.append(msg)
    return messages

@app.post("/api/simulate")
def simulate_endpoint(request: SimulateRequest):
    entry = generate_simulated_message(
        message=request.message,
        channel=request.channel,
        language=request.language,
        scenario=request.scenario,
        patient_id=request.patient_id
    )
    
    # Instantiate decide request from the newly generated queue entry
    decide_req = DecideRequest(**entry["input"])
    
    # Run the orchestrator on this new live message
    decision = decide_endpoint(decide_req)
    
    return {"status": "success", "message": entry, "decision": decision}

@app.post("/api/simulate/clear")
def clear_simulate_endpoint():
    clear_simulation_queue()
    return {"status": "success"}

def background_booking_workflow(
    appointment: dict,
    patient_id: str,
    provider_id: str,
    service_id: str
):
    try:
        from app.services.documents import generate_appointment_confirmation, generate_invoice
        from app.services.notifications import NotificationService
        
        patient = crm_indexer.get_patient_by_id(patient_id) or {}
        provider = crm_indexer.get_provider_by_id(provider_id) or {}
        service = crm_indexer.get_service_by_id(service_id) or {}
        
        patient_name = patient.get("name", "Patient")
        patient_email = patient.get("email", "patient@example.com")
        patient_phone = patient.get("phone", "+15555555555")
        
        provider_name = provider.get("name", "Provider")
        service_name = service.get("name", "Service")
        
        # 1. Generate PDF confirmation
        generate_appointment_confirmation(
            appointment=appointment,
            patient_name=patient_name,
            provider_name=provider_name,
            service_name=service_name
        )
        
        # 2. Generate PDF Invoice
        generate_invoice(
            appointment=appointment,
            patient_name=patient_name,
            provider_name=provider_name,
            service_name=service_name
        )
        
        # 3. Send Notifications
        NotificationService.send_confirmation_email(
            appointment=appointment,
            patient_name=patient_name,
            patient_email=patient_email,
            provider_name=provider_name,
            service_name=service_name
        )
        
        NotificationService.send_confirmation_sms(
            appointment=appointment,
            patient_name=patient_name,
            patient_phone=patient_phone,
            provider_name=provider_name,
            service_name=service_name
        )
        
        NotificationService.generate_calendar_invite(
            appointment=appointment,
            patient_name=patient_name,
            patient_email=patient_email,
            provider_name=provider_name,
            service_name=service_name
        )
    except Exception as e:
        print(f"[WORKFLOW ERROR] Background workflow failed for appt {appointment.get('id')}: {e}")

@app.post("/api/confirm")
def confirm_booking_endpoint(payload: dict, background_tasks: BackgroundTasks, authorization: Optional[str] = Header(None)):
    token = authorization or "dev-token-developer"
    from app.services.auth import verify_permission
    verify_permission(token, Permission.APPROVE_BOOKING)
    if payload.get("override_reason"):
        verify_permission(token, Permission.OVERRIDE_AI)
    patient_id = payload.get("patient_id")
    provider_id = payload.get("provider_id")
    service_id = payload.get("service_id")
    start_time = payload.get("start_time")
    duration_minutes = payload.get("duration_minutes", 30)
    price_usd = payload.get("price_usd", 0.0)
    rescheduled_appointment_id = payload.get("rescheduled_appointment_id")
    override_reason = payload.get("override_reason")
    ai_proposal = payload.get("ai_proposal")

    from app.interval_tree import has_overlap
    from app.calendar_math import parse_iso_datetime
    from app.slot_ranker import find_candidate_slots
    from datetime import timedelta

    start_dt = parse_iso_datetime(start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    if has_overlap(provider_id, start_dt, end_dt):
        svc = crm_indexer.get_service_by_id(service_id)
        pat = crm_indexer.get_patient_by_id(patient_id) if patient_id else None
        
        # Search for candidates starting from the conflict date to 7 days later
        alternatives = find_candidate_slots(
            service=svc,
            requested_provider=None,  # search all providers
            patient=pat,
            start_search=start_dt,
            end_search=start_dt + timedelta(days=7),
            now_dt=start_dt
        )
        return {
            "status": "error",
            "error_type": "concurrency_conflict",
            "message": f"Conflict detected: Provider {provider_id} is already booked at {start_time}.",
            "alternatives": alternatives
        }

    if override_reason:
        diff = {}
        if ai_proposal:
            if ai_proposal.get("provider_id") != provider_id:
                diff["provider_changed"] = {
                    "ai": ai_proposal.get("provider_name") or ai_proposal.get("provider_id"),
                    "human": provider_id
                }
            if ai_proposal.get("start_time") != start_time:
                diff["start_time_changed"] = {
                    "ai": ai_proposal.get("start_time"),
                    "human": start_time
                }
                
        log_entry = {
            "patient_id": patient_id,
            "override_reason": override_reason,
            "original_ai_proposal": ai_proposal,
            "final_human_choice": {
                "provider_id": provider_id,
                "service_id": service_id,
                "start_time": start_time,
                "duration_minutes": duration_minutes,
                "price_usd": price_usd
            },
            "difference": diff,
            "category": "manual_override"
        }
        log_human_override(log_entry)
            
    if rescheduled_appointment_id:
        res = crm_indexer.reschedule_appointment(
            appt_id=rescheduled_appointment_id,
            start_time=start_time,
            provider_id=provider_id
        )
    else:
        res = crm_indexer.add_appointment(
            patient_id=patient_id,
            provider_id=provider_id,
            service_id=service_id,
            start_time=start_time,
            duration_minutes=duration_minutes,
            price_usd=price_usd,
            status="confirmed"
        )
        
    if res:
        crm_indexer.add_audit_log(
            patient_id=patient_id,
            action="appointment_confirmed" if not rescheduled_appointment_id else "appointment_rescheduled",
            details={
                "appointment_id": res.get("id"),
                "provider_id": provider_id,
                "service_id": service_id,
                "start_time": start_time,
                "override_reason": override_reason,
                "original_ai_proposal": ai_proposal
            }
        )
    
    # Dispatch background jobs for docs and notifications
    if res:
        background_tasks.add_task(
            background_booking_workflow,
            res,
            patient_id,
            provider_id,
            service_id
        )

    pdf_filename = f"confirmation_{res.get('id')}.pdf" if res else None
    result = {"status": "success", "appointment": res}
    if pdf_filename:
        result["pdf_filename"] = pdf_filename
    return result

@app.get("/api/docs/download/{filename}")
def download_document(filename: str):
    from fastapi.responses import FileResponse
    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "runtime", "docs"))
    filepath = os.path.join(docs_dir, filename)
    if not os.path.exists(filepath):
        return {"error": "File not found"}
    return FileResponse(filepath, media_type="application/pdf", filename=filename)

@app.get("/api/evals", dependencies=[Depends(check_permission(Permission.RUN_EVALS))])
def get_evals_endpoint():
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    from eval_harness import run_evals
    passed, total, categories = run_evals()
    return {
        "passed": passed,
        "total": total,
        "score_pct": round(passed / total * 100, 1),
        "categories": categories
    }

@app.get("/api/crm")
def get_crm_endpoint():
    return {
        "patients": crm_indexer._crm_data.get("patients", []),
        "providers": crm_indexer.get_all_providers(),
        "services": crm_indexer.get_all_services(),
        "appointments": crm_indexer._crm_data.get("appointments", [])
    }

def has_safety_word(text: str) -> bool:
    """Helper to match safety words strictly with word boundaries to avoid sub-word collisions."""
    safety_words = ["uneven", "numb", "rash", "pain", "hurt", "bad", "disappointed", "refund", "1-star", "one star", "dispute", "complain", "discontent", "blue", "cold", "symptom", "side effect", "normal", "turning"]
    for w in safety_words:
        if re.search(r'\b' + re.escape(w) + r'\b', text):
            return True
    return False

orchestrator = DecisionOrchestrator()

@app.post("/decide", response_model=DecideResponse)
def decide_endpoint(request: DecideRequest):
    # Run the centralized Orchestrator
    context = orchestrator.run(request)
    
    # Map DecisionContext back to DecideResponse Pydantic model
    booking_proposal = None
    if context.proposed_slot:
        booking_proposal = BookingProposal(
            provider_id=context.proposed_slot.provider_id,
            provider_name=context.proposed_slot.provider_name,
            service_id=context.proposed_slot.service_id,
            service_name=context.proposed_slot.service_name,
            start_time=context.proposed_slot.start_time,
            duration_minutes=context.proposed_slot.duration_minutes,
            price_usd=context.proposed_slot.price_usd,
            rescheduled_appointment_id=context.proposed_slot.rescheduled_appointment_id
        )
        
    alternative_proposals = []
    if len(context.alternative_slots) > 1:
        for s in context.alternative_slots[1:4]:
            alternative_proposals.append(BookingProposal(
                provider_id=s.provider_id,
                provider_name=s.provider_name,
                service_id=s.service_id,
                service_name=s.service_name,
                start_time=s.start_time,
                duration_minutes=s.duration_minutes,
                price_usd=s.price_usd,
                rescheduled_appointment_id=s.rescheduled_appointment_id
            ))
            
    # Format the Event Stream as list of dicts
    formatted_stream = []
    for event in context.event_stream.events:
        formatted_stream.append({
            "stage_name": event.stage_name,
            "status": event.status,
            "duration_ms": round(event.duration_ms, 1),
            "started_at": event.started_at,
            "finished_at": event.finished_at,
            "metadata": event.metadata
        })
        
    decision_stages = [e.stage_name for e in context.event_stream.events]
    if "Ready" not in decision_stages:
        decision_stages.append("Ready")
        
    elapsed_ms = context.request_context.elapsed_ms()
    
    # Log telemetry for Admin Analytics dashboard
    telemetry_entry = {
        "timestamp": datetime.now().isoformat(),
        "outcome": context.outcome,
        "confidence_score": context.confidence_score,
        "latency_ms": elapsed_ms,
        "metadata": {
            "prompt_tokens": context.request_context.prompt_tokens,
            "completion_tokens": context.request_context.completion_tokens,
            "estimated_cost_usd": context.request_context.estimated_cost_usd,
            "fallback_used": context.request_context.fallback_used,
            "retries": context.request_context.retries,
            "model": context.request_context.model,
            "api_provider": context.request_context.api_provider
        }
    }
    log_request_telemetry(telemetry_entry)
    
    return DecideResponse(
        outcome=context.outcome,
        booking_proposal=booking_proposal,
        rationale=context.rationale,
        question=context.question,
        reason=context.reason,
        alternative_proposals=alternative_proposals,
        confidence_score=context.confidence_score,
        violated_rules=context.violated_rules,
        decision_stages=decision_stages,
        event_stream=formatted_stream,
        metadata={
            "latency_ms": round(elapsed_ms, 1),
            "model": context.request_context.model,
            "api_provider": context.request_context.api_provider,
            "timestamp": datetime.now().isoformat(),
            "prompt_tokens": context.request_context.prompt_tokens,
            "completion_tokens": context.request_context.completion_tokens,
            "estimated_cost_usd": context.request_context.estimated_cost_usd,
            "fallback_used": context.request_context.fallback_used,
            "retries": context.request_context.retries,
            "extracted_service": context.extracted_service_name,
            "extracted_provider": context.extracted_provider_name,
            "extracted_time_text": context.extracted_time_text,
            "resolved_time_boundary": context.resolved_time_boundary
        }
    )

@app.post("/api/ask")
def ask_assistant_endpoint(request: AskRequest):
    try:
        res = handle_ask_assistant(request.context, request.question, request.session_id, request.ui_context)
        return {
            "reply": res["answer"],
            "tool_calls": res["tool_calls"],
            "reasoning_summary": res["reasoning_summary"],
            "sources": res.get("sources", []),
            "grounded_confidence": res.get("grounded_confidence", "N/A"),
            "rich_cards": res.get("rich_cards", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
def search_endpoint(q: str = ""):
    if not q:
        return {"patients": [], "providers": [], "services": [], "appointments": []}
    
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        from app.db_models import Patient as DBPatient, Provider as DBProvider, Service as DBService, Appointment as DBAppointment
        
        # Query Patients
        patients_query = db.query(DBPatient).filter(
            (DBPatient.name.like(f"%{q}%")) | 
            (DBPatient.phone.like(f"%{q}%")) | 
            (DBPatient.email.like(f"%{q}%"))
        ).limit(10).all()
        patients = []
        for p in patients_query:
            patients.append({
                "id": p.id,
                "name": p.name,
                "phone": p.phone,
                "email": p.email,
                "vip": p.vip
            })
            
        # Query Providers
        providers_query = db.query(DBProvider).filter(
            DBProvider.name.like(f"%{q}%")
        ).limit(10).all()
        providers = []
        for prov in providers_query:
            providers.append({
                "id": prov.id,
                "name": prov.name,
                "specialties": prov.specialties
            })
            
        # Query Services
        services_query = db.query(DBService).filter(
            DBService.name.like(f"%{q}%")
        ).limit(10).all()
        services = []
        for s in services_query:
            services.append({
                "id": s.id,
                "name": s.name,
                "price_usd": s.price_usd
            })
            
        # Query Appointments
        appointments_query = db.query(DBAppointment).filter(
            (DBAppointment.id.like(f"%{q}%")) | 
            (DBAppointment.status.like(f"%{q}%"))
        ).limit(10).all()
        appointments = []
        for appt in appointments_query:
            appointments.append({
                "id": appt.id,
                "patient_id": appt.patient_id,
                "provider_id": appt.provider_id,
                "start": appt.start,
                "status": appt.status
            })
            
        return {
            "patients": patients,
            "providers": providers,
            "services": services,
            "appointments": appointments
        }
    except Exception as e:
        return {"error": str(e), "patients": [], "providers": [], "services": [], "appointments": []}
    finally:
        db.close()

@app.get("/api/health")
def health_endpoint():
    from sqlalchemy import text
    from app.database import SessionLocal
    db = SessionLocal()
    health = {
        "status": "healthy",
        "details": {
            "database": "healthy",
            "llm_provider": "healthy",
            "workers": "healthy",
            "notifications": "healthy"
        }
    }
    try:
        # Ping DB
        db.execute(text("SELECT 1"))
    except Exception as e:
        health["status"] = "degraded"
        health["details"]["database"] = f"error: {str(e)}"
    finally:
        db.close()
        
    # Ping Redis
    import os
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis
            r = redis.from_url(redis_url, socket_connect_timeout=1)
            r.ping()
        except Exception as e:
            health["status"] = "degraded"
            health["details"]["workers"] = f"redis error: {str(e)}"
            
    return health


@app.get("/api/config", dependencies=[Depends(check_permission(Permission.MODIFY_CONFIG))])
def get_config_endpoint():
    return load_dynamic_config()

@app.post("/api/config", dependencies=[Depends(check_permission(Permission.MODIFY_CONFIG))])
def save_config_endpoint(payload: dict):
    try:
        save_dynamic_config(payload)
        return {"status": "success", "config": payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics", dependencies=[Depends(check_permission(Permission.ACCESS_ANALYTICS))])
def get_analytics_endpoint():
    try:
        return get_aggregated_analytics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



