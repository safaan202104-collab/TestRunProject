"""
Generates fixtures/crm.json for the AI-engineer take-home.

Deterministic (seeded). Re-run only if you need to regenerate.
The generated file is checked into the package so the candidate does NOT need to run this.

Data shape:
- 8 providers with realistic, varied schedules
- 15 services across botox / filler / laser / aesthetic
- ~260 patients (10 deterministic + 250 generated)
- ~900 appointments spanning the prior 16 weeks + next 3 weeks

Deterministic patients pat_001..pat_010 are referenced by eval.jsonl.
Do not change their properties without updating eval.jsonl.
"""

import json
import random
from datetime import datetime, timedelta, time
from pathlib import Path

SEED = 20260518
random.seed(SEED)

NOW = datetime(2026, 5, 18, 14, 30, 0)   # local wall-clock (America/Los_Angeles); matches eval cases
TZ_SUFFIX = "-07:00"

OUT_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "crm.json"

# ---------- providers ----------

PROVIDERS = [
    {
        "id": "prov_1", "name": "Dr. Amelia Reyes", "title": "MD",
        "specialties": ["botox", "filler", "consult", "filler-dissolve"],
        "hours": {"mon": ["09:00-17:00"], "tue": ["09:00-17:00"], "wed": ["09:00-13:00"],
                  "thu": ["09:00-17:00"], "fri": ["09:00-15:00"]},
    },
    {
        "id": "prov_2", "name": "Jordan Patel, RN", "title": "RN",
        "specialties": ["botox", "filler", "lip-touchup", "filler-dissolve"],
        "hours": {"mon": ["10:00-18:00"], "tue": ["10:00-18:00"], "wed": ["10:00-18:00"],
                  "thu": ["10:00-18:00"], "sat": ["09:00-14:00"]},
    },
    {
        "id": "prov_3", "name": "Maya Lin, LE", "title": "LE",
        "specialties": ["laser", "hydrafacial", "consult", "chemical-peel", "microneedling"],
        "hours": {"tue": ["11:00-19:00"], "wed": ["11:00-19:00"], "thu": ["11:00-19:00"],
                  "fri": ["10:00-18:00"], "sat": ["10:00-15:00"]},
    },
    {
        "id": "prov_4", "name": "Dr. Henry Okafor", "title": "MD",
        "specialties": ["botox", "filler", "consult", "filler-dissolve", "post-procedure"],
        "hours": {"mon": ["08:00-14:00"], "wed": ["08:00-14:00"], "fri": ["08:00-14:00"]},
    },
    {
        "id": "prov_5", "name": "Taylor Nguyen, RN", "title": "RN",
        "specialties": ["botox", "lip-touchup", "post-procedure"],
        "hours": {"tue": ["12:00-20:00"], "wed": ["12:00-20:00"], "thu": ["12:00-20:00"],
                  "fri": ["12:00-20:00"]},
    },
    {
        "id": "prov_6", "name": "Sofia Marin, LE", "title": "LE",
        "specialties": ["hydrafacial", "chemical-peel", "microneedling", "consult"],
        "hours": {"mon": ["10:00-18:00"], "tue": ["10:00-18:00"], "thu": ["10:00-18:00"],
                  "sat": ["09:00-15:00"]},
    },
    {
        "id": "prov_7", "name": "Riley Brooks, RN", "title": "RN",
        "specialties": ["botox", "filler", "lip-touchup"],
        "hours": {"wed": ["09:00-17:00"], "thu": ["09:00-17:00"], "fri": ["09:00-17:00"],
                  "sat": ["09:00-14:00"]},
    },
    {
        "id": "prov_8", "name": "Imani Carter, LE", "title": "LE",
        "specialties": ["laser", "hydrafacial", "microneedling"],
        "hours": {"mon": ["11:00-19:00"], "wed": ["11:00-19:00"], "fri": ["11:00-19:00"]},
    },
]

# ---------- services ----------

SERVICES = [
    {"id": "svc_botox",        "name": "Botox treatment",         "duration_minutes": 30, "required_specialty": "botox",          "price_usd": 480},
    {"id": "svc_botox_touch",  "name": "Botox touch-up",          "duration_minutes": 20, "required_specialty": "botox",          "price_usd": 180},
    {"id": "svc_filler_lip",   "name": "Lip filler",              "duration_minutes": 45, "required_specialty": "filler",         "price_usd": 750},
    {"id": "svc_filler_cheek", "name": "Cheek filler",            "duration_minutes": 45, "required_specialty": "filler",         "price_usd": 850},
    {"id": "svc_filler_jaw",   "name": "Jaw / chin filler",       "duration_minutes": 60, "required_specialty": "filler",         "price_usd": 950},
    {"id": "svc_filler_undereye", "name": "Under-eye filler",     "duration_minutes": 60, "required_specialty": "filler",         "price_usd": 900},
    {"id": "svc_lip_touch",    "name": "Lip filler touch-up",     "duration_minutes": 30, "required_specialty": "lip-touchup",    "price_usd": 350},
    {"id": "svc_dissolve",     "name": "Filler dissolving",       "duration_minutes": 30, "required_specialty": "filler-dissolve","price_usd": 400},
    {"id": "svc_laser_small",  "name": "Laser hair removal (small area)", "duration_minutes": 30, "required_specialty": "laser",  "price_usd": 150},
    {"id": "svc_laser_large",  "name": "Laser hair removal (large area)", "duration_minutes": 60, "required_specialty": "laser",  "price_usd": 350},
    {"id": "svc_hydra",        "name": "HydraFacial",             "duration_minutes": 60, "required_specialty": "hydrafacial",    "price_usd": 250},
    {"id": "svc_peel",         "name": "Chemical peel",           "duration_minutes": 45, "required_specialty": "chemical-peel",  "price_usd": 200},
    {"id": "svc_microneedle",  "name": "Microneedling",           "duration_minutes": 60, "required_specialty": "microneedling",  "price_usd": 400},
    {"id": "svc_consult",      "name": "New-patient consult",     "duration_minutes": 30, "required_specialty": "consult",        "price_usd": 0},
    {"id": "svc_followup",     "name": "Post-procedure follow-up","duration_minutes": 15, "required_specialty": "post-procedure", "price_usd": 0},
]

# A weighted list of services representing typical demand mix (used when generating appointments).
SERVICE_WEIGHTS = [
    ("svc_botox", 22), ("svc_botox_touch", 8), ("svc_filler_lip", 10), ("svc_filler_cheek", 6),
    ("svc_filler_jaw", 3), ("svc_filler_undereye", 4), ("svc_lip_touch", 12), ("svc_dissolve", 2),
    ("svc_laser_small", 7), ("svc_laser_large", 5), ("svc_hydra", 9), ("svc_peel", 4),
    ("svc_microneedle", 4), ("svc_consult", 3), ("svc_followup", 1),
]
SERVICE_POOL = [sid for sid, w in SERVICE_WEIGHTS for _ in range(w)]

# Map service -> the patient tag(s) the service implies (used for assigning realistic tags)
SERVICE_TO_TAGS = {
    "svc_botox": ["botox"], "svc_botox_touch": ["botox"], "svc_filler_lip": ["filler"],
    "svc_filler_cheek": ["filler"], "svc_filler_jaw": ["filler"], "svc_filler_undereye": ["filler"],
    "svc_lip_touch": ["lip-touchup", "filler"], "svc_dissolve": ["filler"],
    "svc_laser_small": ["laser"], "svc_laser_large": ["laser"],
    "svc_hydra": ["hydrafacial"], "svc_peel": ["peel"], "svc_microneedle": ["microneedling"],
    "svc_consult": [], "svc_followup": [],
}

# ---------- patients ----------

FIRST_NAMES = [
    "Sarah", "Marco", "Priya", "Daniela", "Evan", "Hannah", "Mei", "Carlos", "Aisha", "Liam",
    "Olivia", "Noah", "Emma", "Mateo", "Sophia", "Jamal", "Yara", "Kenji", "Lila", "Diego",
    "Zara", "Ethan", "Ava", "Ravi", "Chloe", "Omar", "Isabella", "Felix", "Nadia", "Theo",
    "Layla", "Hugo", "Maya", "Asher", "Camila", "Bodhi", "Ruby", "Idris", "Saoirse", "Wren",
    "Elena", "Tomás", "Anya", "Beau", "Selene", "Kai", "Indira", "Léa", "Sami", "Yusuf",
    "Mira", "Atlas", "Juno", "Rafael", "Imani", "Niko", "Anaïs", "Sage", "Rohan", "Esme",
    "Quinn", "Tariq", "Brielle", "Cyrus", "Marisol", "Otto", "Romi", "Soren", "Vera", "Zane",
    "Adira", "Bastien", "Cleo", "Dax", "Ines", "Jaxon", "Keira", "Linnea", "Milo", "Nia",
]

LAST_NAMES = [
    "Chen", "Alvarez", "Shah", "Souza", "Wright", "Brooks", "Tanaka", "Patel", "Khan", "Nguyen",
    "Park", "Hernandez", "Okafor", "Liu", "Müller", "Rossi", "Petrov", "Goldberg", "Cohen", "Singh",
    "Adeyemi", "Fernandez", "Yamamoto", "Lopez", "Kim", "Davies", "Walsh", "Carter", "Reyes", "Holm",
    "Beaumont", "Costa", "Andersson", "Khoury", "Mendez", "Becker", "Vidal", "O'Neill", "Lindgren", "Tahir",
    "Sokolov", "Marchetti", "Bauer", "Caron", "Diaz", "Ferrari", "Hassan", "Iqbal", "Jensen", "Kovač",
    "Lambert", "Marin", "Novak", "Owens", "Pavlov", "Quintero", "Romero", "Sato", "Toma", "Ueda",
]

def make_phone(i):
    return f"+1555{(550000 + i):07d}"

def make_email(first, last, i):
    return f"{first.lower()}.{last.lower().replace(chr(39), '')}{i}@example.com"

# Deterministic patients (referenced by eval.jsonl). Do not renumber.
PINNED_PATIENTS = [
    {"id": "pat_001", "name": "Sarah Chen",      "phone": "+15555550101", "email": "sarah.chen@example.com",     "last_visit": "2026-02-14", "preferred_provider_id": "prov_2", "tags": ["filler", "lip-touchup"]},
    {"id": "pat_002", "name": "Marco Alvarez",   "phone": "+15555550102", "email": "marco.alvarez@example.com",  "last_visit": "2026-04-30", "preferred_provider_id": "prov_2", "tags": ["botox"]},
    {"id": "pat_003", "name": "Priya Shah",      "phone": "+15555550103", "email": "priya.shah@example.com",     "last_visit": "2025-11-02", "preferred_provider_id": "prov_1", "tags": ["botox"]},
    {"id": "pat_004", "name": "Daniela Souza",   "phone": "+15555550104", "email": "daniela.souza@example.com",  "last_visit": "2026-03-12", "preferred_provider_id": "prov_3", "tags": ["hydrafacial", "laser"]},
    {"id": "pat_005", "name": "Evan Wright",     "phone": "+15555550105", "email": "evan.wright@example.com",    "last_visit": "2026-04-05", "preferred_provider_id": "prov_2", "tags": ["filler"]},
    {"id": "pat_006", "name": "Hannah Brooks",   "phone": "+15555550106", "email": "hannah.brooks@example.com",  "last_visit": "2026-01-22", "preferred_provider_id": "prov_2", "tags": ["lip-touchup", "filler"], "opted_out_marketing": True},
    {"id": "pat_007", "name": "Robert Larsen",   "phone": "+15555550107", "email": "robert.larsen@example.com",  "last_visit": "2024-11-19", "preferred_provider_id": "prov_1", "tags": ["botox"]},
    {"id": "pat_008", "name": "Quentin Voss",    "phone": "+15555550108", "email": "quentin.voss@example.com",   "last_visit": "2025-09-04", "preferred_provider_id": None,     "tags": [], "do_not_book": True, "do_not_book_reason": "Account flagged after repeated no-shows + dispute. Escalate any contact to clinic manager."},
    {"id": "pat_009", "name": "Nora Holloway",   "phone": "+15555550109", "email": "nora.holloway@example.com",  "last_visit": None,         "preferred_provider_id": None,     "tags": []},
    {"id": "pat_010", "name": "Beatrice Whitmore","phone": "+15555550110","email": "beatrice.whitmore@example.com","last_visit": "2026-05-01","preferred_provider_id": "prov_1","tags": ["botox", "filler", "hydrafacial"], "vip": True, "notes": "VIP — always offer Dr. Reyes first; flag to front desk on any booking."},
]
PINNED_IDS = {p["id"] for p in PINNED_PATIENTS}

def generate_patients(n_extra=250):
    patients = list(PINNED_PATIENTS)
    used_names = {p["name"] for p in patients}
    i = 11
    while len(patients) < len(PINNED_PATIENTS) + n_extra:
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        if name in used_names:
            continue
        used_names.add(name)
        # last visit: 70% within 6 months, 20% 6-18 months ago, 8% >18 months, 2% never
        roll = random.random()
        if roll < 0.02:
            last_visit = None
        elif roll < 0.10:
            last_visit = (NOW - timedelta(days=random.randint(540, 900))).date().isoformat()
        elif roll < 0.30:
            last_visit = (NOW - timedelta(days=random.randint(180, 540))).date().isoformat()
        else:
            last_visit = (NOW - timedelta(days=random.randint(7, 180))).date().isoformat()

        # preferred provider biased toward 1/2/3 (more popular)
        weights = [3, 4, 3, 2, 2, 2, 2, 1]
        pref = random.choices([p["id"] for p in PROVIDERS], weights=weights)[0] if random.random() > 0.05 else None
        # tags from a probable history
        tag_pool = ["botox", "filler", "lip-touchup", "hydrafacial", "laser", "peel", "microneedling"]
        n_tags = random.choices([0, 1, 2, 3], weights=[1, 4, 4, 2])[0]
        tags = random.sample(tag_pool, n_tags) if last_visit else []
        rec = {
            "id": f"pat_{i:03d}",
            "name": name,
            "phone": make_phone(i),
            "email": make_email(first, last, i),
            "last_visit": last_visit,
            "preferred_provider_id": pref,
            "tags": tags,
        }
        if random.random() < 0.14:
            rec["opted_out_marketing"] = True
        if random.random() < 0.015:
            rec["do_not_book"] = True
            rec["do_not_book_reason"] = "Flagged after repeated no-shows."
        if random.random() < 0.03:
            rec["vip"] = True
        patients.append(rec)
        i += 1
    return patients

# ---------- appointments ----------

WEEKDAY = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

def parse_hours_range(rng):
    a, b = rng.split("-")
    return time(int(a[:2]), int(a[3:])), time(int(b[:2]), int(b[3:]))

def provider_windows_on(provider, day_date):
    wd = WEEKDAY[day_date.weekday()]
    return [parse_hours_range(r) for r in provider["hours"].get(wd, [])]

def fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + TZ_SUFFIX

def overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end

# Reserved-FREE slots: the generator's random pass will skip these so they remain available
# for the eval.jsonl cases that ask the candidate's system to book them. They do NOT appear
# as appointments in the output — they're holes carved into the random fill.
RESERVED_FREE_SLOTS = [
    # (provider_id, start_iso, end_iso, eval_id_for_reference)
    ("prov_2", "2026-05-18T17:00:00-07:00", "2026-05-18T17:30:00-07:00", "e35"),
    ("prov_2", "2026-05-21T11:00:00-07:00", "2026-05-21T11:30:00-07:00", "e31"),
    ("prov_2", "2026-05-21T15:00:00-07:00", "2026-05-21T15:30:00-07:00", "e44"),
    ("prov_2", "2026-05-21T16:30:00-07:00", "2026-05-21T17:30:00-07:00", "e02"),
    ("prov_1", "2026-05-22T09:30:00-07:00", "2026-05-22T10:00:00-07:00", "e08"),
    ("prov_1", "2026-05-22T10:00:00-07:00", "2026-05-22T10:30:00-07:00", "e40"),
    ("prov_1", "2026-05-22T11:00:00-07:00", "2026-05-22T11:30:00-07:00", "e30"),
    ("prov_3", "2026-05-22T14:00:00-07:00", "2026-05-22T15:00:00-07:00", "e33"),
    ("prov_2", "2026-05-23T09:30:00-07:00", "2026-05-23T10:00:00-07:00", "e36"),
    ("prov_3", "2026-05-23T10:00:00-07:00", "2026-05-23T11:00:00-07:00", "e03"),
    ("prov_2", "2026-05-26T13:00:00-07:00", "2026-05-26T13:30:00-07:00", "e01"),
    ("prov_2", "2026-05-28T14:00:00-07:00", "2026-05-28T14:45:00-07:00", "e37"),
    ("prov_1", "2026-05-22T12:00:00-07:00", "2026-05-22T12:30:00-07:00", "e41"),
]

def generate_appointments(patients):
    # Pinned appointments referenced by eval.jsonl. Keep these stable.
    pinned = [
        # Marco has an existing appt at Tue May 19 13:00 with Jordan — creates the e10 conflict scenario.
        {"id": "appt_pin_1", "provider_id": "prov_2", "patient_id": "pat_002", "start": "2026-05-19T13:00:00-07:00", "end": "2026-05-19T13:30:00-07:00", "service_id": "svc_botox", "status": "booked"},
        # Evan filler appt that anchors the e09 / e10 area.
        {"id": "appt_pin_2", "provider_id": "prov_2", "patient_id": "pat_005", "start": "2026-05-19T14:00:00-07:00", "end": "2026-05-19T14:45:00-07:00", "service_id": "svc_filler_lip", "status": "booked"},
        # Priya botox with Dr. Reyes Mon morning (Reyes works Wed only AM — for e09 logic).
        {"id": "appt_pin_3", "provider_id": "prov_1", "patient_id": "pat_003", "start": "2026-05-18T10:00:00-07:00", "end": "2026-05-18T10:30:00-07:00", "service_id": "svc_botox", "status": "completed"},
        # Daniela hydra on Wed.
        {"id": "appt_pin_4", "provider_id": "prov_3", "patient_id": "pat_004", "start": "2026-05-20T15:00:00-07:00", "end": "2026-05-20T16:00:00-07:00", "service_id": "svc_hydra", "status": "booked"},
        # Hannah lip touch-up on Sat.
        {"id": "appt_pin_5", "provider_id": "prov_2", "patient_id": "pat_006", "start": "2026-05-23T11:30:00-07:00", "end": "2026-05-23T12:00:00-07:00", "service_id": "svc_lip_touch", "status": "booked"},
    ]
    appts = list(pinned)

    # Build a busy index for conflict avoidance during random generation.
    busy = {p["id"]: [] for p in PROVIDERS}
    for a in pinned:
        s = datetime.fromisoformat(a["start"])
        e = datetime.fromisoformat(a["end"])
        busy[a["provider_id"]].append((s.replace(tzinfo=None), e.replace(tzinfo=None)))
    # Reserved free slots — make the random generator believe they're busy so it skips them.
    # They are never added to the appointments output, so they remain truly free.
    for prov_id, s_iso, e_iso, _ in RESERVED_FREE_SLOTS:
        s = datetime.fromisoformat(s_iso).replace(tzinfo=None)
        e = datetime.fromisoformat(e_iso).replace(tzinfo=None)
        busy[prov_id].append((s, e))

    # Past 16 weeks + next 3 weeks.
    start_day = (NOW - timedelta(weeks=16)).date()
    end_day = (NOW + timedelta(weeks=3)).date()
    days = []
    d = start_day
    while d <= end_day:
        days.append(d)
        d += timedelta(days=1)

    bookable_pids = [p["id"] for p in patients if not p.get("do_not_book")]
    bookable_pids_array = bookable_pids  # for speed
    next_id = 1

    for day in days:
        is_future = day >= NOW.date()
        for prov in PROVIDERS:
            windows = provider_windows_on(prov, day)
            if not windows:
                continue
            # Decide load for this provider on this day: 40-85% utilization.
            for w_start, w_end in windows:
                ws = datetime.combine(day, w_start)
                we = datetime.combine(day, w_end)
                total_min = int((we - ws).total_seconds() // 60)
                target_min = int(total_min * random.uniform(0.40, 0.85))
                booked_min = 0
                tries = 0
                while booked_min < target_min and tries < 40:
                    tries += 1
                    svc_id = random.choice(SERVICE_POOL)
                    svc = next(s for s in SERVICES if s["id"] == svc_id)
                    # Provider must have the specialty
                    if svc["required_specialty"] not in prov["specialties"]:
                        continue
                    dur = svc["duration_minutes"]
                    # pick a slot aligned to 15-min grid
                    slots = list(range(0, total_min - dur + 1, 15))
                    if not slots:
                        break
                    offset = random.choice(slots)
                    s_dt = ws + timedelta(minutes=offset)
                    e_dt = s_dt + timedelta(minutes=dur)
                    if any(overlaps(s_dt, e_dt, b[0], b[1]) for b in busy[prov["id"]]):
                        continue
                    pid = random.choice(bookable_pids_array)
                    status = "booked" if is_future else random.choices(["completed", "no_show", "cancelled"], weights=[88, 7, 5])[0]
                    appts.append({
                        "id": f"appt_{next_id:04d}",
                        "provider_id": prov["id"],
                        "patient_id": pid,
                        "start": fmt(s_dt),
                        "end": fmt(e_dt),
                        "service_id": svc_id,
                        "status": status,
                    })
                    busy[prov["id"]].append((s_dt, e_dt))
                    booked_min += dur
                    next_id += 1
    return appts

# ---------- write ----------

def main():
    patients = generate_patients(n_extra=250)
    appointments = generate_appointments(patients)
    out = {
        "_comment": (
            "Synthetic CRM data for the AI-engineer take-home. Generated deterministically. "
            "All names, contact info, and history are fictional. Times are local wall-clock "
            "(America/Los_Angeles). Treat the field 'now' in eval cases as your reference time — "
            "do not use the actual current time."
        ),
        "_generated_with_seed": SEED,
        "_now": fmt(NOW),
        "_timezone": "America/Los_Angeles",
        "providers": PROVIDERS,
        "services": SERVICES,
        "patients": patients,
        "appointments": appointments,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUT_PATH}")
    print(f"  providers:    {len(PROVIDERS)}")
    print(f"  services:     {len(SERVICES)}")
    print(f"  patients:     {len(patients)}")
    print(f"  appointments: {len(appointments)}")
    fut = sum(1 for a in appointments if a["start"] > fmt(NOW))
    print(f"    future:     {fut}")
    print(f"    past:       {len(appointments) - fut}")

if __name__ == "__main__":
    main()
