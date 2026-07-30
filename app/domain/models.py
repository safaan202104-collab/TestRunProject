from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class Patient(BaseModel):
    id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    marketing_status: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    preferred_provider_id: Optional[str] = None
    do_not_book: bool = False
    vip: bool = False
    notes: Optional[str] = None

class Provider(BaseModel):
    id: str
    name: str
    specialties: List[str] = Field(default_factory=list)
    working_hours: Dict[str, Any] = Field(default_factory=dict)

class Service(BaseModel):
    id: str
    name: str
    duration_minutes: int
    price_usd: float
    specialties_required: List[str] = Field(default_factory=list)

class Appointment(BaseModel):
    id: str
    patient_id: str
    provider_id: str
    service_id: str
    start: str
    duration: int
    price: float
    status: str = "booked"  # "booked" | "cancelled" | "completed"

class CandidateSlot(BaseModel):
    provider_id: str
    provider_name: str
    service_id: str
    service_name: str
    start_time: str
    duration_minutes: int
    price_usd: float
    rescheduled_appointment_id: Optional[str] = None
    score: float = 0.0  # Ranking score (computed dynamically)
    suitability_metrics: Dict[str, Any] = Field(default_factory=dict) # Details of scores
