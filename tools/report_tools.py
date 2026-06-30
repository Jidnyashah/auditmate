"""
tools/report_tools.py
---------------------
Generates regulatory report summaries via Gemini and exports to Markdown/PDF.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

try:
    import google.genai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


def _get_gemini_client():
    if not _GENAI_AVAILABLE:
        raise ImportError("google-genai not installed. Run: pip install google-genai")
    if not config.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not set in .env")
    return genai.Client(api_key=config.GOOGLE_API_KEY)


def build_report_context(
    stats: dict,
    anomaly_summary: dict,
    rule_summary: dict,
    date_range: Optional[str] = None,
) -> str:
    """Build a structured context string for the Gemini report prompt."""
    ctx = f"""
=== AUDIT REPORT CONTEXT ===
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
Period: {date_range or stats.get('date_range', {}).get('from','N/A') + ' to ' + stats.get('date_range', {}).get('to','N/A')}

TRADE SUMMARY:
- Total Trades: {stats.get('total_trades', 0):,}
- Total Notional: ₹{stats.get('total_notional', 0):,.2f}
- Avg Notional:  ₹{stats.get('avg_notional', 0):,.2f}
- Unique Traders: {stats.get('unique_traders', 0)}
- Unique Counterparties: {stats.get('unique_counterparties', 0)}

TRADES BY DESK:
{json.dumps(stats.get('by_desk', []), indent=2)}

STATUS BREAKDOWN:
{json.dumps(stats.get('status_counts', {}), indent=2)}

ANOMALY DETECTION RESULTS:
- Total Flagged: {anomaly_summary.get('total_flagged', 0)}
- Unique Flagged Trades: {anomaly_summary.get('unique_trades', 0)}
- By Type: {json.dumps(anomaly_summary.get('by_type', {}), indent=2)}
- By Severity: {json.dumps(anomaly_summary.get('by_severity', {}), indent=2)}

RULE VIOLATIONS:
- Total Violations: {rule_summary.get('total_violations', 0)}
- By Severity: {json.dumps(rule_summary.get('by_severity', {}), indent=2)}
- By Rule: {json.dumps(rule_summary.get('by_rule', {}), indent=2)}
""".strip()
    return ctx


def generate_report_with_gemini(context: str) -> str:
    """
    Call Gemini to generate a professional regulatory compliance report.
    Returns the report as a Markdown string.
    """
    client = _get_gemini_client()

    prompt = f"""You are the Chief Compliance Officer at a major investment bank representing the AuditMate compliance system.
Based ONLY on the following audit data, generate a professional regulatory compliance report in Markdown format.

CRITICAL BOUNDARIES:
- The report must be based strictly on the provided audit data.
- Do not make up, hallucinate, or assume any statistics, desk data, counts, or anomalies that are not explicitly present in the AUDIT DATA below.
- If any required section lacks data in the provided AUDIT DATA, state "No data available in audit logs" for that section. Do not fabricate mock numbers.

The report must include these sections:
1. **Executive Summary** (3–5 sentences, plain language, based strictly on the provided data)
2. **Trade Activity Overview** (table of desk-level stats)
3. **Anomalies Detected** (structured table: Anomaly Type | Count | Severity | Risk Assessment)
4. **Rule Violations** (table: Rule ID | Rule Name | Violations | Severity | Regulation)
5. **Risk Assessment** (overall risk rating: LOW/MEDIUM/HIGH/CRITICAL, with justification based on data)
6. **Recommended Actions** (numbered list of specific, actionable recommendations based on the findings)
7. **Compliance Officer Sign-off Block** (date, signature placeholder, status)

Be precise, professional, and regulatory-appropriate. Use ⚠️ for HIGH severity and 🚨 for CRITICAL.

AUDIT DATA:
{context}"""

    response = client.models.generate_content(
        model=config.MODEL_NAME,
        contents=prompt,
    )
    return response.text


def export_report_markdown(report_text: str, filename: Optional[str] = None, output_dir: Optional[Path] = None) -> str:
    """Save report to a .md file. Returns the file path."""
    target_dir = output_dir if output_dir else config.REPORTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    if not filename:
        filename = f"audit_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
    path = target_dir / filename
    path.write_text(report_text, encoding="utf-8")
    return str(path)


def export_report_pdf(report_text: str, filename: Optional[str] = None) -> str:
    """Export report to PDF using reportlab. Returns the file path."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
    except ImportError:
        raise ImportError("reportlab not installed. Run: pip install reportlab")

    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if not filename:
        filename = f"audit_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = config.REPORTS_DIR / filename

    doc = SimpleDocTemplate(str(path), pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle("Title", parent=styles["Title"],
                                  fontSize=18, textColor=colors.HexColor("#1a237e"))
    story.append(Paragraph("AuditMate – Regulatory Compliance Report", title_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("<i>⚠️ <b>Demonstration Mode:</b> This report contains simulated sample data for educational and validation purposes only. No actual regulatory policies, confidential records, or real trade data are violated or exposed.</i>", styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                             styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))

    # Body — strip markdown and render as paragraphs
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)
    heading_style = ParagraphStyle("Heading", parent=styles["Heading2"],
                                    fontSize=12, textColor=colors.HexColor("#1a237e"))

    for line in report_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 0.2*cm))
        elif stripped.startswith("## ") or stripped.startswith("# "):
            text = stripped.lstrip("#").strip()
            story.append(Paragraph(text, heading_style))
            story.append(Spacer(1, 0.2*cm))
        elif stripped.startswith("**") and stripped.endswith("**"):
            story.append(Paragraph(f"<b>{stripped.strip('*')}</b>", body_style))
        else:
            # Replace markdown bold
            text = stripped.replace("**", "<b>", 1).replace("**", "</b>", 1)
            story.append(Paragraph(text, body_style))

    doc.build(story)
    return str(path)
