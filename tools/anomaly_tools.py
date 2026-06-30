"""
tools/anomaly_tools.py
----------------------
Statistical and rule-based anomaly detection on trade data.
"""

import pandas as pd
import numpy as np
from typing import Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
import config


def _zscore_flag(series: pd.Series, threshold: float = None) -> pd.Series:
    """Return boolean mask where |z-score| > threshold."""
    thr = threshold or config.ZSCORE_THRESHOLD
    s_clean = series.dropna()
    if len(s_clean) < 2 or s_clean.std(ddof=0) == 0:
        z = pd.Series(0.0, index=s_clean.index)
    else:
        z = np.abs((s_clean - s_clean.mean()) / s_clean.std(ddof=0))
    z_full = pd.Series(0.0, index=series.index)
    z_full.loc[s_clean.index] = z
    return z_full > thr, z_full


def detect_statistical_anomalies(df: pd.DataFrame) -> list[dict]:
    """
    Z-score based detection on price and quantity per instrument.
    Returns list of flagged trade dicts with zscore details.
    """
    flagged = []

    for instrument, grp in df.groupby("instrument"):
        if len(grp) < 5:
            continue  # not enough data for meaningful z-score

        # Price outlier
        price_flag, price_z = _zscore_flag(grp["price"])
        for idx in grp[price_flag].index:
            flagged.append({
                "trade_id":     df.at[idx, "trade_id"],
                "anomaly_type": "price_outlier",
                "severity":     "HIGH",
                "reason":       f"Price z-score={price_z[idx]:.2f} (threshold {config.ZSCORE_THRESHOLD})",
                "instrument":   instrument,
                "desk":         df.at[idx, "desk"],
                "trader_id":    df.at[idx, "trader_id"],
                "timestamp":    str(df.at[idx, "timestamp"]),
                "value":        df.at[idx, "price"],
            })

        # Volume / quantity spike
        qty_flag, qty_z = _zscore_flag(grp["quantity"])
        for idx in grp[qty_flag].index:
            flagged.append({
                "trade_id":     df.at[idx, "trade_id"],
                "anomaly_type": "volume_spike",
                "severity":     "HIGH",
                "reason":       f"Quantity z-score={qty_z[idx]:.2f} (threshold {config.ZSCORE_THRESHOLD})",
                "instrument":   instrument,
                "desk":         df.at[idx, "desk"],
                "trader_id":    df.at[idx, "trader_id"],
                "timestamp":    str(df.at[idx, "timestamp"]),
                "value":        int(df.at[idx, "quantity"]),
            })

    return flagged


def detect_rule_anomalies(df: pd.DataFrame) -> list[dict]:
    """
    Rule-based anomaly detection. Returns list of flagged trade dicts.
    """
    flagged = []

    # ── R002: Off-hours trades ────────────────────────────────
    lo, hi = config.TRADE_HOURS
    off_hours_mask = (
        df["timestamp"].dt.hour < lo
    ) | (df["timestamp"].dt.hour >= hi)
    for idx in df[off_hours_mask].index:
        flagged.append({
            "trade_id":     df.at[idx, "trade_id"],
            "anomaly_type": "off_hours",
            "severity":     "MEDIUM",
            "reason":       f"Trade at {df.at[idx, 'timestamp'].strftime('%H:%M')} outside {lo}:00–{hi}:00",
            "instrument":   df.at[idx, "instrument"],
            "desk":         df.at[idx, "desk"],
            "trader_id":    df.at[idx, "trader_id"],
            "timestamp":    str(df.at[idx, "timestamp"]),
            "value":        df.at[idx, "timestamp"].hour,
        })

    # ── R005: Duplicate trade IDs ─────────────────────────────
    dup_mask = df.duplicated(subset=["trade_id"], keep=False)
    for idx in df[dup_mask].index:
        flagged.append({
            "trade_id":     df.at[idx, "trade_id"],
            "anomaly_type": "duplicate_id",
            "severity":     "CRITICAL",
            "reason":       f"Duplicate trade_id detected",
            "instrument":   df.at[idx, "instrument"],
            "desk":         df.at[idx, "desk"],
            "trader_id":    df.at[idx, "trader_id"],
            "timestamp":    str(df.at[idx, "timestamp"]),
            "value":        df.at[idx, "trade_id"],
        })

    # ── R004: Missing mandatory fields ────────────────────────
    mandatory_fields = ["trader_id", "venue", "counterparty"]
    for field in mandatory_fields:
        null_mask = df[field].isna()
        for idx in df[null_mask].index:
            flagged.append({
                "trade_id":     df.at[idx, "trade_id"],
                "anomaly_type": "missing_field",
                "severity":     "HIGH",
                "reason":       f"Mandatory field '{field}' is null",
                "instrument":   df.at[idx, "instrument"],
                "desk":         df.at[idx, "desk"],
                "trader_id":    df.at[idx, "trader_id"] if pd.notna(df.at[idx, "trader_id"]) else "UNKNOWN",
                "timestamp":    str(df.at[idx, "timestamp"]),
                "value":        None,
            })

    # ── R006: Counterparty concentration ─────────────────────
    for (desk, date), grp in df.groupby([
        df["desk"], df["timestamp"].dt.date
    ]):
        total_notional = grp["notional"].sum()
        if total_notional == 0:
            continue
        cp_conc = grp.groupby("counterparty")["notional"].sum() / total_notional
        breached = cp_conc[cp_conc > config.COUNTERPARTY_CONC_LIMIT]
        for cp, ratio in breached.items():
            cp_trades = grp[grp["counterparty"] == cp]
            for idx in cp_trades.index:
                flagged.append({
                    "trade_id":     df.at[idx, "trade_id"],
                    "anomaly_type": "counterparty_concentration",
                    "severity":     "HIGH",
                    "reason":       f"Counterparty {cp} = {ratio:.1%} of {desk} desk on {date}",
                    "instrument":   df.at[idx, "instrument"],
                    "desk":         desk,
                    "trader_id":    df.at[idx, "trader_id"],
                    "timestamp":    str(df.at[idx, "timestamp"]),
                    "value":        round(ratio, 4),
                })

    # ── R007: Minor deviation (Low severity) ──────────────────
    if "anomaly_type" in df.columns:
        minor_mask = df["anomaly_type"] == "minor_deviation"
        for idx in df[minor_mask].index:
            flagged.append({
                "trade_id":     df.at[idx, "trade_id"],
                "anomaly_type": "minor_deviation",
                "severity":     "LOW",
                "reason":       "Minor deviation in trade rounding or latency",
                "instrument":   df.at[idx, "instrument"],
                "desk":         df.at[idx, "desk"],
                "trader_id":    df.at[idx, "trader_id"],
                "timestamp":    str(df.at[idx, "timestamp"]),
                "value":        None,
            })

    return flagged


def get_anomaly_summary(flagged: list[dict]) -> dict:
    """Aggregate anomaly results into a summary dict."""
    if not flagged:
        return {"total_flagged": 0, "by_type": {}, "by_severity": {}, "flagged_trades": []}

    df_f = pd.DataFrame(flagged)
    return {
        "total_flagged":  len(df_f),
        "unique_trades":  int(df_f["trade_id"].nunique()),
        "by_type":        df_f["anomaly_type"].value_counts().to_dict(),
        "by_severity":    df_f["severity"].value_counts().to_dict(),
        "by_desk":        df_f["desk"].value_counts().to_dict(),
        "flagged_trades": flagged,
    }


def run_full_anomaly_detection(df: pd.DataFrame) -> dict:
    """Run both statistical and rule-based detection and merge results."""
    stat_flags  = detect_statistical_anomalies(df)
    rule_flags  = detect_rule_anomalies(df)
    all_flags   = stat_flags + rule_flags

    # Deduplicate by (trade_id, anomaly_type)
    seen = set()
    unique_flags = []
    for f in all_flags:
        key = (f["trade_id"], f["anomaly_type"])
        if key not in seen:
            seen.add(key)
            unique_flags.append(f)

    return get_anomaly_summary(unique_flags)
