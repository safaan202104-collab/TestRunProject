from typing import Dict, Any, Optional, Tuple, List
from app import crm_indexer

def validate_business_rules(
    patient: Optional[Dict[str, Any]],
    provider: Optional[Dict[str, Any]],
    service: Optional[Dict[str, Any]],
    original_message: str
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Applies the clinic's iron business rules on resolved entities.
    
    Returns:
        (outcome, payload)
        If a rule triggers an early decision, returns (outcome, decision_dict).
        Otherwise returns (None, None).
    """
    # 1. Rule 1: Do Not Book Check
    if patient and patient.get("do_not_book"):
        reason_text = patient.get("do_not_book_reason") or "Patient account flagged 'do_not_book'."
        decision = {
            "outcome": "escalate_to_human",
            "booking_proposal": None,
            "reason": f"Patient is flagged as Do-Not-Book. Reason: {reason_text}"
        }
        return "escalate_to_human", decision

    # 2. Rule 2: Provider Specialty Check
    if provider and service:
        required_spec = service.get("required_specialty")
        provider_specs = provider.get("specialties", [])
        
        if required_spec and required_spec not in provider_specs:
            # Find alternative providers who DO have this specialty
            alts = []
            for other_prov in crm_indexer.get_all_providers():
                if required_spec in other_prov.get("specialties", []):
                    alts.append(other_prov["name"])
            
            alt_str = ", or ".join(alts) if alts else "none"
            question = (
                f"{provider['name']} does not perform {service['name']}. "
                f"Would you like to book with an alternative provider who does (such as {alt_str})?"
            )
            decision = {
                "outcome": "ask_clarification",
                "question": question
            }
            return "ask_clarification", decision
            
    return None, None
