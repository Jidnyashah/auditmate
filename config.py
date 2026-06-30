import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# ── Gemini / ADK ──────────────────────────────────────────────
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
MODEL_NAME: str = "gemini-2.5-flash"

# ── Paths ─────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
CHROMA_DIR = BASE_DIR / "vector_db"

TRADE_DATA_PATH = DATA_DIR / "synthetic_trades.csv"
RULES_PATH = DATA_DIR / "compliance_rules.json"
AUDIT_LOG_DB = DATA_DIR / "audit_log.db"

# ── Anomaly thresholds ─────────────────────────────────────────
ZSCORE_THRESHOLD = 3.0          # flag if |z| > this
COUNTERPARTY_CONC_LIMIT = 0.25  # flag if single CP > 25% of desk volume (RBI LEF limit)
TRADE_HOURS = (9, 17)           # 09:00 – 17:00 IST considered normal
LARGE_TRADE_NOTIONAL = 10_000_000  # ₹10M (1 Crore) notional threshold

# ── ChromaDB collections ──────────────────────────────────────
REGULATIONS_COLLECTION = "regulations"
AUDIT_TRAIL_COLLECTION = "audit_trail"

# ── Report output ─────────────────────────────────────────────
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
