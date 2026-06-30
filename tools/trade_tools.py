"""
tools/trade_tools.py
--------------------
Core trade data loading and querying tools.
"""

import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
import config


def load_trades(file_path: Optional[str] = None) -> pd.DataFrame:
    """Load trade data from CSV. Falls back to synthetic data path."""
    path = Path(file_path) if file_path else config.TRADE_DATA_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Trade data not found at {path}. Run: python data/generate_trades.py"
        )
    df = pd.read_csv(path, parse_dates=["timestamp"])
    return df


def get_trade_stats(df: pd.DataFrame) -> dict:
    """Return high-level summary statistics for a trade DataFrame."""
    total = len(df)
    by_desk = df.groupby("desk")["notional"].agg(["count", "sum"]).reset_index()
    by_desk.columns = ["desk", "trade_count", "total_notional"]

    return {
        "total_trades":       total,
        "total_notional":     round(float(df["notional"].sum()), 2),
        "avg_notional":       round(float(df["notional"].mean()), 2),
        "date_range": {
            "from": str(df["timestamp"].min().date()),
            "to":   str(df["timestamp"].max().date()),
        },
        "by_desk":        by_desk.to_dict(orient="records"),
        "status_counts":  df["status"].value_counts().to_dict(),
        "unique_traders": int(df["trader_id"].nunique()),
        "unique_counterparties": int(df["counterparty"].nunique()),
    }


def query_trades(
    df: pd.DataFrame,
    desk: Optional[str] = None,
    trader_id: Optional[str] = None,
    instrument: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    flagged_only: bool = False,
) -> pd.DataFrame:
    """Filter trades by optional criteria."""
    mask = pd.Series([True] * len(df), index=df.index)
    if desk:
        mask &= df["desk"].str.upper() == desk.upper()
    if trader_id:
        mask &= df["trader_id"] == trader_id
    if instrument:
        mask &= df["instrument"].str.upper() == instrument.upper()
    if status:
        mask &= df["status"].str.lower() == status.lower()
    if from_date:
        mask &= df["timestamp"] >= pd.to_datetime(from_date)
    if to_date:
        mask &= df["timestamp"] <= pd.to_datetime(to_date)
    if flagged_only and "is_flagged" in df.columns:
        mask &= df["is_flagged"].astype(bool)
    return df[mask].copy()


def log_audit_event(event_type: str, description: str, severity: str = "INFO") -> None:
    """Write an audit event to SQLite audit log."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.AUDIT_LOG_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            description TEXT,
            severity TEXT,
            created_at TEXT
        )
    """)
    conn.execute(
        "INSERT INTO audit_log (event_type, description, severity, created_at) VALUES (?,?,?,?)",
        (event_type, description, severity, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_audit_log(limit: int = 50) -> list[dict]:
    """Retrieve recent audit log entries."""
    if not config.AUDIT_LOG_DB.exists():
        return []
    conn = sqlite3.connect(config.AUDIT_LOG_DB)
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    cols = ["id", "event_type", "description", "severity", "created_at"]
    return [dict(zip(cols, r)) for r in rows]
