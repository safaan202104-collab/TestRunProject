"""
Analytics Helper — Database-backed version.
Logs and aggregates telemetry and override analytics from SQL tables.
"""
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import func
from app.database import SessionLocal
from app.db_models import RequestTelemetry, HumanOverride

def log_request_telemetry(data: Dict[str, Any]) -> None:
    """Logs request metadata, latency, tokens, cost, and outcome to database."""
    db = SessionLocal()
    try:
        # Convert datetime key if it's already string or iso format
        timestamp = datetime.utcnow()
        telemetry = RequestTelemetry(
            timestamp=timestamp,
            outcome=data.get("outcome"),
            confidence_score=data.get("confidence_score", 1.0),
            latency_ms=data.get("latency_ms", 0.0),
            metadata_json=data.get("metadata", {})
        )
        db.add(telemetry)
        db.commit()
    except Exception as e:
        print(f"[ANALYTICS] Failed to log telemetry: {e}")
        db.rollback()
    finally:
        db.close()

def log_human_override(data: Dict[str, Any]) -> None:
    """Logs a human override event to the database."""
    db = SessionLocal()
    try:
        override = HumanOverride(
            timestamp=datetime.utcnow(),
            patient_id=data.get("patient_id"),
            override_reason=data.get("override_reason"),
            original_ai_proposal=data.get("original_ai_proposal", {}),
            final_human_choice=data.get("final_human_choice", {}),
            difference=data.get("difference", {}),
            category=data.get("category", "manual_override")
        )
        db.add(override)
        db.commit()
    except Exception as e:
        print(f"[ANALYTICS] Failed to log override: {e}")
        db.rollback()
    finally:
        db.close()

def get_aggregated_analytics() -> Dict[str, Any]:
    """Queries DB tables and computes performance & quality metrics."""
    db = SessionLocal()
    try:
        # Get all telemetry
        telemetry_rows = db.query(RequestTelemetry).all()
        # Get all overrides
        override_rows = db.query(HumanOverride).all()
        
        total_requests = len(telemetry_rows)
        total_latency = sum(t.latency_ms for t in telemetry_rows)
        total_confidence = sum(t.confidence_score for t in telemetry_rows)
        
        total_cost = 0.0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        fallback_count = 0
        outcome_counts = {
            "propose_booking": 0,
            "ask_clarification": 0,
            "escalate_to_human": 0,
            "no_action": 0
        }
        
        for t in telemetry_rows:
            meta = t.metadata_json or {}
            total_cost += meta.get("estimated_cost_usd", 0.0)
            total_prompt_tokens += meta.get("prompt_tokens", 0)
            total_completion_tokens += meta.get("completion_tokens", 0)
            if meta.get("fallback_used"):
                fallback_count += 1
                
            outcome = t.outcome or "no_action"
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
            
        avg_latency = total_latency / total_requests if total_requests > 0 else 0.0
        avg_confidence = total_confidence / total_requests if total_requests > 0 else 1.0
        fallback_rate = (fallback_count / total_requests * 100) if total_requests > 0 else 0.0
        
        total_overrides = len(override_rows)
        provider_overrides = 0
        time_overrides = 0
        reasons = []
        raw_overrides = []
        
        # We sort by timestamp desc, take last 10
        sorted_overrides = sorted(override_rows, key=lambda x: x.timestamp or datetime.min, reverse=True)
        
        for o in override_rows:
            reason_text = o.override_reason or ""
            if reason_text:
                reasons.append(reason_text)
                
            diff = o.difference or {}
            if "provider_changed" in diff:
                provider_overrides += 1
            if "start_time_changed" in diff:
                time_overrides += 1
                
        # Format last 10 overrides for UI
        for o in sorted_overrides[:10]:
            raw_overrides.append({
                "timestamp": o.timestamp.isoformat() if o.timestamp else datetime.utcnow().isoformat(),
                "patient_id": o.patient_id,
                "override_reason": o.override_reason,
                "original_ai_proposal": o.original_ai_proposal,
                "final_human_choice": o.final_human_choice,
                "difference": o.difference,
                "category": o.category
            })
            
        override_rate = (total_overrides / total_requests * 100) if total_requests > 0 else 0.0
        
        # Calculate top reasons
        reason_freq = {}
        for r in reasons:
            reason_freq[r] = reason_freq.get(r, 0) + 1
        sorted_reasons = sorted(reason_freq.items(), key=lambda x: x[1], reverse=True)
        top_reasons = [{"reason": item[0], "count": item[1]} for item in sorted_reasons[:5]]
        
        return {
            "telemetry": {
                "total_requests": total_requests,
                "avg_latency_ms": round(avg_latency, 1),
                "avg_confidence": round(avg_confidence * 100, 1),
                "total_cost_usd": round(total_cost, 4),
                "total_tokens": total_prompt_tokens + total_completion_tokens,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "fallback_rate_pct": round(fallback_rate, 1),
                "outcome_distribution": outcome_counts
            },
            "overrides": {
                "total_overrides": total_overrides,
                "provider_overrides": provider_overrides,
                "time_overrides": time_overrides,
                "override_rate_pct": round(override_rate, 1),
                "common_reasons": top_reasons,
                "raw_overrides": raw_overrides
            }
        }
    finally:
        db.close()
