"""
mcp_server.py
-------------
Lightweight MCP (Model Context Protocol) Server for AuditMate.
Exposes tools to other agents/clients using FastMCP.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

import config
import pandas as pd
from fastmcp import FastMCP
from tools.anomaly_tools import run_full_anomaly_detection
from tools.rule_checker import load_rules, check_rules, get_rule_summary
from tools.rag_tools import search_regulations

# Initialize FastMCP Server
mcp = FastMCP("AuditMate")

@mcp.tool()
def run_anomaly_scan(dataset_type: str = "trades") -> str:
    """
    Run statistical and rule-based anomaly detection on the active dataset.
    Args:
        dataset_type: Either 'trades' (Trade Logs) or 'transactions' (Customer Wires/Transactions).
    Returns:
        JSON string of flagged anomalies and severity summary.
    """
    try:
        if dataset_type.lower() == "transactions":
            csv_path = config.DATA_DIR / "customer_transactions.csv"
            df = pd.read_csv(csv_path, parse_dates=["timestamp"])
            # Map columns to match trade logic
            df = df.rename(columns={
                "amount_usd": "notional",
                "customer_id": "trader_id",
                "account_type": "desk",
                "counterparty_name": "counterparty",
                "transaction_id": "trade_id",
                "channel": "venue"
            })
            df["instrument"] = df.get("transaction_type", "TXN")
            df["price"] = df["notional"]
            df["quantity"] = 1
        else:
            csv_path = config.TRADE_DATA_PATH
            df = pd.read_csv(csv_path, parse_dates=["timestamp"])

        results = run_full_anomaly_detection(df)
        flagged_list = results.get("flagged_trades", [])
        summary = {
            "total_flagged": results.get("total_flagged", 0),
            "by_type": results.get("by_type", {}),
            "by_severity": results.get("by_severity", {}),
            "sample_anomalies": flagged_list[:10]  # Return top 10 for conciseness
        }
        import json
        return json.dumps(summary, indent=2)
    except Exception as e:
        return f"Error running scan: {e}"

@mcp.tool()
def check_compliance_rules() -> str:
    """
    Validate all trades/transactions against the structured JSON rulebook.
    Returns:
        JSON string outlining rules, total violations, and affected records.
    """
    try:
        csv_path = config.TRADE_DATA_PATH
        df = pd.read_csv(csv_path, parse_dates=["timestamp"])
        rules = load_rules()
        violations = check_rules(df, rules)
        summary = get_rule_summary(violations)
        
        import json
        return json.dumps({
            "total_violations": summary.get("total_violations", 0),
            "unique_trades_affected": summary.get("unique_trades", 0),
            "by_severity": summary.get("by_severity", {}),
            "violations_sample": summary.get("violations", [])[:10]
        }, indent=2)
    except Exception as e:
        return f"Error checking rules: {e}"

@mcp.tool()
def search_regulations_kb(query: str) -> str:
    """
    Perform semantic search over indexed regulations (SEBI, RBI, PMLA).
    Args:
        query: Semantic query (e.g. 'What is the limit for large exposure?').
    Returns:
        JSON string of top matching text chunks with source documents.
    """
    try:
        chunks = search_regulations(query, n_results=3)
        import json
        return json.dumps(chunks, indent=2)
    except Exception as e:
        return f"Error searching KB: {e}"

if __name__ == "__main__":
    mcp.run()
