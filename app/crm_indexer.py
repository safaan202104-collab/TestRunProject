"""
CRM Indexer — Database-backed version.
All public function signatures are preserved from the original JSON version.
The module uses SQLAlchemy queries instead of in-memory dicts.
Falls back to JSON if the database is not yet seeded.
"""
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from app.database import SessionLocal
from app.db_models import (
    Patient as DBPatient,
    Provider as DBProvider,
    Service as DBService,
    Appointment as DBAppointment,
    AuditLog as DBAuditLog,
)

# Keep legacy JSON path for backward-compatible seeding and _crm_data access
CRM_JSON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures", "crm.json"))

# Legacy in-memory cache — populated by load_crm() for backward compat
# Used only by code that accesses _crm_data directly (e.g., /api/crm endpoint)
_crm_data: Dict[str, Any] = {}


def _row_to_dict(row) -> Dict[str, Any]:
    """Converts a SQLAlchemy row to a plain dict."""
    if row is None:
        return None
    d = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    # Remove SQLAlchemy internal fields
    d.pop("created_at", None)
    return d


def _db():
    """Gets a new database session."""
    return SessionLocal()


def _is_db_available() -> bool:
    """Check if the database has been seeded."""
    try:
        db = _db()
        count = db.query(DBProvider).count()
        db.close()
        return count > 0
    except Exception:
        return False


# ---- Legacy JSON loader (kept for backward compat) ----

def load_crm(file_path: str = CRM_JSON_PATH) -> None:
    """Loads CRM data into the legacy _crm_data dict for backward compat."""
    global _crm_data
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                _crm_data = json.load(f)
        except Exception:
            _crm_data = {}


# ---- Patient queries ----

def get_patient_by_id(pat_id: str) -> Optional[Dict[str, Any]]:
    if not pat_id:
        return None
    try:
        db = _db()
        row = db.query(DBPatient).filter(DBPatient.id == pat_id).first()
        db.close()
        return _row_to_dict(row)
    except Exception:
        # Fallback to legacy
        for p in _crm_data.get("patients", []):
            if p["id"] == pat_id:
                return p
        return None


def get_patient_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    if not phone:
        return None
    clean_phone = re.sub(r"[^\d+]", "", phone)
    try:
        db = _db()
        # Try exact match
        row = db.query(DBPatient).filter(DBPatient.phone != None).all()
        db.close()
        for r in row:
            r_phone = re.sub(r"[^\d+]", "", r.phone) if r.phone else ""
            if r_phone == clean_phone:
                return _row_to_dict(r)
        # Suffix match fallback
        suffix = clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone
        for r in row:
            r_phone = re.sub(r"[^\d+]", "", r.phone) if r.phone else ""
            if r_phone.endswith(suffix):
                return _row_to_dict(r)
        return None
    except Exception:
        return None


def get_patient_by_email(email: str) -> Optional[Dict[str, Any]]:
    if not email:
        return None
    try:
        db = _db()
        row = db.query(DBPatient).filter(
            DBPatient.email.ilike(email.strip())
        ).first()
        db.close()
        return _row_to_dict(row)
    except Exception:
        return None


def find_patient_by_name(name_str: str) -> Optional[Dict[str, Any]]:
    """Resolves patient name or partial name to a patient record."""
    if not name_str:
        return None
    name_clean = name_str.lower().strip()
    try:
        db = _db()
        patients = db.query(DBPatient).all()
        db.close()
        for p in patients:
            if name_clean in p.name.lower():
                return _row_to_dict(p)
        return None
    except Exception:
        # Fallback to legacy
        for p in _crm_data.get("patients", []):
            if name_clean in p["name"].lower():
                return p
        return None


# ---- Provider queries ----

def get_provider_by_id(prov_id: str) -> Optional[Dict[str, Any]]:
    if not prov_id:
        return None
    try:
        db = _db()
        row = db.query(DBProvider).filter(DBProvider.id == prov_id).first()
        db.close()
        return _row_to_dict(row)
    except Exception:
        return None


def find_provider_by_name(name_str: str) -> Optional[Dict[str, Any]]:
    """Resolves provider name or partial name to a provider record."""
    if not name_str:
        return None
    name_clean = name_str.lower().strip()
    try:
        db = _db()
        providers = db.query(DBProvider).all()
        db.close()
        
        # Try direct substring match
        for prov in providers:
            if name_clean in prov.name.lower():
                return _row_to_dict(prov)
        
        # Try matching individual name parts
        name_parts = re.findall(r"\w+", name_clean)
        for part in name_parts:
            if part in ["dr", "md", "rn", "le"]:
                continue
            for prov in providers:
                if part in prov.name.lower():
                    return _row_to_dict(prov)
        return None
    except Exception:
        return None


def get_all_providers() -> List[Dict[str, Any]]:
    try:
        db = _db()
        rows = db.query(DBProvider).all()
        db.close()
        return [_row_to_dict(r) for r in rows]
    except Exception:
        return _crm_data.get("providers", [])


# ---- Service queries ----

def get_service_by_id(svc_id: str) -> Optional[Dict[str, Any]]:
    if not svc_id:
        return None
    try:
        db = _db()
        row = db.query(DBService).filter(DBService.id == svc_id).first()
        db.close()
        return _row_to_dict(row)
    except Exception:
        return None


def find_service_by_name(name_str: str) -> Optional[Dict[str, Any]]:
    """Finds a service by name, synonym, or specialty match."""
    if not name_str:
        return None
    name_clean = name_str.lower().strip().replace("-", " ")
    
    try:
        db = _db()
        services = db.query(DBService).all()
        db.close()
        services_dict = {s.id: _row_to_dict(s) for s in services}
    except Exception:
        services_dict = {s["id"]: s for s in _crm_data.get("services", [])}
    
    # Direct exact/substring matches
    for svc in services_dict.values():
        if name_clean == svc["name"].lower().replace("-", " "):
            return svc
    for svc in services_dict.values():
        if name_clean in svc["name"].lower().replace("-", " "):
            return svc

    # Match synonyms
    synonyms = {
        "filler": "svc_filler_lip",
        "lip filler": "svc_filler_lip",
        "botox": "svc_botox",
        "peel": "svc_peel",
        "chemical peel": "svc_peel",
        "laser": "svc_laser_small",
        "hydrafacial": "svc_hydra",
        "facial": "svc_hydra",
        "microneedling": "svc_microneedle",
        "consult": "svc_consult",
        "consultation": "svc_consult",
        "new patient": "svc_consult",
        "lip touchup": "svc_lip_touch",
        "lip touch up": "svc_lip_touch",
        "filler dissolve": "svc_dissolve",
        "dissolve filler": "svc_dissolve",
        "undereye": "svc_filler_undereye",
        "cheek": "svc_filler_cheek",
        "chin": "svc_filler_jaw",
        "jaw": "svc_filler_jaw",
        "relleno de labios": "svc_filler_lip",
        "retoque de labios": "svc_lip_touch",
        "retoque de relleno de labios": "svc_lip_touch",
        "retoque de relleno": "svc_lip_touch",
        "relleno": "svc_filler_lip",
        "retoque": "svc_lip_touch",
    }
    
    for k in sorted(synonyms.keys(), key=len, reverse=True):
        v = synonyms[k]
        if k in name_clean or name_clean in k:
            return services_dict.get(v)
    return None


def get_all_services() -> List[Dict[str, Any]]:
    try:
        db = _db()
        rows = db.query(DBService).all()
        db.close()
        return [_row_to_dict(r) for r in rows]
    except Exception:
        return _crm_data.get("services", [])


# ---- Appointment queries ----

def get_appointments_for_provider(prov_id: str) -> List[Dict[str, Any]]:
    try:
        db = _db()
        rows = db.query(DBAppointment).filter(
            DBAppointment.provider_id == prov_id
        ).order_by(DBAppointment.start).all()
        db.close()
        return [_row_to_dict(r) for r in rows]
    except Exception:
        return []


def get_appointments_for_patient(patient_id: str) -> List[Dict[str, Any]]:
    try:
        db = _db()
        rows = db.query(DBAppointment).filter(
            DBAppointment.patient_id == patient_id
        ).order_by(DBAppointment.start).all()
        db.close()
        return [_row_to_dict(r) for r in rows]
    except Exception:
        return []


# ---- Mutation functions ----

def add_appointment(
    patient_id: str,
    provider_id: str,
    service_id: str,
    start_time: str,
    duration_minutes: int,
    price_usd: float,
    status: str = "booked"
) -> Dict[str, Any]:
    from app.calendar_math import parse_iso_datetime
    
    start_dt = parse_iso_datetime(start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    
    try:
        db = _db()
        # Generate next ID
        from sqlalchemy import func
        max_row = db.query(func.max(DBAppointment.id)).scalar()
        if max_row:
            m = re.match(r"appt_(\d+)", max_row)
            max_id = int(m.group(1)) if m else 0
        else:
            max_id = 0
        new_id = f"appt_{max_id + 1}"
        
        new_appt = DBAppointment(
            id=new_id,
            patient_id=patient_id,
            provider_id=provider_id,
            service_id=service_id,
            start=start_time,
            end=end_dt.isoformat(),
            duration=duration_minutes,
            price=price_usd,
            status=status,
        )
        db.add(new_appt)
        db.commit()
        result = _row_to_dict(new_appt)
        db.close()
        return result
    except Exception as e:
        print(f"[CRM] add_appointment error: {e}")
        # Fallback — should not happen in production
        return {
            "id": f"appt_fallback_{datetime.now().timestamp():.0f}",
            "patient_id": patient_id,
            "provider_id": provider_id,
            "service_id": service_id,
            "start": start_time,
            "end": end_dt.isoformat(),
            "duration": duration_minutes,
            "price": price_usd,
            "status": status,
        }


def reschedule_appointment(
    appt_id: str,
    start_time: str,
    provider_id: str = None
) -> Optional[Dict[str, Any]]:
    try:
        db = _db()
        target = db.query(DBAppointment).filter(DBAppointment.id == appt_id).first()
        if not target:
            db.close()
            return None
        
        target.status = "rescheduled"
        db.commit()
        
        old_data = _row_to_dict(target)
        db.close()
        
        new_appt = add_appointment(
            patient_id=old_data["patient_id"],
            provider_id=provider_id or old_data["provider_id"],
            service_id=old_data["service_id"],
            start_time=start_time,
            duration_minutes=old_data["duration"],
            price_usd=old_data["price"],
            status="booked",
        )
        return new_appt
    except Exception as e:
        print(f"[CRM] reschedule_appointment error: {e}")
        return None


def add_audit_log(
    patient_id: str,
    action: str,
    details: Dict[str, Any]
) -> None:
    """Writes an entry to the database audit trail."""
    try:
        db = _db()
        db.add(DBAuditLog(
            patient_id=patient_id,
            action=action,
            details=details,
        ))
        db.commit()
        db.close()
    except Exception as e:
        print(f"[CRM] add_audit_log error: {e}")


# ---- Initialization ----
# Load legacy JSON for backward compat (used by /api/crm endpoint)
load_crm()
