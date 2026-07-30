"""
SQLAlchemy ORM models for all MyGlowTheory entities.
Maps directly to the existing fixture schema while adding production features
like proper status enums, timestamps, and foreign keys.
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base


# ---------- Enums ----------

class AppointmentStatus(str, enum.Enum):
    pending = "pending"
    booked = "booked"
    confirmed = "confirmed"
    rescheduled = "rescheduled"
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"


# ---------- Models ----------

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    marketing_status = Column(String, nullable=True)
    tags = Column(JSON, default=list)
    preferred_provider_id = Column(String, ForeignKey("providers.id"), nullable=True)
    do_not_book = Column(Boolean, default=False)
    do_not_book_reason = Column(Text, nullable=True)
    vip = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    clinical_notes = Column(Text, nullable=True)
    clinic_id = Column(String, default="clinic_default", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="patient")


class Provider(Base):
    __tablename__ = "providers"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    specialties = Column(JSON, default=list)
    hours = Column(JSON, default=dict)  # Working hours schedule
    clinic_id = Column(String, default="clinic_default", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="provider")


class Service(Base):
    __tablename__ = "services"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    price_usd = Column(Float, nullable=False)
    required_specialty = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=False, index=True)
    service_id = Column(String, ForeignKey("services.id"), nullable=False)
    start = Column(String, nullable=False)  # ISO-8601 datetime string
    end = Column(String, nullable=True)     # ISO-8601 datetime string
    duration = Column(Integer, nullable=False)
    price = Column(Float, nullable=False, default=0.0)
    status = Column(String, default="booked", index=True)
    workflow_stage = Column(String, default="operator_review")
    override_notes = Column(Text, nullable=True)
    clinic_id = Column(String, default="clinic_default", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    provider = relationship("Provider", back_populates="appointments")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    patient_id = Column(String, nullable=True)
    action = Column(String, nullable=False, index=True)
    details = Column(JSON, default=dict)


class HumanOverride(Base):
    __tablename__ = "human_overrides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    patient_id = Column(String, nullable=True)
    override_reason = Column(Text, nullable=True)
    original_ai_proposal = Column(JSON, default=dict)
    final_human_choice = Column(JSON, default=dict)
    difference = Column(JSON, default=dict)
    category = Column(String, default="manual_override")


class RequestTelemetry(Base):
    __tablename__ = "request_telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    outcome = Column(String, nullable=True)
    confidence_score = Column(Float, default=1.0)
    latency_ms = Column(Float, default=0.0)
    metadata_json = Column(JSON, default=dict)  # prompt_tokens, completion_tokens, cost, etc.


class SystemConfig(Base):
    __tablename__ = "system_config"

    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String, nullable=False, index=True)
    model_used = Column(String, nullable=False)
    tool_chain = Column(JSON, default=list)
    latency_ms = Column(Float, default=0.0)
    cost_usd = Column(Float, default=0.0)
    eval_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
