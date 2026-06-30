# AuditMate 🏦

**Enterprise Regulatory Compliance Agent** — Capstone Project for *5-Day AI Agents: Intensive Vibe Coding Course With Google*

> Powered by **Google ADK** · **Gemini 1.5 Flash** · **ChromaDB** · **Streamlit**

---

## What It Does

AuditMate is a multi-agent AI system that helps compliance and operations teams in banks and fintechs:

| Capability | Description |
|---|---|
| 🚨 **Trade Anomaly Detector** | Z-score + rule-based detection: volume spikes, price outliers, off-hours trades, duplicate IDs, missing fields |
| 📄 **Regulatory Summary Generator** | Gemini-synthesized professional compliance reports with risk assessment and recommendations |
| 📋 **Rule Checker** | 10 deterministic rules mapped to MiFID II, AML, Basel III, EMIR, MAR |
| 💬 **Audit Trail Q&A** | RAG over regulatory documents + natural language trade queries |
| 📡 **SLA Monitor** | Compliance SLA tracking dashboard |

---

## Quick Start

### 1. Clone / Navigate to the project
```bash
cd auditmate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Add your API key
Edit `.env`:
```
GOOGLE_API_KEY=your_actual_key_here
```

### 4. Generate synthetic trade data
```bash
python data/generate_trades.py
```

### 5. Run the dashboard
```bash
streamlit run ui/dashboard.py
```

---

## Architecture

```
auditmate/
├── agents/
│   ├── orchestrator.py       # Root ADK agent — routes all queries
│   ├── anomaly_agent.py      # Trade Anomaly Detector
│   ├── summary_agent.py      # Regulatory Summary Generator
│   └── qa_agent.py           # Audit Trail Q&A (RAG)
│
├── tools/
│   ├── trade_tools.py        # Data loading, querying, audit log
│   ├── anomaly_tools.py      # Statistical + rule-based detection
│   ├── rule_checker.py       # JSON rulebook compliance checker
│   ├── rag_tools.py          # ChromaDB indexing + semantic search
│   └── report_tools.py       # Gemini report generation + PDF export
│
├── data/
│   ├── generate_trades.py    # Synthetic trade data generator
│   ├── synthetic_trades.csv  # 500 trades, ~10% anomalies
│   ├── compliance_rules.json # 10 compliance rules
│   └── regulations/          # MiFID II, AML, Basel III text
│
├── ui/
│   └── dashboard.py          # Streamlit dashboard (6 tabs)
│
├── config.py                 # All config, paths, thresholds
├── .env                      # API key (never commit!)
└── requirements.txt
```

---

## Agent Design (Google ADK)

```
Orchestrator Agent (Root)
├── trade_anomaly_detector  ← 3 tools: detect, stats, filter-by-type
├── regulatory_summary_generator ← 2 tools: generate, preview
└── audit_trail_qa          ← 4 tools: setup KB, reg Q&A, trade Q&A, audit search
```

---

## Anomaly Types Detected

| Type | Method | Severity |
|---|---|---|
| Volume spike | Z-score > 3σ on quantity | HIGH |
| Price outlier | Z-score > 3σ per instrument | HIGH |
| Off-hours trade | Outside 08:00–18:00 | MEDIUM |
| Duplicate trade ID | `pandas.duplicated()` | CRITICAL |
| Missing fields | Null check on trader_id, venue, counterparty | HIGH |
| Counterparty concentration | Single CP > 60% of desk notional | HIGH |

---

## Tech Stack

| Component | Technology |
|---|---|
| LLM | AuditMate (Gemini 2.5 Flash) |
| Agent Framework | Google ADK (`google-adk`) |
| Vector Store | ChromaDB + all-MiniLM-L6-v2 embeddings |
| UI | Streamlit |
| Data | Pandas + SQLite |
| Charts | Plotly |
| Report Export | Markdown + ReportLab (PDF) |

---

## Example Queries

**Anomaly Detection:**
> "Run anomaly detection on today's trades"

**Regulation Q&A:**
> "What is the MiFID II large trade reporting threshold?"
> "What AML rules apply to counterparty concentration?"

**Trade Data Q&A:**
> "Show me all off-hours trades by trader T042"
> "Were there any CRITICAL anomalies in the Equities desk?"

**Report Generation:**
> "Generate a compliance report for Q1 2024"

---

## Capstone Concepts Demonstrated

- ✅ Multi-Agent Orchestration (ADK agent-as-tool pattern)
- ✅ Tool Use / Function Calling (10+ tools)
- ✅ Retrieval-Augmented Generation (ChromaDB)
- ✅ Structured Output (JSON, Markdown, PDF)
- ✅ Session State
- ✅ Real-world domain (banking compliance)
- ✅ Human-in-the-loop (flagged trades require review)
