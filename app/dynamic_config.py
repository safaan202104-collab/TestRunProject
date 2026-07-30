"""
Dynamic Configuration Engine — Database-backed.
Loads and saves configuration parameters dynamically in SQLite/PostgreSQL system_config table.
"""
from typing import Dict, Any
from app.database import SessionLocal
from app.db_models import SystemConfig as DBSystemConfig

DEFAULT_CONFIG = {
    "confidence_threshold": 0.85,
    "alternative_slot_count": 3,
    "fallback_model_enabled": True,
    "logging_level": "INFO",
    "weight_preferred_provider": 20.0,
    "weight_back_to_back": 10.0,
    "weight_small_gap": 5.0,
    "weight_soonest_penalty": 0.5,
    "escalation_threshold": 0.70,
    "booking_window_days": 14,
    "max_alternatives": 3
}

def load_dynamic_config() -> Dict[str, Any]:
    """Loads system configuration from the database, merging defaults for missing keys."""
    db = SessionLocal()
    try:
        rows = db.query(DBSystemConfig).all()
        config = {r.key: r.value for r in rows}
        
        # Merge defaults
        changed = False
        for k, v in DEFAULT_CONFIG.items():
            if k not in config:
                config[k] = v
                db.add(DBSystemConfig(key=k, value=v))
                changed = True
        if changed:
            db.commit()
            
        return config
    except Exception as e:
        print(f"[CONFIG] Failed to load config from database: {e}")
        return DEFAULT_CONFIG
    finally:
        db.close()

def save_dynamic_config(config: Dict[str, Any]) -> None:
    """Saves system configuration to the database."""
    db = SessionLocal()
    try:
        for k, v in config.items():
            row = db.query(DBSystemConfig).filter(DBSystemConfig.key == k).first()
            if row:
                row.value = v
            else:
                db.add(DBSystemConfig(key=k, value=v))
        db.commit()
    except Exception as e:
        print(f"[CONFIG] Failed to save config to database: {e}")
        db.rollback()
    finally:
        db.close()

def get_config_val(key: str) -> Any:
    """Gets a configuration value by key."""
    db = SessionLocal()
    try:
        row = db.query(DBSystemConfig).filter(DBSystemConfig.key == key).first()
        if row:
            return row.value
        return DEFAULT_CONFIG.get(key)
    except Exception:
        return DEFAULT_CONFIG.get(key)
    finally:
        db.close()
