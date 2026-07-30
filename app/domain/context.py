import time
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid

class RequestContext(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    user: Optional[str] = "receptionist"
    session: Optional[str] = None
    model: Optional[str] = "llama-3.3-70b-versatile"
    api_provider: Optional[str] = "Groq"
    start_time_ns: int = Field(default_factory=time.perf_counter_ns)
    
    # Token count & cost metrics
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    retries: int = 0
    fallback_used: bool = False
    
    def elapsed_ms(self) -> float:
        return (time.perf_counter_ns() - self.start_time_ns) / 1_000_000.0

class StageEvent(BaseModel):
    stage_name: str
    status: str = "started" # "started" | "finished" | "failed"
    started_at: float = Field(default_factory=time.time)
    finished_at: Optional[float] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def finish(self, metadata: Optional[Dict[str, Any]] = None):
        self.finished_at = time.time()
        self.duration_ms = (self.finished_at - self.started_at) * 1000.0
        self.status = "finished"
        if metadata:
            self.metadata.update(metadata)

class EventStream(BaseModel):
    events: List[StageEvent] = Field(default_factory=list)
    
    def start_stage(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> StageEvent:
        event = StageEvent(stage_name=name, metadata=metadata or {})
        self.events.append(event)
        return event
        
    def finish_stage(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        for event in reversed(self.events):
            if event.stage_name == name and event.status == "started":
                event.finish(metadata)
                break
