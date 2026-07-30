import json
import re
from typing import Dict, Any, Optional
from app.client import get_llm_client

def extract_entities(message_body: str) -> Dict[str, Optional[str]]:
    """Extracts scheduling entities (service, provider, and time query) from a message."""
    if not message_body:
        return {
            "service_query": None,
            "provider_query": None,
            "time_boundary_query": None
        }
        
    system_prompt = (
        "You are a precise clinical scheduler assistant that extracts structured parameters from natural language requests.\n"
        "Your task is to extract three fields from the patient's message:\n\n"
        "1. service_query: The name/description of the treatment/service the patient is asking to book "
        "(e.g., 'lip filler touch-up', 'under-eye filler', 'HydraFacial', 'botox').\n"
        "2. provider_query: The name of the specific provider requested (e.g., 'Jordan', 'Dr. Reyes', 'Amelia'). "
        "If the patient does not request a specific person, return null.\n"
        "3. time_boundary_query: The exact text describing the desired date, day, time, or general range they want "
        "(e.g., 'sometime next Tuesday afternoon', 'Thursday at 4:30pm', 'this Saturday morning').\n\n"
        "Format your response as a valid JSON object with exactly these keys:\n"
        "{\n"
        "  \"service_query\": \"string or null\",\n"
        "  \"provider_query\": \"string or null\",\n"
        "  \"time_boundary_query\": \"string or null\"\n"
        "}\n\n"
        "Output ONLY the raw JSON object. Do not wrap it in markdown block tags like ```json. "
        "Do not include any explanation or extra characters."
    )
    
    prompt = f"Patient Message:\n\"\"\"\n{message_body}\n\"\"\""
    
    client = get_llm_client()
    
    # Use Sonnet 3.5 or GPT-4o-mini
    result = client.chat_completion(
        system_prompt=system_prompt,
        prompt=prompt,
        temperature=0.0,
        max_tokens=250
    )
    
    # Parse JSON block robustly
    try:
        # Regex to find JSON object in case model wrapped it in markdown or text
        json_match = re.search(r"\{.*\}", result, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = result.strip()
            
        data = json.loads(json_str)
        return {
            "service_query": data.get("service_query"),
            "provider_query": data.get("provider_query"),
            "time_boundary_query": data.get("time_boundary_query")
        }
    except Exception as e:
        # Fallback in case of parse error
        return {
            "service_query": None,
            "provider_query": None,
            "time_boundary_query": None
        }
