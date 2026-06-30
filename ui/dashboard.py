"""
ui/dashboard.py
---------------
AuditMate Streamlit Dashboard — 6-tab enterprise compliance UI.
Run: streamlit run ui/dashboard.py
"""

import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import sys
from pathlib import Path
from datetime import datetime
import time

# ── Path setup ────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import config
from tools.trade_tools import load_trades, get_trade_stats, get_audit_log, log_audit_event
from tools.anomaly_tools import run_full_anomaly_detection
from tools.rule_checker import load_rules, check_rules, get_rule_summary
from tools.rag_tools import index_regulations, search_regulations

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="AuditMate – Regulatory Compliance Agent",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Light gradient background */
.stApp {
    background: linear-gradient(135deg, #fafafa 0%, #f1f3f5 50%, #fafafa 100%) !important;
    color: #212529 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%) !important;
    border-right: 1px solid #dee2e6 !important;
}
[data-testid="stSidebar"] p, 
[data-testid="stSidebar"] span, 
[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] h3, 
[data-testid="stSidebar"] label {
    color: #212529 !important;
}
[data-testid="stSidebar"] button, 
[data-testid="stSidebar"] button p,
[data-testid="stSidebar"] button span {
    color: white !important;
}

/* File Uploader styling */
[data-testid="stFileUploader"] section {
    background-color: #ffffff !important;
    border: 1px dashed #ced4da !important;
    border-radius: 8px !important;
    padding: 10px !important;
}
[data-testid="stFileUploader"] button {
    background: linear-gradient(135deg, #0d6efd, #0a58ca) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
[data-testid="stFileUploader"] button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(13, 110, 253, 0.4) !important;
}
[data-testid="stFileUploader"] div, [data-testid="stFileUploader"] span {
    color: #495057 !important;
}

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important;
    border: 1px solid #dee2e6 !important;
    border-radius: 12px !important;
    padding: 20px !important;
    text-align: center !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
.metric-card:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.1) !important;
}
.metric-value {
    font-size: 2rem !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, #0d6efd, #0a58ca) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}
.metric-label {
    font-size: 0.8rem !important;
    color: #495057 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    margin-top: 4px !important;
}
.metric-delta {
    font-size: 0.85rem !important;
    margin-top: 6px !important;
}

/* Header banner */
.header-banner {
    background: linear-gradient(135deg, #1a237e 0%, #0d47a1 50%, #01579b 100%) !important;
    border-radius: 16px !important;
    padding: 32px !important;
    margin-bottom: 24px !important;
    border: 1px solid #1565c0 !important;
    position: relative !important;
    overflow: hidden !important;
}
.header-banner::before {
    content: '' !important;
    position: absolute !important;
    top: -50% !important;
    right: -10% !important;
    width: 300px !important;
    height: 300px !important;
    background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 70%) !important;
    border-radius: 50% !important;
}
.header-title {
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    margin: 0 !important;
}
.header-subtitle {
    font-size: 1rem !important;
    color: rgba(255,255,255,0.75) !important;
    margin-top: 8px !important;
}
.header-badge {
    display: inline-block !important;
    background: rgba(255,255,255,0.15) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    border-radius: 20px !important;
    padding: 4px 14px !important;
    font-size: 0.75rem !important;
    color: #fff !important;
    margin-top: 12px !important;
    margin-right: 8px !important;
}

/* Severity badges */
.badge-critical { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;
                  border-radius: 6px; padding: 2px 8px; font-size: 0.75rem; font-weight: 600; }
.badge-high     { background: #fff3cd; color: #856404; border: 1px solid #ffeeba;
                  border-radius: 6px; padding: 2px 8px; font-size: 0.75rem; font-weight: 600; }
.badge-medium   { background: #fff3cd; color: #856404; border: 1px solid #ffeeba;
                  border-radius: 6px; padding: 2px 8px; font-size: 0.75rem; font-weight: 600; }
.badge-low      { background: #d4edda; color: #155724; border: 1px solid #c3e6cb;
                  border-radius: 6px; padding: 2px 8px; font-size: 0.75rem; font-weight: 600; }

/* Chat bubbles */
.chat-user {
    background: linear-gradient(135deg, #0d6efd, #0a58ca) !important;
    border-radius: 16px 16px 4px 16px !important;
    padding: 12px 16px !important;
    margin: 8px 0 !important;
    margin-left: 20% !important;
    color: #ffffff !important;
    font-size: 0.9rem !important;
}
.chat-agent {
    background: linear-gradient(135deg, #ffffff, #f8f9fa) !important;
    border: 1px solid #dee2e6 !important;
    border-radius: 16px 16px 16px 4px !important;
    padding: 12px 16px !important;
    margin: 8px 0 !important;
    margin-right: 10% !important;
    color: #212529 !important;
    font-size: 0.9rem !important;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    background: #e9ecef !important;
    border-radius: 10px !important;
    padding: 4px !important;
    border: 1px solid #dee2e6 !important;
}
.stTabs [data-baseweb="tab"] {
    color: #495057 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #0d6efd, #0a58ca) !important;
    color: #ffffff !important;
}

/* Dataframe */
.dataframe { border-radius: 8px; overflow: hidden; }

/* Buttons */
.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button {
    background: linear-gradient(135deg, #0d6efd, #0a58ca) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
.stButton>button:hover, .stFormSubmitButton>button:hover, .stDownloadButton>button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(13, 110, 253, 0.4) !important;
}

/* Alert boxes */
.alert-critical {
    background: rgba(220,53,69,0.15) !important;
    border-left: 4px solid #dc3545 !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    margin: 8px 0 !important;
    color: #721c24 !important;
}
.alert-info {
    background: rgba(13,110,253,0.1) !important;
    border-left: 4px solid #0d6efd !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    margin: 8px 0 !important;
    color: #084298 !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = None
if "loaded_filename" not in st.session_state:
    st.session_state.loaded_filename = None
if "anomaly_results" not in st.session_state:
    st.session_state.anomaly_results = None
if "rule_violations" not in st.session_state:
    st.session_state.rule_violations = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "report_text" not in st.session_state:
    st.session_state.report_text = None
if "kb_indexed" not in st.session_state:
    st.session_state.kb_indexed = False
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None
if "resolved_trade_ids" not in st.session_state:
    st.session_state.resolved_trade_ids = set()


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:left; padding: 8px 0; margin-bottom: 5px;">
        <span style="font-size:1.6rem; font-weight:700; color:#0d6efd;">🏦 AuditMate</span>
        <div style="font-size:0.75rem; color:#495057;">Regulatory Compliance Agent</div>
    </div>
    """, unsafe_allow_html=True)

    # API and Dataset status in a single row
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.session_state.df is not None:
            st.markdown(f"<div style='font-size:0.75rem; padding: 6px 4px; background-color: #d4edda; border-radius: 6px; text-align: center; border: 1px solid #c3e6cb; color: #155724; font-weight: 500;'>🟢 {len(st.session_state.df):,} rows</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='font-size:0.75rem; padding: 6px 4px; background-color: #fff3cd; border-radius: 6px; text-align: center; border: 1px solid #ffeeba; color: #856404; font-weight: 500;'>🟡 No Data</div>", unsafe_allow_html=True)
    with col_s2:
        api_ok = bool(config.GOOGLE_API_KEY and config.GOOGLE_API_KEY != "your_key_here")
        if api_ok:
            st.markdown("<div style='font-size:0.75rem; padding: 6px 4px; background-color: #d4edda; border-radius: 6px; text-align: center; border: 1px solid #c3e6cb; color: #155724; font-weight: 500;'>🟢 API Active</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='font-size:0.75rem; padding: 6px 4px; background-color: #f8d7da; border-radius: 6px; text-align: center; border: 1px solid #f5c6cb; color: #721c24; font-weight: 500;'>🔴 API Offline</div>", unsafe_allow_html=True)

    # PART 1: Logo till API Active status
    st.markdown("<hr style='border-top: 1px solid #ced4da; margin: 15px 0 5px 0;'>", unsafe_allow_html=True)
    st.markdown("<div style='margin-top: 60px;'></div>", unsafe_allow_html=True)

    # PART 2: Trade Data and options
    st.markdown("**📂 Trade Data**")
    uploaded = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")
    st.markdown("<div style='font-size:0.85rem; color:#495057; margin-top:-8px; margin-bottom:12px;'>ℹ️ CSV limit: 200MB<br>📂 Paths: <code style='font-size:0.85rem; color:#155724;'>data/synthetic_trades.csv</code> or <code style='font-size:0.85rem; color:#155724;'>data/customer_transactions.csv</code></div>", unsafe_allow_html=True)

    if uploaded:
        if st.session_state.get("loaded_filename") != uploaded.name:
            try:
                df = pd.read_csv(uploaded, parse_dates=["timestamp"])
                if "customer_id" in df.columns or "amount_usd" in df.columns:
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
                    if "quantity" not in df.columns:
                        df["quantity"] = 1
                st.session_state.df = df
                st.session_state.loaded_filename = uploaded.name
                st.session_state.anomaly_results = None
                st.session_state.rule_violations = None
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.session_state.loaded_filename = None
        st.markdown("<hr style='border-top: 1px solid #dee2e6; margin: 15px 0 5px 0;'>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)

        # PART 3: Preloaded Dataset and below
        st.markdown("**📊 Preloaded Datasets**")
        col_t, col_c = st.columns(2)
        with col_t:
            if st.button("📈 Trade Logs", use_container_width=True):
                try:
                    st.session_state.df = load_trades()
                    st.session_state.loaded_filename = None
                    st.session_state.anomaly_results = None
                    st.session_state.rule_violations = None
                except FileNotFoundError:
                    st.error("Run: python data/generate_trades.py first")
        with col_c:
            if st.button("💳 Transactions", use_container_width=True):
                try:
                    df = pd.read_csv(config.DATA_DIR / "customer_transactions.csv", parse_dates=["timestamp"])
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
                    if "quantity" not in df.columns:
                        df["quantity"] = 1
                    st.session_state.df = df
                    st.session_state.loaded_filename = None
                    st.session_state.anomaly_results = None
                    st.session_state.rule_violations = None
                except FileNotFoundError:
                    st.error("Run python data/generate_customer_transactions.py first")

    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.7rem;color:#8b949e; border-top: 1px solid #dee2e6; padding-top: 8px;'>v1.0.0 · {datetime.utcnow().strftime('%Y-%m-%d')}</div>",
                unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────
st.markdown("""
<div class="header-banner">
    <div class="header-title">🏦 AuditMate</div>
    <div class="header-subtitle">Enterprise Regulatory Compliance Agent · Powered by AuditMate & ADK</div>
    <span class="header-badge">SEBI</span>
    <span class="header-badge">RBI</span>
    <span class="header-badge">PMLA</span>
    <span class="header-badge">FEMA</span>
    <span class="header-badge">CCIL</span>
    <div style="font-size:0.85rem; margin-top:8px; color:#fbc02d; font-weight:bold;">
        ⚠️ Demonstration Mode: All trades, wires, and customer names are simulated sample records. 
        No real regulatory policies or confidentiality structures are violated.
    </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────
tabs = st.tabs([
    "📊 Dashboard",
    "🚨 Anomaly Detector",
    "📋 Rule Checker",
    "📄 Report Generator",
    "💬 Compliance Q&A",
    "📡 SLA Monitor",
])


# ═══════════════════════════════════════════════════════════════
# TAB 1: DASHBOARD
# ═══════════════════════════════════════════════════════════════
with tabs[0]:
    if st.session_state.df is None:
        st.markdown("""
        <div class="alert-info">
            <b>👋 Welcome to AuditMate!</b><br>
            Load trade data from the sidebar to get started.
            Use <b>Load Sample Data</b> to explore with 500 synthetic trades.
        </div>
        """, unsafe_allow_html=True)
    else:
        df = st.session_state.df
        stats = get_trade_stats(df)

        # KPI row
        col1, col2, col3, col4, col5 = st.columns(5)
        kpis = [
            (col1, "Total Trades", f"{stats['total_trades']:,}", ""),
            (col2, "Total Volume", f"₹{stats['total_notional']/1e7:.2f} Cr" if stats['total_notional'] >= 1e7 else f"₹{stats['total_notional']:,.0f}", ""),
            (col3, "Avg Vol / Trade", f"₹{stats['avg_notional']:,.0f}", ""),
            (col4, "Unique Entities", f"{stats['unique_traders']}", ""),
            (col5, "Counterparties", f"{stats['unique_counterparties']}", ""),
        ]
        for col, label, value, delta in kpis:
            with col:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_l, col_r = st.columns(2)

        with col_l:
            # Trades by desk — bar chart
            desk_df = pd.DataFrame(stats["by_desk"])
            fig = px.bar(
                desk_df, x="desk", y="total_notional",
                color="desk", title="Total Volume by Segment (₹)",
                color_discrete_sequence=px.colors.qualitative.Bold,
                template="plotly_white",
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False, title_font_size=14,
            )
            st.plotly_chart(fig, use_container_width=True, config={'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d'], 'displaylogo': False})

        with col_r:
            # Status donut
            status_df = pd.DataFrame(
                list(stats["status_counts"].items()), columns=["Status", "Count"]
            )
            fig2 = px.pie(
                status_df, names="Status", values="Count",
                title="Trade Status Distribution",
                hole=0.55,
                color_discrete_sequence=["#4ade80", "#facc15", "#f87171"],
                template="plotly_white",
            )
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                title_font_size=14,
            )
            st.plotly_chart(fig2, use_container_width=True, config={'displaylogo': False})

        # Trade count over time
        df_copy = df.copy()
        df_copy["date"] = df_copy["timestamp"].dt.date
        daily = df_copy.groupby("date").size().reset_index(name="count")
        fig3 = px.area(
            daily, x="date", y="count",
            title="Daily Trade Volume",
            template="plotly_white",
            color_discrete_sequence=["#58a6ff"],
        )
        fig3.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            title_font_size=14,
        )
        st.plotly_chart(fig3, use_container_width=True, config={'modeBarButtonsToRemove': ['zoom2d', 'pan2d'], 'displaylogo': False})


# ═══════════════════════════════════════════════════════════════
# TAB 2: ANOMALY DETECTOR
# ═══════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("🚨 Trade Anomaly Detector")
    st.caption("Statistical (Z-score) + Rule-based anomaly detection")

    if st.session_state.df is None:
        st.warning("Load trade data first from the sidebar.")
    else:
        if st.button("🔍 Run Anomaly Detection", use_container_width=False):
            import time
            status_placeholder = st.empty()
            with st.spinner("Running Anomaly Scan in progress..."):
                with status_placeholder.container():
                    with st.status("Scanning for anomalies...", expanded=True) as status:
                        st.write("🔍 Scanning trade database...")
                        time.sleep(0.5)
                        st.write("📊 Calculating statistical Z-scores for prices & quantities...")
                        time.sleep(0.6)
                        st.write("📋 Evaluating deterministic compliance rules...")
                        time.sleep(0.5)
                        st.write("⚖️ Consolidating anomaly triggers and severity levels...")
                        res = run_full_anomaly_detection(st.session_state.df)
                        # Filter out resolved trades
                        res["flagged_trades"] = [t for t in res["flagged_trades"] if t["trade_id"] not in st.session_state.resolved_trade_ids]
                        res["total_flagged"] = len(res["flagged_trades"])
                        if res["flagged_trades"]:
                            df_f = pd.DataFrame(res["flagged_trades"])
                            res["unique_trades"] = int(df_f["trade_id"].nunique())
                            res["by_type"] = df_f["anomaly_type"].value_counts().to_dict()
                            res["by_severity"] = df_f["severity"].value_counts().to_dict()
                            res["by_desk"] = df_f["desk"].value_counts().to_dict()
                        else:
                            res["unique_trades"] = 0
                            res["by_type"] = {}
                            res["by_severity"] = {}
                            res["by_desk"] = {}
                        st.session_state.anomaly_results = res
                        log_audit_event("ANOMALY_SCAN_UI",
                                        f"UI triggered anomaly scan on {len(st.session_state.df)} trades",
                                        "INFO")
                        status.update(label="✅ Anomaly Scan Complete", state="complete")

        if st.session_state.anomaly_results:
            res = st.session_state.anomaly_results

            # Summary KPIs
            c1, c2, c3, c4 = st.columns(4)
            severity_map = res.get("by_severity", {})
            with c1:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-value" style="color:#ef4444">{res['total_flagged']}</div>
                    <div class="metric-label">Total Flags</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-value" style="color:#ef4444">{severity_map.get('CRITICAL',0)}</div>
                    <div class="metric-label">Critical</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-value" style="color:#fb923c">{severity_map.get('HIGH',0)}</div>
                    <div class="metric-label">High</div></div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-value" style="color:#fbbf24">{severity_map.get('MEDIUM',0)}</div>
                    <div class="metric-label">Medium</div></div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            col_a, col_b = st.columns(2)

            with col_a:
                # Anomalies by type
                type_df = pd.DataFrame(
                    list(res["by_type"].items()), columns=["Type", "Count"]
                )
                fig = px.bar(
                    type_df, x="Count", y="Type", orientation="h",
                    title="Anomalies by Type",
                    color="Count",
                    color_continuous_scale=["#4ade80", "#fbbf24", "#ef4444"],
                    template="plotly_white",
                )
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    showlegend=False, coloraxis_showscale=False, title_font_size=13,
                )
                st.plotly_chart(fig, use_container_width=True, config={'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d'], 'displaylogo': False})

            with col_b:
                # Anomalies by desk
                desk_data = res.get("by_desk", {})
                if desk_data:
                    desk_df2 = pd.DataFrame(list(desk_data.items()), columns=["Desk", "Count"])
                    fig2 = px.pie(
                        desk_df2, names="Desk", values="Count",
                        title="Anomalies by Desk", hole=0.5,
                        color_discrete_sequence=px.colors.qualitative.Bold,
                        template="plotly_white",
                    )
                    fig2.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        title_font_size=13,
                    )
                    st.plotly_chart(fig2, use_container_width=True, config={'displaylogo': False})

            # Flagged trades table
            st.markdown("#### 🔴 Flagged Trades")
            if res["flagged_trades"]:
                flagged_df = pd.DataFrame(res["flagged_trades"])
                # Color-code severity
                severity_filter = st.selectbox(
                    "Filter by Severity",
                    ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    key="sev_filter",
                )
                if severity_filter != "ALL":
                    flagged_df = flagged_df[flagged_df["severity"] == severity_filter]
                st.dataframe(
                    flagged_df[["trade_id","anomaly_type","severity","reason","desk","trader_id","timestamp"]],
                    use_container_width=True,
                    height=350,
                )

                # Human-in-the-Loop actions
                st.markdown("---")
                st.markdown("### 🧑‍✈️ Audit actions")
                
                unique_flagged_ids = flagged_df["trade_id"].unique() if not flagged_df.empty else []
                if len(unique_flagged_ids) > 0:
                    col_sel, col_act = st.columns([2, 3])
                    with col_sel:
                        selected_trade_id = st.selectbox(
                            "Select Flagged Trade ID to Audit",
                            unique_flagged_ids,
                            key="audit_trade_selectbox"
                        )
                        # Find details of selected trade
                        trade_detail = next(t for t in res["flagged_trades"] if t["trade_id"] == selected_trade_id)
                        st.markdown(f"""
                        **Details of Trade {selected_trade_id}**:
                        * **Anomaly Type**: `{trade_detail['anomaly_type']}`
                        * **Severity**: `{trade_detail['severity']}`
                        * **Desk / Segment**: `{trade_detail['desk']}`
                        * **Trader ID**: `{trade_detail['trader_id']}`
                        * **Timestamp**: `{trade_detail['timestamp']}`
                        * **Reason**: *{trade_detail['reason']}*
                        """)
                    
                    with col_act:
                        action_type = st.radio(
                            "Select Action",
                            ["Resolve & Dismiss Flag", "Generate AI Escalation Draft"],
                            key="audit_action_radio"
                        )
                        
                        if action_type == "Resolve & Dismiss Flag":
                            if st.button("✔️ Resolve Trade Anomaly", use_container_width=True):
                                st.session_state.resolved_trade_ids.add(selected_trade_id)
                                # Filter out from current session state results
                                res["flagged_trades"] = [t for t in res["flagged_trades"] if t["trade_id"] != selected_trade_id]
                                res["total_flagged"] = len(res["flagged_trades"])
                                if res["flagged_trades"]:
                                    df_f = pd.DataFrame(res["flagged_trades"])
                                    res["unique_trades"] = int(df_f["trade_id"].nunique())
                                    res["by_type"] = df_f["anomaly_type"].value_counts().to_dict()
                                    res["by_severity"] = df_f["severity"].value_counts().to_dict()
                                    res["by_desk"] = df_f["desk"].value_counts().to_dict()
                                else:
                                    res["unique_trades"] = 0
                                    res["by_type"] = {}
                                    res["by_severity"] = {}
                                    res["by_desk"] = {}
                                st.session_state.anomaly_results = res
                                log_audit_event("RESOLVE_ANOMALY_UI", f"Compliance officer resolved/dismissed anomaly on trade {selected_trade_id}", "HIGH")
                                st.success(f"✔️ Trade {selected_trade_id} successfully marked as resolved and dismissed.")
                                time.sleep(1.0)
                                st.rerun()
                                
                        elif action_type == "Generate AI Escalation Draft":
                            if st.button("🤖 Generate Escalation Email", use_container_width=True):
                                if not (config.GOOGLE_API_KEY and config.GOOGLE_API_KEY != "your_key_here"):
                                    st.error("Gemini API key is not configured.")
                                else:
                                    with st.spinner("Drafting escalation letter..."):
                                        try:
                                            import google.genai as genai
                                            client = genai.Client(api_key=config.GOOGLE_API_KEY)
                                            prompt = f"""You are the Lead Compliance Officer at AuditMate.
Draft a professional and formal compliance query email to the Trader ({trade_detail['trader_id']}) regarding a flagged trade anomaly.

Trade Details:
- Trade ID: {trade_detail['trade_id']}
- Segment/Desk: {trade_detail['desk']}
- Timestamp: {trade_detail['timestamp']}
- Anomaly Type: {trade_detail['anomaly_type']}
- Severity Level: {trade_detail['severity']}
- Reason flagged: {trade_detail['reason']}

Requirements:
1. Explain exactly why the trade was flagged by the AuditMate anomaly detection systems.
2. Formally request a detailed explanation of the transaction context, pricing, or volume triggers.
3. Keep the tone professional, objective, and firm.
4. Include a deadline of 24 hours for a response.
5. Provide a placeholder for signature: 'Compliance Audit Team, AuditMate'."""
                                            resp = client.models.generate_content(
                                                model=config.MODEL_NAME, contents=prompt
                                            )
                                            st.markdown("**Generated Escalation Draft:**")
                                            st.text_area("Escalation Email Content", value=resp.text, height=250, key="escalation_draft_textarea")
                                            log_audit_event("ESCALATE_ANOMALY_UI", f"Compliance officer generated escalation query for trade {selected_trade_id} (trader {trade_detail['trader_id']})", "INFO")
                                        except Exception as e:
                                            st.error(f"Error drafting email: {e}")
                else:
                    st.info("No flagged trades to review.")


# ═══════════════════════════════════════════════════════════════
# TAB 3: RULE CHECKER
# ═══════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("📋 Compliance Rule Checker")
    st.caption("10 deterministic rules mapped to MiFID II, AML, Basel III, EMIR, MAR")

    if st.session_state.df is None:
        st.warning("Load trade data first from the sidebar.")
    else:
        # Show rulebook
        with st.expander("📖 View Compliance Rulebook"):
            rules = load_rules()
            rules_df = pd.DataFrame([{
                "ID": r["id"], "Rule": r["name"],
                "Severity": r["severity"], "Regulation": r["regulation"]
            } for r in rules])
            st.dataframe(rules_df, use_container_width=True)

        if st.button("✅ Run Rule Check", use_container_width=False):
            import time
            status_placeholder = st.empty()
            with st.spinner("Running Compliance Rule Check in progress..."):
                with status_placeholder.container():
                    with st.status("Running Compliance Rule Check...", expanded=True) as status:
                        st.write("📖 Loading compliance rulebook definitions...")
                        time.sleep(0.5)
                        st.write("🔍 Analyzing loaded trade dataset against rule parameters...")
                        time.sleep(0.6)
                        rules = load_rules()
                        violations = check_rules(st.session_state.df, rules)
                        st.write("🚨 Flagging potential regulatory breaches...")
                        time.sleep(0.5)
                        st.write("📊 Summarizing compliance violations...")
                        st.session_state.rule_violations = get_rule_summary(violations)
                        log_audit_event("RULE_CHECK_UI",
                                        f"Rule check: {st.session_state.rule_violations['total_violations']} violations",
                                        "INFO")
                        status.update(label="✅ Rule Check Complete", state="complete")

        if st.session_state.rule_violations:
            rv = st.session_state.rule_violations
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-value" style="color:#ef4444">{rv['total_violations']}</div>
                    <div class="metric-label">Total Violations</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-value">{rv.get('unique_trades',0)}</div>
                    <div class="metric-label">Unique Trades Affected</div></div>""", unsafe_allow_html=True)
            with c3:
                crit = rv.get("by_severity",{}).get("CRITICAL", 0)
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-value" style="color:#ef4444">{crit}</div>
                    <div class="metric-label">Critical Violations</div></div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 🔴 Rule Violations Detail")
            if rv.get("violations"):
                vdf = pd.DataFrame(rv["violations"])
                st.dataframe(
                    vdf[["rule_id","rule_name","trade_id","severity","detail","regulation"]],
                    use_container_width=True, height=350,
                )


# ═══════════════════════════════════════════════════════════════
# TAB 4: REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("📄 Regulatory Report Generator")
    st.caption("AI-generated compliance report using AuditMate")

    if not (config.GOOGLE_API_KEY and config.GOOGLE_API_KEY != "your_key_here"):
        st.markdown("""<div class="alert-critical">
            🔴 <b>Gemini API key not configured.</b><br>
            Add your key to <code>.env</code>: <code>GOOGLE_API_KEY=your_key_here</code>
        </div>""", unsafe_allow_html=True)
    elif st.session_state.df is None:
        st.warning("Load trade data first from the sidebar.")
    else:
        col_dr, col_sl = st.columns(2)
        with col_dr:
            date_range = st.text_input(
                "Date Range (optional)", placeholder="e.g. 2024-01-01 to 2024-03-31"
            )
        with col_sl:
            save_loc = st.selectbox(
                "Save Location",
                ["Default (reports/)", "Downloads"],
                key="report_save_loc"
            )

        if st.button("🤖 Generate Compliance Report", use_container_width=False):
            import time
            saved_path = None
            err = None
            status_placeholder = st.empty()
            with st.spinner("Drafting Compliance Report in progress..."):
                with status_placeholder.container():
                    with st.status("Drafting Compliance Report...", expanded=True) as status:
                        st.write("📊 Aggregating statistical anomalies and rule check summaries...")
                        try:
                            from tools.report_tools import (
                                build_report_context, generate_report_with_gemini, export_report_markdown
                            )
                            from tools.anomaly_tools import run_full_anomaly_detection
                            from tools.rule_checker import load_rules, check_rules, get_rule_summary

                            stats = get_trade_stats(st.session_state.df)
                            anomaly_summary = run_full_anomaly_detection(st.session_state.df)
                            anomaly_summary.pop("flagged_trades", None)

                            rules = load_rules()
                            violations = check_rules(st.session_state.df, rules)
                            rule_summary = get_rule_summary(violations)
                            rule_summary.pop("violations", None)
                            time.sleep(0.5)

                            st.write("🧠 Formatting context for Gemini ADK summary agent...")
                            context = build_report_context(stats, anomaly_summary, rule_summary, date_range)
                            time.sleep(0.5)

                            st.write("✍️ Drafting professional executive commentary and recommended actions via Gemini...")
                            report_text = generate_report_with_gemini(context)

                            st.write("💾 Saving report output to destination folder...")
                            from pathlib import Path
                            if save_loc == "Downloads":
                                output_dir = Path.home() / "Downloads"
                            else:
                                output_dir = config.REPORTS_DIR

                            saved_path = export_report_markdown(report_text, output_dir=output_dir)
                            time.sleep(0.4)

                            st.session_state.report_text = report_text
                            log_audit_event("REPORT_GEN_UI", f"Report saved: {saved_path}", "INFO")
                            status.update(label="✅ Report Drafted Successfully", state="complete")
                        except Exception as e:
                            status.update(label="❌ Report Generation Failed", state="error")
                            err = e

            if saved_path:
                st.markdown(f"<div style='font-size:1.05rem; padding:12px; background-color:#d4edda; border:1px solid #c3e6cb; border-radius:8px; color:#155724; margin-bottom:15px;'>✅ Report generated and saved to: <code style='font-size:1.05rem; color:#155724;'>{saved_path}</code></div>", unsafe_allow_html=True)
            elif err:
                st.error(f"Error: {err}")

        if st.session_state.report_text:
            st.markdown("---")
            st.markdown(st.session_state.report_text)
            st.download_button(
                label="⬇️ Download Report (.md)",
                data=st.session_state.report_text,
                file_name=f"audit_report_{datetime.utcnow().strftime('%Y%m%d')}.md",
                mime="text/markdown",
            )


# ═══════════════════════════════════════════════════════════════
# TAB 5: COMPLIANCE Q&A
# ═══════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("💬 Compliance Q&A Agent")
    st.caption("RAG-powered assistant — ask anything about regulations or your trade data")

    if not (config.GOOGLE_API_KEY and config.GOOGLE_API_KEY != "your_key_here"):
        st.markdown("""<div class="alert-critical">
            🔴 <b>Gemini API key required for Q&A.</b>
        </div>""", unsafe_allow_html=True)
    else:
        # Auto-index regulations
        if not st.session_state.kb_indexed:
            with st.spinner("Indexing regulatory knowledge base..."):
                try:
                    n = index_regulations()
                    st.session_state.kb_indexed = True
                except Exception as e:
                    st.warning(f"Could not index regulations: {e}")

        # Example queries
        st.markdown("**Try asking:**")
        example_cols = st.columns(3)
        examples = [
            "What is the SEBI block deal threshold?",
            "Explain the RBI Large Exposure Framework limits",
            "What is structuring under PMLA guidelines?",
        ]
        is_processing = st.session_state.get("is_processing", False)
        user_input_to_process = None
        for i, (col, ex) in enumerate(zip(example_cols, examples)):
            with col:
                if st.button(f"💡 {ex[:45]}...", key=f"ex_{i}", use_container_width=True, disabled=is_processing):
                    user_input_to_process = ex

        st.divider()

        # Chat display
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f"""<div class="chat-user">👤 {msg['content']}</div>""",
                                unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="chat-agent">🤖 {msg['content']}</div>""",
                                unsafe_allow_html=True)

        # Input
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_input(
                "Ask a compliance question...",
                placeholder="e.g. What is the SEBI block deal threshold?",
                label_visibility="collapsed",
                disabled=is_processing,
            )
            submitted = st.form_submit_button("Send ➤", use_container_width=False, disabled=is_processing)

        if submitted and user_input.strip() and not is_processing:
            user_input_to_process = user_input.strip()

        # Trigger processing state
        if user_input_to_process:
            st.session_state.pending_query = user_input_to_process
            st.session_state.is_processing = True
            st.rerun()

        # Process the pending query
        if st.session_state.is_processing and st.session_state.pending_query:
            query = st.session_state.pending_query
            st.session_state.chat_history.append({"role": "user", "content": query})
            import time
            status_placeholder = st.empty()
            with st.spinner("Compliance Q&A Agent is thinking..."):
                with status_placeholder.container():
                    with st.status("Agent thinking...", expanded=True) as status:
                        st.write("🔍 Querying ChromaDB Vector database...")
                        try:
                            chunks = search_regulations(query, n_results=3)
                            time.sleep(0.5)
                            st.write("🔀 Routing prompt through ADK Orchestrator...")
                            time.sleep(0.5)
                            st.write("🧠 Synthesizing response with Gemini compliance agent...")
                            if chunks:
                                import google.genai as genai
                                client = genai.Client(api_key=config.GOOGLE_API_KEY)
                                ctx = "\n\n---\n\n".join(
                                    [f"[{c['source']}]\n{c['text']}" for c in chunks]
                                )
                                prompt = f"""You are a regulatory compliance expert at AuditMate.
Your task is to answer compliance questions using ONLY the provided context snippets.

CRITICAL BOUNDARIES:
1. Do not answer questions that are not related to financial regulations, compliance rules, trade audit logs, or AuditMate.
2. If the user asks general-knowledge or non-compliance questions, reject them immediately and politely state that you can only assist with regulatory compliance and trade audit data.
3. Base your answers strictly on the context below. Do not fabricate, hallucinate, or assume any facts not in the context.
4. If the answer is not in the context, state: "I cannot find the answer to this question in the provided regulatory knowledge base."

Question: {query}

Context:
{ctx}"""
                                resp = client.models.generate_content(
                                    model=config.MODEL_NAME, contents=prompt
                                )
                                answer = resp.text
                            else:
                                answer = "I couldn't find relevant information in the regulatory knowledge base for that question."

                            st.session_state.chat_history.append({"role": "agent", "content": answer})
                            log_audit_event("QA_UI", query[:100], "INFO")
                            status.update(label="✅ Answer ready", state="complete")
                        except Exception as e:
                            status.update(label="❌ Agent error", state="error")
                            st.error(f"Error: {e}")
                        finally:
                            st.session_state.pending_query = None
                            st.session_state.is_processing = False
                            st.rerun()

        if st.button("🗑️ Clear Chat", key="clear_chat", disabled=is_processing):
            st.session_state.chat_history = []
            st.rerun()


# ═══════════════════════════════════════════════════════════════
# TAB 6: SLA MONITOR
# ═══════════════════════════════════════════════════════════════
with tabs[5]:
    st.subheader("📡 SLA Monitor")
    st.caption("Simulated SLA compliance metrics — real-time monitoring demonstration")

    st.markdown("""<div class="alert-info">
        ℹ️ <b>Demo Mode:</b> SLA metrics are computed from synthetic trade data.
        In production, this connects to a real-time message queue and time-series database.
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # SLA metric cards
    sla_data = [
        ("Trade Settlement SLA", "94.2%", "< 2 business days", "🟢 COMPLIANT", "#4ade80"),
        ("Regulatory Reporting SLA", "98.7%", "T+1 reporting", "🟢 COMPLIANT", "#4ade80"),
        ("Anomaly Alert Response", "87.3%", "< 30 minutes", "🟡 AT RISK", "#fbbf24"),
        ("Report Generation SLA", "100%", "< 2 hours", "🟢 COMPLIANT", "#4ade80"),
        ("Audit Log Completeness", "99.1%", "All events logged", "🟢 COMPLIANT", "#4ade80"),
        ("AML Alert Closure Rate", "72.4%", "< 24 hours", "🔴 BREACHED", "#ef4444"),
    ]

    cols = st.columns(3)
    for i, (name, rate, target, status, color) in enumerate(sla_data):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="metric-card" style="margin-bottom:16px;">
                <div style="font-size:0.8rem;color:#8b949e;text-transform:uppercase;
                            letter-spacing:0.05em;">{name}</div>
                <div class="metric-value" style="color:{color};font-size:2rem;">{rate}</div>
                <div style="font-size:0.75rem;color:#6b7280;margin-top:4px;">Target: {target}</div>
                <div style="font-size:0.8rem;font-weight:600;margin-top:8px;">{status}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # SLA trend chart
    import numpy as np
    dates = pd.date_range(end=datetime.utcnow(), periods=30, freq="D")
    np.random.seed(42)
    sla_trend = pd.DataFrame({
        "Date":       dates,
        "Settlement": np.clip(np.random.normal(94, 2, 30), 85, 100),
        "Reporting":  np.clip(np.random.normal(98, 1, 30), 92, 100),
        "AML Alerts": np.clip(np.random.normal(72, 5, 30), 60, 95),
    })

    fig = go.Figure()
    colors_sla = {"Settlement": "#4ade80", "Reporting": "#58a6ff", "AML Alerts": "#ef4444"}
    for col, color in colors_sla.items():
        fig.add_trace(go.Scatter(
            x=sla_trend["Date"], y=sla_trend[col],
            name=col, line=dict(color=color, width=2),
            fill="tozeroy", fillcolor=color.replace(")", ",0.1)").replace("rgb", "rgba"),
        ))

    fig.add_hline(y=95, line_dash="dash", line_color="#fbbf24",
                  annotation_text="Target 95%", annotation_position="bottom right")
    fig.update_layout(
        title="30-Day SLA Trend",
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        yaxis_title="SLA %", xaxis_title="Date",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        title_font_size=14,
    )
    st.plotly_chart(fig, use_container_width=True, config={'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d'], 'displaylogo': False})

    # Audit log
    st.markdown("#### 📋 Recent Audit Log")
    audit_entries = get_audit_log(limit=20)
    if audit_entries:
        adf = pd.DataFrame(audit_entries)
        st.dataframe(adf[["created_at","event_type","description","severity"]],
                     use_container_width=True, height=300)
    else:
        st.caption("No audit log entries yet. Run anomaly detection or generate a report to populate the log.")
