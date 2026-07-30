import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app import crm_indexer
from app import calendar_math
from app import interval_tree
from app.slot_ranker import find_candidate_slots

# ---------- Provider Tools ----------

def get_provider_profile(provider_name: str) -> Dict[str, Any]:
    """Returns the full profile of a provider including specialties and hours."""
    prov = crm_indexer.find_provider_by_name(provider_name)
    if not prov:
        return {"error": f"Provider '{provider_name}' not found."}
    return {
        "id": prov["id"],
        "name": prov["name"],
        "specialties": prov.get("specialties", []),
        "working_hours": prov.get("hours", {})
    }

def get_provider_daily_schedule(provider_name: str, date_str: str) -> Dict[str, Any]:
    """Returns all active appointments for a provider on a specific date (YYYY-MM-DD)."""
    prov = crm_indexer.find_provider_by_name(provider_name)
    if not prov:
        return {"error": f"Provider '{provider_name}' not found."}
        
    appts = crm_indexer.get_appointments_for_provider(prov["id"])
    daily_appts = []
    for a in appts:
        if a.get("status") == "cancelled":
            continue
        try:
            start_dt = calendar_math.parse_iso_datetime(a["start"])
            if start_dt.strftime("%Y-%m-%d") == date_str:
                daily_appts.append(a)
        except Exception:
            continue
            
    return {
        "provider_name": prov["name"],
        "date": date_str,
        "appointments_count": len(daily_appts),
        "appointments": daily_appts
    }

def get_provider_weekly_schedule(provider_name: str, start_date_str: str) -> Dict[str, Any]:
    """Returns all active appointments for a provider for a week starting from a specific date (YYYY-MM-DD)."""
    prov = crm_indexer.find_provider_by_name(provider_name)
    if not prov:
        return {"error": f"Provider '{provider_name}' not found."}
        
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except Exception:
        return {"error": "Invalid start_date_str. Use YYYY-MM-DD."}
        
    end_date = start_date + timedelta(days=7)
    
    appts = crm_indexer.get_appointments_for_provider(prov["id"])
    weekly_appts = []
    for a in appts:
        if a.get("status") == "cancelled":
            continue
        try:
            appt_date = calendar_math.parse_iso_datetime(a["start"]).date()
            if start_date <= appt_date < end_date:
                weekly_appts.append(a)
        except Exception:
            continue
            
    return {
        "provider_name": prov["name"],
        "week_start": start_date_str,
        "appointments_count": len(weekly_appts),
        "appointments": weekly_appts
    }

def provider_utilization(provider_name: str) -> Dict[str, Any]:
    """Returns the utilization rate for a given provider (hours booked vs hours available)."""
    prov = crm_indexer.find_provider_by_name(provider_name)
    if not prov:
        return {"error": f"Provider '{provider_name}' not found."}
        
    appointments = crm_indexer.get_appointments_for_provider(prov["id"])
    active_appointments = [a for a in appointments if a.get("status") not in ("cancelled", "rescheduled")]
    
    total_minutes_booked = sum(a.get("duration", 0) for a in active_appointments)
    total_hours_booked = total_minutes_booked / 60.0
    
    return {
        "provider_name": prov["name"],
        "total_hours_booked": total_hours_booked,
        "total_appointments": len(active_appointments)
    }

def get_provider_supported_services(provider_name: str) -> Dict[str, Any]:
    """Returns services that can be performed by the provider based on their specialties."""
    prov = crm_indexer.find_provider_by_name(provider_name)
    if not prov:
        return {"error": f"Provider '{provider_name}' not found."}
        
    specialties = prov.get("specialties", [])
    all_services = crm_indexer.get_all_services()
    supported = []
    for s in all_services:
        req = s.get("required_specialty")
        if not req or req in specialties:
            supported.append(s)
            
    return {
        "provider_name": prov["name"],
        "supported_services_count": len(supported),
        "services": supported
    }

# ---------- Patient Tools ----------

def get_patient_profile(patient_name: str) -> Dict[str, Any]:
    """Returns the full patient profile including tags and VIP status."""
    patient = crm_indexer.find_patient_by_name(patient_name)
    if not patient:
        return {"error": f"Patient '{patient_name}' not found."}
    return patient

def get_patient_history(patient_name: str) -> Dict[str, Any]:
    """Returns past/completed appointments and treatment history of a patient."""
    patient = crm_indexer.find_patient_by_name(patient_name)
    if not patient:
        return {"error": f"Patient '{patient_name}' not found."}
        
    appts = crm_indexer.get_appointments_for_patient(patient["id"])
    now_str = datetime.now().isoformat()
    past_appts = [a for a in appts if a.get("start") < now_str]
    
    return {
        "patient_name": patient["name"],
        "past_appointments_count": len(past_appts),
        "appointments": past_appts
    }

def get_patient_upcoming(patient_name: str) -> Dict[str, Any]:
    """Returns upcoming future appointments for a patient."""
    patient = crm_indexer.find_patient_by_name(patient_name)
    if not patient:
        return {"error": f"Patient '{patient_name}' not found."}
        
    appts = crm_indexer.get_appointments_for_patient(patient["id"])
    now_str = datetime.now().isoformat()
    upcoming = [a for a in appts if a.get("start") >= now_str and a.get("status") not in ("cancelled", "rescheduled")]
    
    return {
        "patient_name": patient["name"],
        "upcoming_appointments_count": len(upcoming),
        "appointments": upcoming
    }

def get_patient_preferred_provider(patient_name: str) -> Dict[str, Any]:
    """Returns preferred provider details for a patient."""
    patient = crm_indexer.find_patient_by_name(patient_name)
    if not patient:
        return {"error": f"Patient '{patient_name}' not found."}
        
    pref_id = patient.get("preferred_provider_id")
    if not pref_id:
        return {"patient_name": patient["name"], "preferred_provider": None}
        
    provider = crm_indexer.get_provider_by_id(pref_id)
    return {
        "patient_name": patient["name"],
        "preferred_provider": provider
    }

# ---------- Scheduling Tools ----------

def check_availability(service_name: str, date_str: str) -> Dict[str, Any]:
    """Checks availability for a specific service on a specific date (YYYY-MM-DD)."""
    svc = crm_indexer.find_service_by_name(service_name)
    if not svc:
        return {"error": f"Service '{service_name}' not found."}
        
    try:
        start_search = calendar_math.parse_iso_datetime(f"{date_str}T00:00:00-07:00")
    except Exception:
        return {"error": "Invalid date_str format. Use YYYY-MM-DD."}
        
    end_search = start_search + timedelta(days=1)
    
    candidates = find_candidate_slots(
        service=svc,
        requested_provider=None,
        patient=None,
        start_search=start_search,
        end_search=end_search,
        now_dt=start_search
    )
    
    return {
        "service_name": svc["name"],
        "date": date_str,
        "available_slots_count": len(candidates),
        "slots": candidates[:5]
    }

def get_appointment_details(appointment_id: str) -> Dict[str, Any]:
    """Returns all details of a specific appointment by ID."""
    db = crm_indexer._db()
    try:
        from app.db_models import Appointment as DBAppointment
        appt = db.query(DBAppointment).filter(DBAppointment.id == appointment_id).first()
        if not appt:
            return {"error": f"Appointment ID '{appointment_id}' not found."}
        return crm_indexer._row_to_dict(appt)
    except Exception:
        return {"error": "Database lookup failed."}
    finally:
        db.close()

def detect_conflicts(provider_name: str, start_time: str, duration_minutes: int) -> Dict[str, Any]:
    """Checks if a specific slot conflicts with any existing appointments for a provider."""
    prov = crm_indexer.find_provider_by_name(provider_name)
    if not prov:
        return {"error": f"Provider '{provider_name}' not found."}
        
    try:
        start_dt = calendar_math.parse_iso_datetime(start_time)
        end_dt = start_dt + timedelta(minutes=duration_minutes)
    except Exception:
        return {"error": "Invalid start_time format. Use ISO format (e.g. YYYY-MM-DDTHH:MM:SS-07:00)."}
        
    conflict = interval_tree.get_overlapping_appointment(prov["id"], start_dt, end_dt)
    return {
        "provider_name": prov["name"],
        "slot_start": start_time,
        "duration_minutes": duration_minutes,
        "has_conflict": conflict is not None,
        "conflicting_appointment": conflict
    }

# ---------- Clinic Analytics ----------

def clinic_revenue_summary() -> Dict[str, Any]:
    """Returns a summary of clinic revenue based on active appointments."""
    providers = crm_indexer.get_all_providers()
    total_revenue = 0.0
    
    for prov in providers:
        appointments = crm_indexer.get_appointments_for_provider(prov["id"])
        active_appointments = [a for a in appointments if a.get("status") not in ("cancelled", "rescheduled")]
        total_revenue += sum(a.get("price", 0.0) for a in active_appointments)
        
    return {
        "total_revenue_usd": total_revenue
    }

def daily_bookings_count(date_str: str) -> Dict[str, Any]:
    """Returns the total bookings count across all providers on a specific day (YYYY-MM-DD)."""
    providers = crm_indexer.get_all_providers()
    total_count = 0
    for prov in providers:
        appts = crm_indexer.get_appointments_for_provider(prov["id"])
        for a in appts:
            if a.get("status") not in ("cancelled", "rescheduled"):
                try:
                    appt_date = calendar_math.parse_iso_datetime(a["start"]).strftime("%Y-%m-%d")
                    if appt_date == date_str:
                        total_count += 1
                except Exception:
                    continue
    return {
        "date": date_str,
        "bookings_count": total_count
    }

def weekly_bookings_count(start_date_str: str) -> Dict[str, Any]:
    """Returns total bookings across all providers for a week starting from a specific day (YYYY-MM-DD)."""
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except Exception:
        return {"error": "Invalid start_date_str. Use YYYY-MM-DD."}
        
    end_date = start_date + timedelta(days=7)
    providers = crm_indexer.get_all_providers()
    total_count = 0
    
    for prov in providers:
        appts = crm_indexer.get_appointments_for_provider(prov["id"])
        for a in appts:
            if a.get("status") not in ("cancelled", "rescheduled"):
                try:
                    appt_date = calendar_math.parse_iso_datetime(a["start"]).date()
                    if start_date <= appt_date < end_date:
                        total_count += 1
                except Exception:
                    continue
                    
    return {
        "week_start": start_date_str,
        "bookings_count": total_count
    }

def no_show_rate() -> Dict[str, Any]:
    """Returns the no-show rate clinic-wide."""
    db = crm_indexer._db()
    try:
        from app.db_models import Appointment as DBAppointment
        total = db.query(DBAppointment).count()
        no_shows = db.query(DBAppointment).filter(DBAppointment.status == "no_show").count()
        rate = (no_shows / total * 100) if total > 0 else 0.0
        return {
            "total_appointments": total,
            "no_shows": no_shows,
            "no_show_rate_pct": round(rate, 2)
        }
    except Exception:
        return {"error": "Failed to query no-show rate."}
    finally:
        db.close()

def cancellation_rate() -> Dict[str, Any]:
    """Returns the cancellation rate clinic-wide."""
    db = crm_indexer._db()
    try:
        from app.db_models import Appointment as DBAppointment
        total = db.query(DBAppointment).count()
        cancelled = db.query(DBAppointment).filter(DBAppointment.status == "cancelled").count()
        rate = (cancelled / total * 100) if total > 0 else 0.0
        return {
            "total_appointments": total,
            "cancelled": cancelled,
            "cancellation_rate_pct": round(rate, 2)
        }
    except Exception:
        return {"error": "Failed to query cancellation rate."}
    finally:
        db.close()

# ---------- CRM Lookup Tools ----------

def find_patient_by_name(patient_name: str) -> Dict[str, Any]:
    """Finds a patient record by matching name or partial name."""
    patient = crm_indexer.find_patient_by_name(patient_name)
    if not patient:
        return {"error": f"Patient with name containing '{patient_name}' not found."}
    return patient

def find_patient_by_phone(phone: str) -> Dict[str, Any]:
    """Finds a patient record by phone number (exact or suffix match)."""
    patient = crm_indexer.get_patient_by_phone(phone)
    if not patient:
        return {"error": f"Patient with phone '{phone}' not found."}
    return patient

def find_patient_by_email(email: str) -> Dict[str, Any]:
    """Finds a patient record by email address (case-insensitive)."""
    patient = crm_indexer.get_patient_by_email(email)
    if not patient:
        return {"error": f"Patient with email '{email}' not found."}
    return patient


def get_platform_guideline(query_key: str) -> Dict[str, Any]:
    """Look up platform guide docs, procedural guidelines, warning meanings, and scoring parameters."""
    import json
    import os
    kb_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runtime", "knowledge_base.json")
    if not os.path.exists(kb_path):
        return {"error": "Knowledge base not initialized."}
    try:
        with open(kb_path, "r") as f:
            data = json.load(f)
        
        # Flattened search
        query_key_lower = query_key.lower()
        for section, items in data.items():
            for k, val in items.items():
                if query_key_lower in k.lower() or k.lower() in query_key_lower:
                    return {
                        "topic": k,
                        "category": section,
                        "content": val
                    }
        return {"result": "No specific guide found for this query key. Check general platform guidelines."}
    except Exception as e:
        return {"error": f"Failed to read knowledge base: {str(e)}"}


# ---------- Registry Mapping ----------

TOOLS_REGISTRY = {
    "get_provider_profile": get_provider_profile,
    "get_provider_daily_schedule": get_provider_daily_schedule,
    "get_provider_weekly_schedule": get_provider_weekly_schedule,
    "provider_utilization": provider_utilization,
    "get_provider_supported_services": get_provider_supported_services,
    "get_patient_profile": get_patient_profile,
    "get_patient_history": get_patient_history,
    "get_patient_upcoming": get_patient_upcoming,
    "get_patient_preferred_provider": get_patient_preferred_provider,
    "check_availability": check_availability,
    "get_appointment_details": get_appointment_details,
    "detect_conflicts": detect_conflicts,
    "clinic_revenue_summary": clinic_revenue_summary,
    "daily_bookings_count": daily_bookings_count,
    "weekly_bookings_count": weekly_bookings_count,
    "no_show_rate": no_show_rate,
    "cancellation_rate": cancellation_rate,
    "find_patient_by_name": find_patient_by_name,
    "find_patient_by_phone": find_patient_by_phone,
    "find_patient_by_email": find_patient_by_email,
    "get_platform_guideline": get_platform_guideline
}

TOOLS_DESCRIPTION = """
Available tools organized by logical domain namespaces:

[Patient Domain]
- find_patient_by_name(patient_name: str): Search for patient profile.
- find_patient_by_phone(phone: str): Search for patient profile by phone.
- find_patient_by_email(email: str): Search for patient profile by email.
- get_patient_profile(patient_name: str): Returns detailed patient fields, clinical notes, VIP status, do_not_book.
- get_patient_history(patient_name: str): Returns past completed appointments and treatments.
- get_patient_upcoming(patient_name: str): Returns future active appointments.
- get_patient_preferred_provider(patient_name: str): Returns patient's preferred provider.

[Provider Domain]
- get_provider_profile(provider_name: str): Returns provider profile specialties and hours.
- get_provider_daily_schedule(provider_name: str, date_str: str): Returns active appointments for provider on YYYY-MM-DD.
- get_provider_weekly_schedule(provider_name: str, start_date_str: str): Returns appointments starting YYYY-MM-DD.
- provider_utilization(provider_name: str): Returns total hours booked vs total hours available.
- get_provider_supported_services(provider_name: str): Returns services this provider is certified to perform.

[Scheduling Domain]
- check_availability(service_name: str, date_str: str): Returns top 5 available slots on YYYY-MM-DD.
- get_appointment_details(appointment_id: str): Returns appointment fields by ID.
- detect_conflicts(provider_name: str, start_time: str, duration_minutes: int): Checks slot availability and overlap.

[Analytics Domain]
- clinic_revenue_summary(): Total clinic revenue summary.
- daily_bookings_count(date_str: str): Total active appointments on YYYY-MM-DD.
- weekly_bookings_count(start_date_str: str): Total active appointments starting YYYY-MM-DD.
- no_show_rate(): Clinic-wide no-show rate.
- cancellation_rate(): Clinic-wide cancellation rate.

[Platform Guide Domain]
- get_platform_guideline(query_key: str): Query platform guide guidelines, warning messages meaning, and confidence score explanations.
"""
