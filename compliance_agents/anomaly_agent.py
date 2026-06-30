"""
compliance_agents/anomaly_agent.py
-----------------------
ADK agent: Trade Anomaly Detector
Detects statistical + rule-based anomalies in trade data.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

import config
from tools.trade_tools import load_trades, get_trade_stats, log_audit_event
from tools.anomaly_tools import run_full_anomaly_detection


# ── Tool functions (plain Python, ADK wraps them) ────────────

def tool_load_and_detect_anomalies(file_path: str = "") -> str:
    """
    Load trade data and run full anomaly detection (statistical + rule-based).
    Args:
        file_path: Optional path to a CSV file. Uses default synthetic data if empty.
    Returns:
        JSON string with anomaly summary.
    """
    try:
        df = load_trades(file_path if file_path else None)
        result = run_full_anomaly_detection(df)
        log_audit_event(
            "ANOMALY_SCAN",
            f"Detected {result['total_flagged']} anomalies across {result['unique_trades']} unique trades.",
            severity="INFO",
        )
        # Limit flagged_trades for response size
        result["flagged_trades"] = result["flagged_trades"][:20]
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_trade_stats(file_path: str = "") -> str:
    """
    Get high-level trade statistics.
    Args:
        file_path: Optional CSV path. Uses default if empty.
    Returns:
        JSON string with trade statistics.
    """
    try:
        df = load_trades(file_path if file_path else None)
        stats = get_trade_stats(df)
        return json.dumps(stats, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_anomaly_by_type(anomaly_type: str, file_path: str = "") -> str:
    """
    Filter and return anomalies of a specific type.
    Args:
        anomaly_type: One of: volume_spike, price_outlier, off_hours, duplicate_id,
                      missing_field, counterparty_concentration
        file_path: Optional CSV path.
    Returns:
        JSON list of matching flagged trades.
    """
    try:
        from tools.anomaly_tools import (
            detect_statistical_anomalies, detect_rule_anomalies
        )
        df = load_trades(file_path if file_path else None)
        all_flags = detect_statistical_anomalies(df) + detect_rule_anomalies(df)
        filtered = [f for f in all_flags if f["anomaly_type"] == anomaly_type]
        return json.dumps({
            "anomaly_type": anomaly_type,
            "count": len(filtered),
            "trades": filtered[:15],
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Build the ADK Agent ───────────────────────────────────────

anomaly_agent = Agent(
    name="trade_anomaly_detector",
    model=config.MODEL_NAME,
    description=(
        "Detects anomalies in trade data using statistical analysis (Z-score) and "
        "rule-based checks. Identifies volume spikes, price outliers, off-hours trades, "
        "duplicate trade IDs, missing fields, and counterparty concentration risk."
    ),
    instruction="""You are an expert trade surveillance analyst at an investment bank.

Your job is to detect suspicious patterns and anomalies in trade data.

When a user asks about anomalies, trade issues, or suspicious activity:
1. Call tool_load_and_detect_anomalies to run the full detection
2. Summarize the findings clearly: total flagged, breakdown by type, and highlight CRITICAL/HIGH items
3. For specific anomaly types, use tool_get_anomaly_by_type
4. Always mention the anomaly type, severity, and a brief explanation of the risk

Format your response with:
- A brief summary of overall findings
- A severity-organized breakdown
- The top 3–5 most concerning individual trades
- A recommended next step

Be precise and professional — this output goes to compliance officers.""",
    tools=[
        FunctionTool(tool_load_and_detect_anomalies),
        FunctionTool(tool_get_trade_stats),
        FunctionTool(tool_get_anomaly_by_type),
    ],
)
