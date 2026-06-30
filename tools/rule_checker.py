"""
tools/rule_checker.py
---------------------
Deterministic JSON-rulebook based compliance rule checker.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
import config


def load_rules(rules_path: Optional[str] = None) -> list[dict]:
    """Load compliance rules from JSON."""
    path = Path(rules_path) if rules_path else config.RULES_PATH
    with open(path) as f:
        return json.load(f)["rules"]


def check_rules(df: pd.DataFrame, rules: Optional[list[dict]] = None) -> list[dict]:
    """
    Run each compliance rule against the trade DataFrame.
    Returns list of violations: {rule_id, rule_name, trade_id, detail, severity, regulation}
    """
    if rules is None:
        rules = load_rules()

    violations = []

    for rule in rules:
        rid      = rule["id"]
        name     = rule["name"]
        field    = rule["field"]
        op       = rule["operator"]
        thr      = rule["threshold"]
        sev      = rule["severity"]
        reg      = rule.get("regulation", "")

        # ── R001 / R008 / R009: numeric threshold on a column ──
        if op == ">" and field in df.columns:
            breach = df[df[field] > thr]
            for idx in breach.index:
                violations.append({
                    "rule_id":    rid,
                    "rule_name":  name,
                    "trade_id":   df.at[idx, "trade_id"],
                    "severity":   sev,
                    "detail":     f"{field}={df.at[idx, field]} > threshold {thr}",
                    "regulation": reg,
                })

        elif op == "<" and field in df.columns:
            breach = df[df[field] < thr]
            for idx in breach.index:
                violations.append({
                    "rule_id":    rid,
                    "rule_name":  name,
                    "trade_id":   df.at[idx, "trade_id"],
                    "severity":   sev,
                    "detail":     f"{field}={df.at[idx, field]} < threshold {thr}",
                    "regulation": reg,
                })

        # ── R002: off-hours ───────────────────────────────────
        elif op == "not_in_range" and field == "hour":
            lo, hi = thr
            off = df[(df["timestamp"].dt.hour < lo) | (df["timestamp"].dt.hour >= hi)]
            for idx in off.index:
                violations.append({
                    "rule_id":    rid,
                    "rule_name":  name,
                    "trade_id":   df.at[idx, "trade_id"],
                    "severity":   sev,
                    "detail":     f"Trade at {df.at[idx,'timestamp'].strftime('%H:%M')} outside {lo}:00–{hi}:00",
                    "regulation": reg,
                })

        # ── R004: null check ─────────────────────────────────
        elif op == "null_check" and isinstance(thr, list):
            for col in thr:
                if col not in df.columns:
                    continue
                null_rows = df[df[col].isna()]
                for idx in null_rows.index:
                    violations.append({
                        "rule_id":    rid,
                        "rule_name":  name,
                        "trade_id":   df.at[idx, "trade_id"],
                        "severity":   sev,
                        "detail":     f"Field '{col}' is null",
                        "regulation": reg,
                    })

        # ── R005: duplicate trade IDs ─────────────────────────
        elif op == "unique" and field == "trade_id":
            dups = df[df.duplicated(subset=["trade_id"], keep=False)]
            for idx in dups.index:
                violations.append({
                    "rule_id":    rid,
                    "rule_name":  name,
                    "trade_id":   df.at[idx, "trade_id"],
                    "severity":   sev,
                    "detail":     "Duplicate trade_id",
                    "regulation": reg,
                })

    return violations


def get_rule_summary(violations: list[dict]) -> dict:
    """Summarize rule violations."""
    if not violations:
        return {"total_violations": 0, "by_rule": {}, "by_severity": {}}

    vdf = pd.DataFrame(violations)
    return {
        "total_violations": len(vdf),
        "unique_trades":    int(vdf["trade_id"].nunique()),
        "by_rule":          vdf.groupby("rule_id")["trade_id"].count().to_dict(),
        "by_severity":      vdf["severity"].value_counts().to_dict(),
        "violations":       violations,
    }
