import os

# Manual parser for dotenv to keep it simple and clean
def load_dotenv() -> None:
    for base_dir in [os.getcwd(), os.path.expanduser("~")]:
        env_path = os.path.join(base_dir, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            k, v = parts[0].strip(), parts[1].strip()
                            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                                v = v[1:-1]
                            if k not in os.environ:
                                os.environ[k] = v

load_dotenv()

# System Config & Feature Flags
USE_GROQ = os.getenv("USE_GROQ", "true").lower() in ("true", "1", "yes")
USE_CLAUDE = os.getenv("USE_CLAUDE", "false").lower() in ("true", "1", "yes")
ENABLE_EXPLANATIONS = os.getenv("ENABLE_EXPLANATIONS", "true").lower() in ("true", "1", "yes")
ENABLE_ALT_SLOTS = os.getenv("ENABLE_ALT_SLOTS", "true").lower() in ("true", "1", "yes")
ENABLE_LOGGING = os.getenv("ENABLE_LOGGING", "true").lower() in ("true", "1", "yes")

# Model Routing Configuration
CLASSIFICATION_MODEL = os.getenv("CLASSIFICATION_MODEL", "llama-3.1-8b-instant")
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "llama-3.3-70b-versatile")
RATIONALE_MODEL = os.getenv("RATIONALE_MODEL", "llama-3.3-70b-versatile")
