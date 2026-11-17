from dotenv import load_dotenv
import os

# Load .env from multi-agent-support/ first, then fall back to repo root
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(base_dir, ".env"))           # multi-agent-support/.env
load_dotenv(dotenv_path=os.path.join(base_dir, "..", ".env"))     # repo root .env (fallback)

def _is_writable_path(path: str) -> bool:
    dir_path = os.path.dirname(os.path.abspath(path))
    try:
        os.makedirs(dir_path, exist_ok=True)
        test_file = os.path.join(dir_path, f".write_test_{os.getpid()}")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return True
    except Exception:
        return False

# ── Streamlit Cloud: inject secrets into os.environ ──────────────────────────
# st.secrets is available when running on Streamlit Cloud. Injecting here
# ensures all os.getenv() calls below (and in third-party libraries like
# langchain-groq) pick up the right values without needing per-call lookups.
try:
    import streamlit as st
    try:
        if hasattr(st, "secrets"):
            for _key in ["GROQ_API_KEY", "DATABASE_URL", "CHROMA_PATH", "USE_PROD", "GROQ_MODEL"]:
                if _key in st.secrets and not os.getenv(_key):
                    os.environ[_key] = str(st.secrets[_key]).strip()
    except Exception:
        pass
except Exception:
    pass  # Running locally or st.secrets not available — .env values are used

class _ConfigMeta(type):
    @property
    def GROQ_API_KEY(cls):
        key = os.getenv("GROQ_API_KEY")
        if not key:
            try:
                import streamlit as st
                if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
                    key = str(st.secrets["GROQ_API_KEY"]).strip()
                    os.environ["GROQ_API_KEY"] = key
            except Exception:
                pass
        return key

    @GROQ_API_KEY.setter
    def GROQ_API_KEY(cls, val):
        if val:
            os.environ["GROQ_API_KEY"] = str(val).strip()
        elif "GROQ_API_KEY" in os.environ:
            del os.environ["GROQ_API_KEY"]

class Config(metaclass=_ConfigMeta):

    # Supported fast model for Groq (e.g. openai/gpt-oss-20b or qwen/qwen3.8-27b)
    DEV_MODEL  = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    PROD_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

    USE_PROD_MODEL = os.getenv("USE_PROD", "false").lower() == "true"

    @classmethod
    def get_model(cls) -> str:
        model = os.getenv("GROQ_MODEL")
        if not model:
            try:
                import streamlit as st
                if hasattr(st, "secrets") and "GROQ_MODEL" in st.secrets:
                    model = str(st.secrets["GROQ_MODEL"]).strip()
                    os.environ["GROQ_MODEL"] = model
            except Exception:
                pass
        if model:
            return model
        return cls.PROD_MODEL if cls.USE_PROD_MODEL else cls.DEV_MODEL

    _db_path = os.path.join(base_dir, "data", "support.db")
    _chroma_default = os.path.join(base_dir, "knowledge_base", "chroma_db")

    # Detect Streamlit Cloud or other standard hosting platforms (Render, Heroku, Railway, HF)
    _is_deployed = (
        os.path.exists("/mount/src")
        or os.getenv("PORT") is not None
        or os.getenv("RENDER") is not None
        or os.getenv("RAILWAY_STATIC_URL") is not None
    )

    # If deployed or default db path is not writable, fall back to /tmp
    if _is_deployed or not _is_writable_path(_db_path):
        _db_path = "/tmp/support.db"
        _chroma_default = "/tmp/chroma_db"
    else:
        # Ensure database directory exists to avoid SQLite operational errors
        os.makedirs(os.path.dirname(_db_path), exist_ok=True)

    DATABASE_URL    = os.getenv("DATABASE_URL", f"sqlite:///{_db_path}")
    CHROMA_PATH     = os.getenv("CHROMA_PATH", _chroma_default)

    # Force using writable directory /tmp for SQLite and Chroma in deployed/read-only environments
    _db_dir = DATABASE_URL.replace("sqlite:///", "") if DATABASE_URL.startswith("sqlite://") else ""
    if _is_deployed or not _db_dir or not _is_writable_path(_db_dir):
        if DATABASE_URL.startswith("sqlite://"):
            db_name = os.path.basename(DATABASE_URL) or "support.db"
            DATABASE_URL = f"sqlite:////tmp/{db_name}"
        
        if CHROMA_PATH and not CHROMA_PATH.startswith("/tmp"):
            src_chroma = CHROMA_PATH
            chroma_dir = os.path.basename(CHROMA_PATH) or "chroma_db"
            dest_chroma = f"/tmp/{chroma_dir}"
            if os.path.exists(src_chroma) and not os.path.exists(dest_chroma):
                import shutil
                try:
                    shutil.copytree(src_chroma, dest_chroma)
                except Exception as e:
                    print(f"Warning: Failed to copy chroma_db to {dest_chroma}: {e}")
            CHROMA_PATH = dest_chroma
    COLLECTION_NAME = "support_kb"

    MAX_RETRIES = 3

    # Raised from 0.7 — only escalate truly angry customers, not mildly negative
    ESCALATION_FRUSTRATION_THRESHOLD = 0.85

    # Raised from 0.7 — only escalate truly angry customers, not mildly negative
    QA_MIN_SCORE = 0.75

    USE_LOCAL_CLASSIFIER = os.getenv("USE_LOCAL_CLASSIFIER", "false").lower() == "true"
    LOCAL_MODEL_PATH     = os.getenv("LOCAL_MODEL_PATH", os.path.join(base_dir, "fine_tuned_classifier"))