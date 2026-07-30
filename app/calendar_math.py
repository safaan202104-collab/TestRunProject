import re
import json
from datetime import datetime, timedelta
import pytz
from dateutil import parser as date_parser
from typing import Tuple, Dict, Any, List, Optional
from app.client import get_llm_client

LA_TZ = pytz.timezone("America/Los_Angeles")

def parse_iso_datetime(dt_str: str) -> datetime:
    """Parses ISO-8601 datetime string, ensuring it is localized to LA timezone."""
    dt = date_parser.isoparse(dt_str)
    if dt.tzinfo is None:
        dt = LA_TZ.localize(dt)
    else:
        dt = dt.astimezone(LA_TZ)
    return dt

def format_iso_datetime(dt: datetime) -> str:
    """Formats datetime back to ISO-8601 with correct offset."""
    return dt.isoformat()

def resolve_time_boundary_with_llm(time_query: str, now_str: str) -> Tuple[datetime, datetime]:
    """Uses LLM to translate relative time queries to absolute ISO start/end search ranges."""
    now_dt = parse_iso_datetime(now_str)
    
    # Construct a reference calendar in the prompt to give the model full context of the relative days
    calendar_lines = []
    current_day = now_dt
    for i in range(14):  # Next 14 days
        day_name = current_day.strftime("%A")
        date_str = current_day.strftime("%Y-%m-%d")
        relative_label = ""
        if i == 0:
            relative_label = " (Today)"
        elif i == 1:
            relative_label = " (Tomorrow)"
            
        calendar_lines.append(f"- {day_name}, {date_str}{relative_label}")
        current_day += timedelta(days=1)
        
    calendar_context = "\n".join(calendar_lines)
    
    system_prompt = (
        "You are an expert scheduling assistant. Convert relative time queries (like 'next Tuesday afternoon') "
        "into strict start/end datetimes in ISO-8601 format, keeping the same timezone offset (-07:00).\n\n"
        f"Reference Time (now): {now_dt.strftime('%A, %Y-%m-%d %I:%M %p')}\n"
        f"Reference Calendar:\n{calendar_context}\n\n"
        "Guidelines for ranges:\n"
        "- 'morning': 09:00:00 to 12:00:00\n"
        "- 'afternoon': 12:00:00 to 17:00:00\n"
        "- 'evening': 17:00:00 to 20:00:00\n"
        "- 'all day' or unspecified time of day: 09:00:00 to 19:00:00\n"
        "- If a patient specifies an exact time (e.g., 'Thursday at 4:30pm'), make start_range and end_range cover exactly that slot (e.g., 16:30:00 to 17:30:00).\n"
        "- If they ask for 'next week', start the range on the next Monday.\n"
        "- If they ask for a specific day (e.g. 'May 19'), range is 09:00:00 to 19:00:00 on that day.\n"
        "- Spanish relative dates: 'el próximo martes' on a Monday means the Tuesday of next week (May 26), not tomorrow (May 19). Always translate 'próximo/a' relative day terms to mean the day of the next week (e.g. May 26).\n"
        "- Weekday matching rule: Strictly match the requested weekday to the exact weekday name in the Reference Calendar (e.g. 'Friday' must map to the date labeled 'Friday' like 2026-05-22, NOT Thursday 2026-05-21). Double-check the calendar names carefully.\n\n"
        "Format your output as a raw JSON object with keys:\n"
        "{\n"
        "  \"start_range\": \"YYYY-MM-DDTHH:MM:SS-07:00\",\n"
        "  \"end_range\": \"YYYY-MM-DDTHH:MM:SS-07:00\"\n"
        "}\n\n"
        "Output ONLY the raw JSON object. Do not wrap it in markdown code blocks."
    )
    
    prompt = f"Time query: \"{time_query}\""
    
    client = get_llm_client()
    result = client.chat_completion(
        system_prompt=system_prompt,
        prompt=prompt,
        temperature=0.0,
        max_tokens=150
    )
    
    try:
        json_match = re.search(r"\{.*\}", result, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = result.strip()
            
        data = json.loads(json_str)
        start_range = parse_iso_datetime(data["start_range"])
        end_range = parse_iso_datetime(data["end_range"])
        return start_range, end_range
    except Exception as e:
        # Fallback: search next 7 days
        return now_dt, now_dt + timedelta(days=7)

def get_weekday_str(dt: datetime) -> str:
    """Gets 3-letter weekday abbreviation used in crm.json hours."""
    days = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
    return days[dt.weekday()]

def is_within_working_hours(dt: datetime, duration_minutes: int, hours_config: Dict[str, List[str]]) -> bool:
    """Checks if slot starting at 'dt' for 'duration_minutes' is within provider's working hours."""
    weekday = get_weekday_str(dt)
    if weekday not in hours_config:
        return False
        
    slot_start_time = dt.time()
    slot_end_time = (dt + timedelta(minutes=duration_minutes)).time()
    
    for window in hours_config[weekday]:
        # Parse window e.g., "09:00-17:00"
        m = re.match(r"(\d{2}):(\d{2})-(\d{2}):(\d{2})", window)
        if not m:
            continue
        start_hr, start_min, end_hr, end_min = map(int, m.groups())
        
        window_start = datetime.combine(dt.date(), datetime.min.time().replace(hour=start_hr, minute=start_min))
        window_start = LA_TZ.localize(window_start).time()
        
        window_end = datetime.combine(dt.date(), datetime.min.time().replace(hour=end_hr, minute=end_min))
        window_end = LA_TZ.localize(window_end).time()
        
        if slot_start_time >= window_start and slot_end_time <= window_end:
            return True
            
    return False

def is_range_outside_working_hours(start: datetime, end: datetime, provider_id: Optional[str] = None) -> bool:
    """Checks if the requested datetime search range falls entirely outside all relevant providers' working hours."""
    from app import crm_indexer
    providers = []
    if provider_id:
        p = crm_indexer.get_provider_by_id(provider_id)
        if p:
            providers.append(p)
    else:
        providers = crm_indexer.get_all_providers()
        
    for prov in providers:
        hours = prov.get("hours", {})
        curr = start
        while curr <= end:
            weekday = get_weekday_str(curr)
            if weekday in hours:
                for h_range in hours[weekday]:
                    h_start_str, h_end_str = h_range.split("-")
                    h_start_h, h_start_m = map(int, h_start_str.split(":"))
                    h_end_h, h_end_m = map(int, h_end_str.split(":"))
                    
                    prov_start = curr.replace(hour=h_start_h, minute=h_start_m, second=0, microsecond=0)
                    prov_end = curr.replace(hour=h_end_h, minute=h_end_m, second=0, microsecond=0)
                    
                    # Check overlap
                    if max(start, prov_start) < min(end, prov_end):
                        return False
            curr += timedelta(days=1)
    return True
