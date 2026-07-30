from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app import crm_indexer
from app import calendar_math

def has_overlap(provider_id: str, slot_start: datetime, slot_end: datetime) -> bool:
    """Checks if the slot overlaps with any active (non-cancelled) appointment for the provider."""
    appointments = crm_indexer.get_appointments_for_provider(provider_id)
    
    for appt in appointments:
        if appt.get("status") == "cancelled":
            continue
            
        appt_start = calendar_math.parse_iso_datetime(appt["start"])
        if appt.get("end"):
            appt_end = calendar_math.parse_iso_datetime(appt["end"])
        else:
            duration = appt.get("duration", 30)
            appt_end = appt_start + timedelta(minutes=duration)
        
        # Check overlap: slot starts before appt ends, and appt starts before slot ends
        if slot_start < appt_end and appt_start < slot_end:
            return True
            
    return False

def get_overlapping_appointment(provider_id: str, slot_start: datetime, slot_end: datetime) -> Optional[Dict[str, Any]]:
    """Returns the overlapping appointment, if one exists."""
    appointments = crm_indexer.get_appointments_for_provider(provider_id)
    
    for appt in appointments:
        if appt.get("status") == "cancelled":
            continue
            
        appt_start = calendar_math.parse_iso_datetime(appt["start"])
        if appt.get("end"):
            appt_end = calendar_math.parse_iso_datetime(appt["end"])
        else:
            duration = appt.get("duration", 30)
            appt_end = appt_start + timedelta(minutes=duration)
        
        if slot_start < appt_end and appt_start < slot_end:
            return appt
            
    return None
