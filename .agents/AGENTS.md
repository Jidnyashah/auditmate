# Workspace Rules — AuditMate Agent Boundaries & Hallucination Defense

This document defines the strict workspace behavior and coding guidelines for the AuditMate agents, tools, and UI prompts.

## 1. Compliance Q&A Boundaries
* **Strict Context Grounding**: All prompts for RAG Q&A (in `ui/dashboard.py` and `agents/qa_agent.py`) must contain explicit instructions forcing the LLM to only answer based on the provided context snippets.
* **Fallback Protocol**: If the context doesn't contain the answer, the LLM must output exactly: *"I cannot find the answer to this question in the provided regulatory knowledge base."*
* **Out-of-Scope Rejection**: The agent must reject questions unrelated to financial compliance, trade anomalies, and audit logs. General programming, recipes, and casual conversation queries must be blocked.

## 2. Report Generation Grounding
* **No Mock Data Fabrication**: The compliance report prompt (in `tools/report_tools.py`) must forbid generating counts, percentages, desk statistics, or severity tallies that are not explicitly present in the input `AUDIT DATA`.
* **State Verification**: If statistics are missing, the report must state *"No data available in audit logs"* rather than inventing data.

## 3. Tool Independence
* Anomaly checking, rule verification, and basic statistical tasks (like Z-score) must run on pure Python/Pandas logic. They must **never** delegate validation or computation to LLM generation.
