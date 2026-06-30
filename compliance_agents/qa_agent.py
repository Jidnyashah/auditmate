"""
agents/qa_agent.py
------------------
ADK agent: Audit Trail Q&A (RAG)
Answers natural language questions over regulations and audit logs.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

import config
from tools.rag_tools import (
    index_regulations,
    index_audit_trail,
    search_regulations,
    search_audit_trail,
)
from tools.trade_tools import load_trades, query_trades, get_audit_log, log_audit_event

try:
    import google.genai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


def _gemini_answer(question: str, context_chunks: list[dict], source_label: str) -> str:
    if not _GENAI_AVAILABLE or not config.GOOGLE_API_KEY:
        # Fallback: just return retrieved chunks
        texts = "\n\n".join([c["text"] for c in context_chunks])
        return f"**Retrieved Context ({source_label}):**\n\n{texts}"

    client = genai.Client(api_key=config.GOOGLE_API_KEY)
    context_text = "\n\n---\n\n".join(
        [f"[Source: {c.get('source', source_label)}]\n{c['text']}" for c in context_chunks]
    )
    prompt = f"""You are a regulatory compliance expert at AuditMate.
Your task is to answer the compliance question using ONLY the provided context.

CRITICAL BOUNDARIES:
1. Do not answer questions that are not related to financial regulations, compliance rules, trade audit logs, or AuditMate.
2. If the user asks general-knowledge or non-compliance questions, reject them immediately and politely state that you can only assist with regulatory compliance and trade audit data.
3. Base your answers strictly on the context below. Do not fabricate, hallucinate, or assume any facts not in the context.
4. If the answer is not in the context, state: "I cannot find the answer to this question in the provided regulatory knowledge base."

QUESTION: {question}

CONTEXT:
{context_text}

Provide a clear, concise answer with source citations in parentheses."""

    response = client.models.generate_content(
        model=config.MODEL_NAME,
        contents=prompt,
    )
    return response.text


# ── Tool functions ────────────────────────────────────────────

def tool_setup_knowledge_base() -> str:
    """
    Index regulatory documents into ChromaDB. Run this once before Q&A.
    Returns the number of chunks indexed.
    """
    try:
        n = index_regulations()
        return json.dumps({"status": "success", "chunks_indexed": n})
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_answer_regulation_question(question: str) -> str:
    """
    Answer a question about regulations (MiFID II, AML, Basel III) using RAG.
    Args:
        question: The compliance/regulation question to answer.
    Returns:
        A cited answer synthesized from the regulatory knowledge base.
    """
    try:
        # Auto-index if needed
        index_regulations()
        chunks = search_regulations(question, n_results=3)
        if not chunks:
            return json.dumps({"answer": "No relevant regulatory text found.", "sources": []})

        answer = _gemini_answer(question, chunks, "regulations")
        log_audit_event("QA_QUERY", f"Regulation Q: {question[:100]}", severity="INFO")
        return json.dumps({
            "question": question,
            "answer":   answer,
            "sources":  [c["source"] for c in chunks],
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_query_trade_data_nl(question: str, trader_id: str = "",
                              desk: str = "", instrument: str = "") -> str:
    """
    Answer natural language questions over trade data with optional filters.
    Args:
        question: What the user wants to know about the trades.
        trader_id: Optional trader to filter by (e.g. T042).
        desk: Optional desk name (FX, Equities, Rates, Credit, Commodities).
        instrument: Optional instrument symbol.
    Returns:
        A summary answer with supporting trade data.
    """
    try:
        df = load_trades()
        filtered = query_trades(
            df,
            trader_id=trader_id if trader_id else None,
            desk=desk if desk else None,
            instrument=instrument if instrument else None,
        )

        # Build context for Gemini
        sample = filtered.head(20).to_dict(orient="records")
        context_text = json.dumps(sample, indent=2, default=str)

        if not _GENAI_AVAILABLE or not config.GOOGLE_API_KEY:
            return json.dumps({
                "question": question,
                "records":  sample,
                "count":    len(filtered),
            }, indent=2)

        client = genai.Client(api_key=config.GOOGLE_API_KEY)
        prompt = f"""You are a compliance analyst. Answer this question about trade data.
Be specific and use the data provided. Include counts, amounts, and trader IDs where relevant.

QUESTION: {question}

TRADE DATA (up to 20 records):
{context_text}

Total matching records: {len(filtered)}"""

        response = client.models.generate_content(
            model=config.MODEL_NAME,
            contents=prompt,
        )
        log_audit_event("QA_TRADE_QUERY", f"Trade Q: {question[:100]}", severity="INFO")
        return json.dumps({
            "question": question,
            "answer":   response.text,
            "record_count": len(filtered),
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_search_audit_log(query: str) -> str:
    """
    Search the audit log for specific events using semantic search.
    Args:
        query: What to search for in the audit trail.
    Returns:
        Matching audit log entries.
    """
    try:
        # First try semantic search
        semantic = search_audit_trail(query, n_results=5)
        # Also get raw recent entries
        raw = get_audit_log(limit=20)

        log_audit_event("AUDIT_SEARCH", f"Searched audit trail: {query[:80]}", severity="INFO")
        return json.dumps({
            "query":           query,
            "semantic_results": semantic,
            "recent_log":      raw[:10],
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Build the ADK Agent ───────────────────────────────────────

qa_agent = Agent(
    name="audit_trail_qa",
    model=config.MODEL_NAME,
    description=(
        "Answers natural language compliance questions using RAG over regulatory documents "
        "(SEBI, RBI, PMLA, FEMA) and trade/transaction data. Also searches the audit trail for "
        "specific events and trader activity."
    ),
    instruction="""You are an expert compliance analyst and regulatory advisor for Indian financial markets.

You have access to:
1. A regulatory knowledge base (SEBI guidelines, RBI master directions, PMLA rules) — use tool_answer_regulation_question
2. Live trade data — use tool_query_trade_data_nl with filters
3. The audit trail — use tool_search_audit_log

When a user asks a question:
- If it's about regulations or rules → use tool_answer_regulation_question
- If it's about specific trades, traders, desks → use tool_query_trade_data_nl
- If it's about audit history or past events → use tool_search_audit_log
- If setup is needed → call tool_setup_knowledge_base first

Always:
- Cite sources for regulatory answers
- Be specific with numbers when answering trade questions
- Format responses clearly with bullet points or tables where helpful
- If uncertain, say so — do not hallucinate regulatory text

Example questions you can handle:
- "What is the SEBI block deal reporting threshold?"
- "Show me off-hours trades by trader T012"
- "What is the PMLA rule for structuring transactions?"
- "Were there any CRITICAL anomalies in the Credit segment?"
""",
    tools=[
        FunctionTool(tool_setup_knowledge_base),
        FunctionTool(tool_answer_regulation_question),
        FunctionTool(tool_query_trade_data_nl),
        FunctionTool(tool_search_audit_log),
    ],
)
