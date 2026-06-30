"""
compliance_agents/summary_agent.py
-----------------------
ADK agent: Regulatory Summary Generator
Generates professional compliance report summaries using Gemini.
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
from tools.rule_checker import load_rules, check_rules, get_rule_summary
from tools.report_tools import (
    build_report_context,
    generate_report_with_gemini,
    export_report_markdown,
)


def tool_generate_compliance_report(file_path: str = "", date_range: str = "") -> str:
    """
    Generate a full regulatory compliance report for the trade data.
    Args:
        file_path: Optional path to CSV. Uses default synthetic data if empty.
        date_range: Optional string like '2024-01-01 to 2024-03-31'.
    Returns:
        The generated report text (Markdown) and the saved file path.
    """
    try:
        df = load_trades(file_path if file_path else None)
        stats = get_trade_stats(df)
        anomaly_summary = run_full_anomaly_detection(df)
        anomaly_summary.pop("flagged_trades", None)  # keep context small

        rules = load_rules()
        violations = check_rules(df, rules)
        rule_summary = get_rule_summary(violations)
        rule_summary.pop("violations", None)

        context = build_report_context(stats, anomaly_summary, rule_summary, date_range)
        report_text = generate_report_with_gemini(context)
        saved_path = export_report_markdown(report_text)

        log_audit_event(
            "REPORT_GENERATED",
            f"Compliance report saved to {saved_path}",
            severity="INFO",
        )

        return json.dumps({
            "status":     "success",
            "saved_path": saved_path,
            "report":     report_text,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_report_context_only(file_path: str = "") -> str:
    """
    Return the raw data context that would be used to generate a report,
    without calling Gemini. Useful for previewing the data.
    Args:
        file_path: Optional CSV path.
    Returns:
        JSON with stats, anomaly summary, and rule violations.
    """
    try:
        df = load_trades(file_path if file_path else None)
        stats = get_trade_stats(df)
        anomaly_summary = run_full_anomaly_detection(df)
        anomaly_summary.pop("flagged_trades", None)

        rules = load_rules()
        violations = check_rules(df, rules)
        rule_summary = get_rule_summary(violations)
        rule_summary.pop("violations", None)

        return json.dumps({
            "trade_stats":    stats,
            "anomaly_summary": anomaly_summary,
            "rule_summary":    rule_summary,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Build the ADK Agent ───────────────────────────────────────

summary_agent = Agent(
    name="regulatory_summary_generator",
    model=config.MODEL_NAME,
    description=(
        "Generates professional regulatory compliance report summaries using Gemini. "
        "Aggregates trade stats, anomaly detection results, and rule violations into "
        "a board-ready report with risk assessment and recommendations."
    ),
    instruction="""You are the Chief Compliance Officer drafting a regulatory report.

When asked to generate a compliance report or summary:
1. Call tool_generate_compliance_report to produce and save the full report
2. Present the report to the user in a clean, readable format
3. Highlight the overall risk rating, key anomaly count, and top 3 recommendations
4. Mention the saved file path so the user can download it

When asked for a data preview (without generating a report):
1. Call tool_get_report_context_only
2. Present a concise summary of the numbers

Always be professional, precise, and regulatory-appropriate.
Use clear headings and tables where helpful.""",
    tools=[
        FunctionTool(tool_generate_compliance_report),
        FunctionTool(tool_get_report_context_only),
    ],
)
