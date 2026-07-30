from typing import Dict, Any, Optional
from app.client import get_llm_client

def generate_rationale(
    patient: Optional[Dict[str, Any]],
    provider: Dict[str, Any],
    service: Dict[str, Any],
    slot_start_str: str,
    original_message: str
) -> str:
    """Generates a one-sentence rationale explaining to the front desk staff why this slot was proposed."""
    patient_name = patient["name"] if patient else "the patient"
    pref_prov_id = patient.get("preferred_provider_id") if patient else None
    
    # Check if this matches preferred provider
    pref_match_str = ""
    if pref_prov_id == provider["id"]:
        pref_match_str = f" This matches their preferred provider, {provider['name']}."
        
    system_prompt = (
        "You are a front desk coordinator at a medical-aesthetic practice.\n"
        "Draft a single, concise sentence explaining to the clinic staff why a proposed appointment slot makes sense for a patient.\n"
        "Keep it highly professional, informational, and to-point (under 25 words).\n"
        "Examples:\n"
        "- 'Sarah requested next Tuesday afternoon; Dr. Chang has a slot at 2:00 PM matching her preferred provider preference.'\n"
        "- 'Priya requested botox this week; Dr. Reyes is available Friday morning at 10:00 AM.'\n"
        "Output ONLY the rationale sentence. Do not add markdown or intro text."
    )
    
    prompt = (
        f"Context:\n"
        f"- Patient: {patient_name}\n"
        f"- Selected Service: {service['name']}\n"
        f"- Proposed Provider: {provider['name']}{pref_match_str}\n"
        f"- Proposed Start Time: {slot_start_str}\n"
        f"- Patient Message: \"{original_message}\"\n"
    )
    
    client = get_llm_client()
    result = client.chat_completion(
        system_prompt=system_prompt,
        prompt=prompt,
        temperature=0.0,
        max_tokens=100
    )
    
    return result.strip().strip('"').strip("'")
