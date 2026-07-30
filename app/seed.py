"""
Fixture seeder: imports data from fixtures/crm.json into the database.
Idempotent — skips records that already exist.
Usage: python -m app.seed
"""
import json
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine, SessionLocal, Base
from app.db_models import Patient, Provider, Service, Appointment, SystemConfig

CRM_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures", "crm.json"))


def seed_database():
    """Seeds the database from fixtures/crm.json."""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    if not os.path.exists(CRM_PATH):
        print(f"[SEED] CRM fixture not found at {CRM_PATH}")
        return

    with open(CRM_PATH, "r", encoding="utf-8") as f:
        crm_data = json.load(f)

    db = SessionLocal()
    try:
        # Seed Providers
        providers = crm_data.get("providers", [])
        existing_prov_ids = {p.id for p in db.query(Provider.id).all()}
        new_providers = 0
        for prov in providers:
            if prov["id"] not in existing_prov_ids:
                db.add(Provider(
                    id=prov["id"],
                    name=prov["name"],
                    specialties=prov.get("specialties", []),
                    hours=prov.get("hours", {}),
                ))
                new_providers += 1
        db.flush()
        print(f"[SEED] Providers: {new_providers} new, {len(existing_prov_ids)} existing")

        # Seed Services
        services = crm_data.get("services", [])
        existing_svc_ids = {s.id for s in db.query(Service.id).all()}
        new_services = 0
        for svc in services:
            if svc["id"] not in existing_svc_ids:
                db.add(Service(
                    id=svc["id"],
                    name=svc["name"],
                    duration_minutes=svc["duration_minutes"],
                    price_usd=svc["price_usd"],
                    required_specialty=svc.get("required_specialty"),
                ))
                new_services += 1
        db.flush()
        print(f"[SEED] Services: {new_services} new, {len(existing_svc_ids)} existing")

        # Seed Patients
        patients = crm_data.get("patients", [])
        existing_pat_ids = {p.id for p in db.query(Patient.id).all()}
        new_patients = 0
        for pat in patients:
            if pat["id"] not in existing_pat_ids:
                db.add(Patient(
                    id=pat["id"],
                    name=pat["name"],
                    phone=pat.get("phone"),
                    email=pat.get("email"),
                    marketing_status=pat.get("marketing_status"),
                    tags=pat.get("tags", []),
                    preferred_provider_id=pat.get("preferred_provider_id"),
                    do_not_book=pat.get("do_not_book", False),
                    do_not_book_reason=pat.get("do_not_book_reason"),
                    vip=pat.get("vip", False),
                    notes=pat.get("notes"),
                    clinical_notes=pat.get("clinical_notes"),
                ))
                new_patients += 1
        db.flush()
        print(f"[SEED] Patients: {new_patients} new, {len(existing_pat_ids)} existing")

        # Seed Appointments
        appointments = crm_data.get("appointments", [])
        existing_appt_ids = {a.id for a in db.query(Appointment.id).all()}
        new_appts = 0
        for appt in appointments:
            if appt["id"] not in existing_appt_ids:
                db.add(Appointment(
                    id=appt["id"],
                    patient_id=appt["patient_id"],
                    provider_id=appt["provider_id"],
                    service_id=appt["service_id"],
                    start=appt["start"],
                    end=appt.get("end"),
                    duration=appt.get("duration", 30),
                    price=appt.get("price", 0.0),
                    status=appt.get("status", "booked"),
                ))
                new_appts += 1
        db.flush()
        print(f"[SEED] Appointments: {new_appts} new, {len(existing_appt_ids)} existing")

        # Seed default system config
        from app.dynamic_config import DEFAULT_CONFIG
        existing_keys = {c.key for c in db.query(SystemConfig.key).all()}
        new_configs = 0
        for key, value in DEFAULT_CONFIG.items():
            if key not in existing_keys:
                db.add(SystemConfig(key=key, value=value))
                new_configs += 1
        print(f"[SEED] Config: {new_configs} new, {len(existing_keys)} existing")

        db.commit()
        print("[SEED] Database seeded successfully!")

    except Exception as e:
        db.rollback()
        print(f"[SEED] Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
