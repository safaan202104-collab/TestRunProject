from pydantic import BaseModel, Field
from typing import Optional, List

class MessageModel(BaseModel):
    channel: str
    from_address: str = Field(..., alias="from")
    body: str

    class Config:
        populate_by_name = True

class DecideRequest(BaseModel):
    message: MessageModel
    patient_id: Optional[str] = None
    now: str

class BookingProposal(BaseModel):
    provider_id: str
    provider_name: str
    service_id: str
    service_name: str
    start_time: str
    duration_minutes: int
    price_usd: float
    rescheduled_appointment_id: Optional[str] = None

class DecideResponse(BaseModel):
    outcome: str # "propose_booking" | "ask_clarification" | "escalate_to_human" | "no_action"
    booking_proposal: Optional[BookingProposal] = None
    rationale: Optional[str] = None # For propose_booking
    question: Optional[str] = None  # For ask_clarification
    reason: Optional[str] = None    # For escalate_to_human
    
    # Observability & Front-end Explainability extensions
    alternative_proposals: Optional[List[BookingProposal]] = None
    confidence_score: Optional[float] = None
    violated_rules: Optional[List[str]] = None
    decision_stages: Optional[List[str]] = None
    event_stream: Optional[List[dict]] = None
    metadata: Optional[dict] = None

    class Config:
        populate_by_name = True

class UIContext(BaseModel):
    selected_patient_id: Optional[str] = None
    selected_provider_id: Optional[str] = None
    selected_appointment_id: Optional[str] = None
    current_message_body: Optional[str] = None
    current_decision_outcome: Optional[str] = None
    current_decision_confidence: Optional[float] = None
    current_decision_violated_rules: Optional[List[str]] = None
    operator_role: Optional[str] = None
    current_view: Optional[str] = None
    clinic_id: Optional[str] = "clinic_default"

class AskRequest(BaseModel):
    context: dict
    question: str
    session_id: Optional[str] = None
    ui_context: Optional[UIContext] = None

class LiveMessageRequest(BaseModel):
    message: str
    patient_id: Optional[str] = None
    channel: str = "sms"

class SimulateRequest(BaseModel):
    message: str
    channel: str = "sms"
    language: str = "English"
    scenario: str = "Custom"
    patient_id: Optional[str] = None
