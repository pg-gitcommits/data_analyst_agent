"""
app.py — Streamlit UI for the Data Analyst Agent.

Handles:
- CSV file upload and preview
- User question input and quick prompts
- Streaming agent responses step by step
- Persistent multi-turn conversation history via session state
"""

import streamlit as st
import pandas as pd
import os
import tempfile
import time

from agent import run_agent

st.set_page_config(
    page_title="Data Analyst Agent",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

.stApp { background: #0f0f0f; color: #e8e8e8; }

.main-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.8rem;
    font-weight: 500;
    color: #e8e8e8;
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
}
.sub-header {
    font-size: 0.85rem;
    color: #666;
    font-family: 'IBM Plex Mono', monospace;
    margin-bottom: 2rem;
}

.stButton > button {
    background: #e8e8e8 !important;
    color: #0f0f0f !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.2rem !important;
}
.stButton > button:hover { background: #ffffff !important; }

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #1a1a1a !important;
    color: #e8e8e8 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 4px !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}

div[data-testid="stFileUploader"] {
    background: #1a1a1a;
    border: 1px dashed #333;
    border-radius: 6px;
    padding: 1rem;
}

.step-box {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.85rem;
}
.step-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: #555;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
}
.code-block {
    background: #111;
    border: 1px solid #222;
    border-left: 3px solid #444;
    border-radius: 4px;
    padding: 0.8rem 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    color: #aaa;
    white-space: pre-wrap;
    overflow-x: auto;
    margin: 0.4rem 0;
}
.output-block {
    background: #0a0a0a;
    border: 1px solid #1e1e1e;
    border-left: 3px solid #2a6e2a;
    border-radius: 4px;
    padding: 0.8rem 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    color: #7acc7a;
    white-space: pre-wrap;
    overflow-x: auto;
    margin: 0.4rem 0;
}
.answer-block {
    background: #111827;
    border: 1px solid #1f2937;
    border-left: 3px solid #3b82f6;
    border-radius: 4px;
    padding: 1rem 1.2rem;
    font-size: 0.9rem;
    color: #d1d5db;
    line-height: 1.7;
    margin: 0.5rem 0;
}
.stat-pill {
    display: inline-block;
    background: #1e1e1e;
    border: 1px solid #2a2a2a;
    border-radius: 3px;
    padding: 0.2rem 0.6rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: #888;
    margin: 0.1rem;
}

.stDataFrame { border: 1px solid #222 !important; border-radius: 6px !important; }

hr { border-color: #1e1e1e !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown('<div class="main-header">⬡ data analyst agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">upload a csv · ask anything · watch it think</div>', unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────────────────────────
if "csv_path" not in st.session_state:
    st.session_state.csv_path = None
if "chart_dir" not in st.session_state:
    st.session_state.chart_dir = tempfile.mkdtemp()
if "history" not in st.session_state:
    st.session_state.history = []  # list of {"question": str, "steps": list}
if "message_history" not in st.session_state:
    st.session_state.message_history = []

# ── Layout ───────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.markdown("#### Upload CSV")
    uploaded = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")

    if uploaded:
        # Save to temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        tmp.write(uploaded.read())
        tmp.flush()
        st.session_state.csv_path = tmp.name

        df_preview = pd.read_csv(st.session_state.csv_path)
        st.markdown(f"""
        <div style='margin-top:0.8rem;'>
            <span class='stat-pill'>{df_preview.shape[0]:,} rows</span>
            <span class='stat-pill'>{df_preview.shape[1]} cols</span>
            <span class='stat-pill'>{uploaded.name}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:1rem; font-size:0.8rem; color:#555;'>Preview</div>", unsafe_allow_html=True)
        st.dataframe(df_preview.head(6), use_container_width=True, height=220)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Ask a question")

    question = st.text_area(
        "Ask a question",
        placeholder="e.g. What are the top 5 categories by revenue? Show a bar chart.",
        height=110,
        label_visibility="collapsed",
        key="question_input"
    )

    if "prefill" in st.session_state:
        question = st.session_state.pop("prefill")


    run_btn = st.button("▶ Run analysis", disabled=not (st.session_state.csv_path and question))
    if st.session_state.get("auto_run") and question:
        st.session_state["auto_run"] = False
        run_btn = True

    st.markdown("<div style='font-size:0.75rem; color:#444; margin-top:0.8rem; margin-bottom:0.3rem;'>Quick prompts</div>", unsafe_allow_html=True)
    example_qs = [
        "Give me a summary of this dataset",
        "Show the distribution of numeric columns",
        "Are there any missing values?",
        "Plot correlations between columns",
    ]
    for eq in example_qs:
        if st.button(eq, key=eq):
            st.session_state["prefill"] = eq
            st.session_state["auto_run"] = True
            st.rerun()

with col_right:
    st.markdown("#### Analysis")

    if run_btn and st.session_state.csv_path and question:
        entry = {"question": question, "steps": []}

        entry = {"question": question, "steps": []}
        st.session_state.history.append(entry)

        with st.container():
            st.markdown(f"<div style='font-family:IBM Plex Mono,monospace;font-size:0.8rem;color:#666;margin-bottom:0.5rem;'>Q: {question}</div>", unsafe_allow_html=True)

            steps_placeholder = st.empty()
            steps_html = ""

            for event in run_agent(st.session_state.csv_path, question, st.session_state.chart_dir, st.session_state.message_history):
                if event["type"] == "text":
                    entry["steps"].append({"kind": "text", "content": event["content"]})
                    steps_html += f"<div class='answer-block'>{event['content']}</div>"

                elif event["type"] == "tool_call":
                    entry["steps"].append({"kind": "code", "content": event["code"]})
                    escaped = event["code"].replace("<", "&lt;").replace(">", "&gt;")
                    steps_html += f"<details><summary style='font-family:IBM Plex Mono,monospace;font-size:0.75rem;color:#555;cursor:pointer;'>▸ view python code</summary><div class='code-block'>{escaped}</div></details>"

                elif event["type"] == "tool_result":
                    entry["steps"].append({"kind": "result", "content": event["output"], "charts": event["charts"]})
                    escaped_out = event["output"].replace("<", "&lt;").replace(">", "&gt;")
                    steps_html += f"<details><summary style='font-family:IBM Plex Mono,monospace;font-size:0.75rem;color:#555;cursor:pointer;'>▸ view output</summary><div class='output-block'>{escaped_out}</div></details>"
                    steps_placeholder.markdown(steps_html, unsafe_allow_html=True)
                    for chart_path in event["charts"]:
                        if os.path.exists(chart_path):
                            st.image(chart_path, use_column_width=True)

                steps_placeholder.markdown(steps_html, unsafe_allow_html=True)

        st.session_state.message_history.append({"role": "user", "content": question})
        st.session_state.message_history.append({"role": "assistant", "content": [
            {"type": "text", "text": "".join(s["content"] for s in entry["steps"] if s["kind"] == "text")}]})
        st.session_state.history.append(entry)
        st.markdown("<hr>", unsafe_allow_html=True)

    # Show previous entries
    for entry in reversed(st.session_state.history[:-1] if run_btn else st.session_state.history):
        with st.expander(f"Q: {entry['question'][:70]}...", expanded=False):
            for step in entry["steps"]:
                if step["kind"] == "text":
                    st.markdown(f"<div class='answer-block'>{step['content']}</div>", unsafe_allow_html=True)
                elif step["kind"] == "code":
                    escaped = step["content"].replace("<", "&lt;").replace(">", "&gt;")
                    st.markdown(f"<div class='code-block'>{escaped}</div>", unsafe_allow_html=True)
                elif step["kind"] == "result":
                    escaped = step["content"].replace("<", "&lt;").replace(">", "&gt;")
                    st.markdown(f"<div class='output-block'>{escaped}</div>", unsafe_allow_html=True)
                    for chart_path in step.get("charts", []):
                        if os.path.exists(chart_path):
                            st.image(chart_path, use_column_width=True)

    if not st.session_state.history:
        st.markdown("""
        <div style='color:#333; font-size:0.85rem; font-family:IBM Plex Mono,monospace; margin-top:3rem; text-align:center; line-height:2;'>
            upload a csv<br>ask a question<br>watch the agent think step by step
        </div>
        """, unsafe_allow_html=True)