"""
Conversational Memory Store for Ask AI 2.1.
Maintains session-based conversation histories and structured state in-memory.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any

# In-memory session store: session_id -> { "history": [{"role": "...", "content": "..."}], "last_activity": datetime, "state": {} }
_session_store: Dict[str, Dict[str, Any]] = {}
SESSION_TIMEOUT_MINUTES = 30

def get_session_history(session_id: str) -> List[Dict[str, str]]:
    """Retrieves session history, checking for expiration."""
    now = datetime.utcnow()
    if session_id not in _session_store:
        _session_store[session_id] = {
            "history": [],
            "state": {},
            "last_activity": now
        }
        return []
        
    session = _session_store[session_id]
    if now - session["last_activity"] > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        # Session expired, clear history and state
        session["history"] = []
        session["state"] = {}
        
    session["last_activity"] = now
    return session["history"]

def get_session_state(session_id: str) -> Dict[str, Any]:
    """Retrieves the active state context for a session."""
    get_session_history(session_id) # ensure it is initialized and not expired
    return _session_store.get(session_id, {}).get("state", {})

def update_session_state(session_id: str, updates: Dict[str, Any]) -> None:
    """Updates the active state context for a session."""
    get_session_history(session_id)
    if session_id in _session_store:
        _session_store[session_id]["state"].update(updates)

def add_session_turn(session_id: str, role: str, content: str) -> None:
    """Adds a conversation turn to the session memory."""
    history = get_session_history(session_id)
    history.append({"role": role, "content": content})
    # Keep only the last 20 turns to avoid prompt bloat
    if len(history) > 20:
        history[:] = history[-20:]
    _session_store[session_id]["history"] = history
    _session_store[session_id]["last_activity"] = datetime.utcnow()

def clear_session(session_id: str) -> None:
    """Clears history and state for a session."""
    if session_id in _session_store:
        _session_store[session_id]["history"] = []
        _session_store[session_id]["state"] = {}
        _session_store[session_id]["last_activity"] = datetime.utcnow()
