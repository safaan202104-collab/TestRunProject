from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Any, Optional
from app import crm_indexer
from app import calendar_math
from app import interval_tree

LA_TZ = pytz.timezone("America/Los_Angeles")

from app.dynamic_config import get_config_val


def score_utilization(provider_id: str, slot_start: datetime, slot_end: datetime) -> float:
    """Scores a slot based on proximity to other appointments (favoring back-to-back)."""
    appointments = crm_indexer.get_appointments_for_provider(provider_id)
    
    weight_back_to_back = get_config_val("weight_back_to_back")
    weight_small_gap = get_config_val("weight_small_gap")
    
    score = 0.0
    for appt in appointments:
        if appt.get("status") == "cancelled":
            continue
            
        appt_start = calendar_math.parse_iso_datetime(appt["start"])
        if appt.get("end"):
            appt_end = calendar_math.parse_iso_datetime(appt["end"])
        else:
            duration = appt.get("duration", 30)
            appt_end = appt_start + timedelta(minutes=duration)
        
        # We only look at appointments on the same day
        if appt_start.date() != slot_start.date():
            continue
            
        # Check back-to-back (0 minutes gap)
        if slot_start == appt_end or slot_end == appt_start:
            score += weight_back_to_back
        # Check small gap (less than or equal to 30 minutes)
        elif abs((slot_start - appt_end).total_seconds()) <= 1800 or abs((appt_start - slot_end).total_seconds()) <= 1800:
            score += weight_small_gap
            
    return score

def find_candidate_slots(
    service: Any, # Can be Dict or Service domain object
    requested_provider: Optional[Any], # Can be Dict or Provider domain object
    patient: Optional[Any], # Can be Dict or Patient domain object
    start_search: datetime,
    end_search: datetime,
    now_dt: datetime
) -> List[Dict[str, Any]]:
    """Generates all available candidate slots for the service within the search range."""
    # Convert domain models to dict if needed to maintain backward compatibility
    svc_id = service.id if hasattr(service, "id") else service["id"]
    svc_name = service.name if hasattr(service, "name") else service["name"]
    duration = service.duration_minutes if hasattr(service, "duration_minutes") else service["duration_minutes"]
    price_usd = service.price_usd if hasattr(service, "price_usd") else service["price_usd"]
    required_spec = service.specialties_required[0] if hasattr(service, "specialties_required") and service.specialties_required else (service.get("required_specialty") if isinstance(service, dict) else None)
    
    # Determine which providers can perform this service
    eligible_providers = []
    if requested_provider:
        # User requested a specific provider
        eligible_providers = [requested_provider]
    else:
        # Match by specialty
        for prov in crm_indexer.get_all_providers():
            prov_specs = prov.specialties if hasattr(prov, "specialties") else prov.get("specialties", [])
            if required_spec in prov_specs:
                eligible_providers.append(prov)
                
    candidates = []
    
    weight_preferred_provider = get_config_val("weight_preferred_provider")
    weight_soonest_penalty = get_config_val("weight_soonest_penalty")
    limit = get_config_val("alternative_slot_count")
    
    # Time stepping: check slots every 15 minutes
    step_minutes = 15
    
    # VIP preference & preferred provider weights
    preferred_prov_id = None
    if patient:
        if hasattr(patient, "preferred_provider_id"):
            preferred_prov_id = patient.preferred_provider_id
        else:
            preferred_prov_id = patient.get("preferred_provider_id")
            
    for provider in eligible_providers:
        prov_id = provider.id if hasattr(provider, "id") else provider["id"]
        prov_name = provider.name if hasattr(provider, "name") else provider["name"]
        
        # Working hours check
        hours = provider.working_hours if hasattr(provider, "working_hours") else provider.get("hours", {})
        
        current_time = start_search
        # Step through the search window
        while current_time + timedelta(minutes=duration) <= end_search:
            slot_start = current_time
            slot_end = current_time + timedelta(minutes=duration)
            
            # Must be in the future relative to now
            if slot_start >= now_dt:
                # Must be within working hours
                if calendar_math.is_within_working_hours(slot_start, duration, hours):
                    # Must not overlap with other active appointments
                    if not interval_tree.has_overlap(prov_id, slot_start, slot_end):
                        # Calculate scores
                        preference_score = 0.0
                        if preferred_prov_id == prov_id:
                          preference_score = weight_preferred_provider
                            
                        utilization_score = score_utilization(prov_id, slot_start, slot_end)
                        
                        days_diff = (slot_start.date() - now_dt.date()).days
                        recency_penalty = days_diff * weight_soonest_penalty
                        
                        total_score = preference_score + utilization_score - recency_penalty
                        
                        candidates.append({
                            "provider_id": prov_id,
                            "provider_name": prov_name,
                            "service_id": svc_id,
                            "service_name": svc_name,
                            "start_time": calendar_math.format_iso_datetime(slot_start),
                            "duration_minutes": duration,
                            "price_usd": price_usd,
                            "score": total_score,
                            "suitability_metrics": {
                                "preference_score": preference_score,
                                "utilization_score": utilization_score,
                                "recency_penalty": recency_penalty
                            }
                        })
                        
            current_time += timedelta(minutes=step_minutes)
            
    # Sort candidates by score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]
