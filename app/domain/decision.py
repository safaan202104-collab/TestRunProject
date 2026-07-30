from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.domain.models import Patient, Provider, Service, CandidateSlot
from app.domain.context import RequestContext, EventStream

class DecisionContext(BaseModel):
    # Context & Audit Trail
    request_context: RequestContext = Field(default_factory=RequestContext)
    event_stream: EventStream = Field(default_factory=EventStream)
    
    # Inbound Data
    channel: str
    from_address: str
    message_body: str
    now_string: str
    
    # Extracted Entities & Resolved Domain Objects
    patient: Optional[Patient] = None
    service: Optional[Service] = None
    provider: Optional[Provider] = None
    
    extracted_service_name: Optional[str] = None
    extracted_provider_name: Optional[str] = None
    extracted_time_text: Optional[str] = None
    resolved_time_boundary: Optional[Dict[str, Any]] = None # start/end range
    
    # Pipeline Execution Decisions
    outcome: str = "no_action" # "propose_booking" | "ask_clarification" | "escalate_to_human" | "no_action"
    proposed_slot: Optional[CandidateSlot] = None
    alternative_slots: List[CandidateSlot] = Field(default_factory=list)
    rationale: Optional[str] = None
    question: Optional[str] = None
    reason: Optional[str] = None
    
    violated_rules: List[str] = Field(default_factory=list)
    confidence_score: float = 1.0
    
    def add_violated_rule(self, rule_name: str):
        if rule_name not in self.violated_rules:
            self.violated_rules.append(rule_name)
