# AuditMate 🏦

**Enterprise Regulatory Compliance Agent** — Capstone Project for *5-Day AI Agents: Intensive Vibe Coding Course With Google*

👉 **Live Interactive Demo:** [https://auditmate.streamlit.app/](https://auditmate.streamlit.app/)

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

## Quick Start (Steps to run the app)

### 1. Clone / Navigate to the project
```bash
git clone https://github.com/Jidnyashah/auditmate.git
cd auditmate
```

### 2. Create and Activate a Virtual Environment
**On Windows (cmd/PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```
**On macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your API key
Edit the `.env` file in the project's root directory (`auditmate/.env`) and replace the placeholder with your actual Gemini API key.

*Note: This file is modified locally with your private credentials and must not be committed to GitHub with your actual key.*
```env
GOOGLE_API_KEY=your_actual_key_here
```

### 5. Verify API Key and Connection (Optional)
Run the diagnostic script to ensure your Gemini API key is configured and communicating correctly:
```bash
python scratch_check_api.py
```

### 6. Generate Synthetic Data
Generate both trade and transaction datasets:
```bash
python data/generate_trades.py
python data/generate_customer_transactions.py
```

### 7. Run the Dashboard
```bash
streamlit run ui/dashboard.py
```

---

## Architecture

```
auditmate/
├── compliance_agents/        # Formerly agents/
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
│   ├── generate_customer_transactions.py # Customer transaction generator
│   ├── synthetic_trades.csv  # 500 trades, ~10% anomalies
│   ├── compliance_rules.json # 10 compliance rules
│   └── regulations/          # MiFID II, AML, Basel III text
│
├── ui/
│   └── dashboard.py          # Streamlit dashboard (6 tabs)
│
├── config.py                 # All config, paths, thresholds
├── mcp_server.py             # Model Context Protocol server entrypoint
├── .env                      # API key (never commit!)
└── requirements.txt
```

---

## Agent Design (Google ADK)

```
Orchestrator Agent (Root - orchestrator.py)
├── trade_anomaly_detector (anomaly_agent.py)  ← 3 tools: detect, stats, filter-by-type
├── regulatory_summary_generator (summary_agent.py) ← 2 tools: generate, preview
└── audit_trail_qa (qa_agent.py)          ← 4 tools: setup KB, reg Q&A, trade Q&A, audit search
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

## Retrieval-Augmented Generation (RAG)

AuditMate uses RAG to answer queries regarding financial regulations without hallucinations:
*   **Knowledge Base**: Documents under `data/regulations/` (e.g., `sebi_rules.txt`, `rbi_rules.txt`, `pmla_rules.txt`) are partitioned into overlapping text chunks.
*   **Embeddings & Database**: Text chunks are converted into 384-dimensional vector embeddings using the `all-MiniLM-L6-v2` SentenceTransformer model and stored in a local, persistent **ChromaDB** vector database.
*   **Contextual Q&A**: When querying regulations, the **Q&A Agent** (`qa_agent.py`) retrieves the most relevant rules from ChromaDB and passes them as grounding context to the Gemini model to compile a cited regulatory answer.

---

## Key Concepts Demonstrated

- ✅ Multi-Agent Orchestration (ADK agent-as-tool pattern)
- ✅ Tool Use / Function Calling (10+ tools)
- ✅ Retrieval-Augmented Generation (ChromaDB)
- ✅ Structured Output (JSON, Markdown, PDF)
- ✅ Session State
- ✅ Real-world domain (banking compliance)
- ✅ Human-in-the-loop (flagged trades require review)

