import os
import time
import requests
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

# Load environment configuration
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY")
BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "incident-memory")

# Page Configuration
st.set_page_config(
    page_title="Aegis SRE | Autonomous Incident Commander",
    page_icon="🛡️",
    layout="wide"
)

# Custom Styling for Enterprise SRE Aesthetic
st.markdown("""
<style>
    .metric-card {
        background-color: #111827;
        border: 1px solid #374151;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
    }
    .status-badge {
        background-color: #064E3B;
        color: #6EE7B7;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Groq Client
@st.cache_resource
def get_groq_client():
    return Groq(api_key=GROQ_API_KEY)

groq_client = get_groq_client()

# Direct REST Client for Hindsight (100% thread-safe, no asyncio errors)
def recall_from_hindsight(bank_id: str, query: str):
    url = f"https://api.hindsight.vectorize.io/v1/default/banks/{bank_id}/memories/recall"
    headers = {
        "Authorization": f"Bearer {HINDSIGHT_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, headers=headers, json={"query": query}, timeout=15)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            extracted = []
            for r in results:
                if isinstance(r, dict):
                    extracted.append(r.get("text", r.get("content", str(r))))
                else:
                    extracted.append(str(r))
            return extracted, None
        else:
            return [], f"Hindsight HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return [], str(e)

def retain_to_hindsight(bank_id: str, content: str):
    url = f"https://api.hindsight.vectorize.io/v1/default/banks/{bank_id}/memories/retain"
    headers = {
        "Authorization": f"Bearer {HINDSIGHT_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, headers=headers, json={"content": content}, timeout=15)
        return response.status_code in [200, 201]
    except Exception:
        return False

# Sidebar: Controls & Presets
with st.sidebar:
    st.title("⚙️ System Control")
    memory_enabled = st.toggle("Enable Hindsight Memory", value=True, help="Toggle persistent recall vs stateless LLM.")
    
    st.divider()
    st.subheader("Simulate Active Outage")
    preset_scenarios = {
        "Select an incident...": "",
        "🚨 PostgreSQL Connection Exhaustion": "Service auth-service throwing HTTP 504 Gateway Timeouts on auth-cluster-04 with error: 'FATAL: remaining connection slots are reserved for non-replicated superuser connections'. Should I increase max_connections to 500?",
        "⚡ Kafka Rebalance Storm": "Kafka consumers in billing-pipeline repeatedly crashing with CommitFailedException and rebalancing. Lag spiked to 1.2M records.",
        "🔥 Redis Cluster OOM": "session-cache-prod throwing OOM command not allowed when used memory > 'maxmemory'. How do we resolve immediately?"
    }
    selected_scenario = st.selectbox("Quick-Load Production Scenario:", list(preset_scenarios.keys()))
    
    st.divider()
    st.markdown(f"""
    **Memory Bank Status:**  
    `Bank ID:` **`{BANK_ID}`**  
    `Engine:` **Hindsight Graph Memory**  
    `Protocol:` **Direct REST API**
    """)

# Main Dashboard Header
col_header, col_status = st.columns([4, 1])
with col_header:
    st.title("🛡️ Aegis SRE — Autonomous Incident Commander")
    st.caption("Persistent Multi-Turn Incident Diagnostics & Remediation Engine powered by Hindsight")
with col_status:
    st.markdown("<br><span class='status-badge'>🟢 SRE COCKPIT ACTIVE</span>", unsafe_allow_html=True)

st.divider()

# Two-Column Cockpit Layout
col_chat, col_telemetry = st.columns([3, 2])

with col_chat:
    st.subheader("💬 Incident Investigation Console")
    
    user_query = st.text_area(
        "Enter Error Logs, Stacktrace, or Outage Symptoms:",
        value=preset_scenarios[selected_scenario] if selected_scenario != "Select an incident..." else "",
        height=140,
        placeholder="Paste production logs or ask diagnostic questions..."
    )
    
    run_btn = st.button("🚀 Analyze Incident", type="primary", use_container_width=True)

with col_telemetry:
    st.subheader("🧠 Hindsight Memory Telemetry")
    telemetry_placeholder = st.empty()
    telemetry_placeholder.info("Awaiting query execution to stream memory retrieval metrics...")

# Execution Flow
if run_btn and user_query.strip():
    recalled_context = ""
    recall_latency = 0.0
    
    if memory_enabled:
        with st.spinner("Querying Hindsight Knowledge Graph..."):
            start_time = time.time()
            memories, err = recall_from_hindsight(BANK_ID, user_query)
            recall_latency = round(time.time() - start_time, 2)
            
            if err:
                telemetry_placeholder.error(f"Hindsight Recall Error: {err}")
            elif memories:
                recalled_context = "\n\n".join([f"• {m}" for m in memories])
                with telemetry_placeholder.container():
                    st.success(f"Recalled {len(memories)} graph nodes in {recall_latency}s")
                    with st.expander("🔍 Inspect Recalled Knowledge Graph Nodes", expanded=True):
                        st.markdown(f"```text\n{recalled_context}\n```")
            else:
                telemetry_placeholder.warning("No matching historical post-mortems found.")
    else:
        telemetry_placeholder.warning("⚠️ Hindsight Memory is DISABLED (Stateless Baseline Mode).")

    # Construct Prompt
    if memory_enabled and recalled_context:
        system_prompt = f"""You are Aegis SRE, an expert incident commander.
You have access to historical organizational post-mortems and verified runbooks stored in Hindsight persistent memory:
---
HISTORICAL POST-MORTEM MEMORY:
{recalled_context}
---
CRITICAL INSTRUCTIONS:
- Directly cite previous incident post-mortems (e.g., INC-4102) and previous root causes.
- If the engineer proposes an action that previously caused failures (such as bumping max_connections), WARN THEM IMMEDIATELY.
- Provide step-by-step verified remediation commands and runbook citations."""
    else:
        system_prompt = "You are a standard generic AI assistant. Provide general troubleshooting advice based only on common public IT documentation."

    with col_chat:
        with st.spinner("Generating incident mitigation plan..."):
            # Automatically find an active chat model in user's Groq account
            try:
                active_models = [
                    m.id for m in groq_client.models.list().data 
                    if not any(x in m.id.lower() for x in ["whisper", "vision", "embed", "guard"])
                ]
                preferred_order = ["llama-3.1-8b-instant", "qwen-2.5-32b", "gemma2-9b-it", "llama3-70b-8192"]
                models_to_try = [p for p in preferred_order if p in active_models] + [m for m in active_models if m not in preferred_order]
                if not models_to_try:
                    models_to_try = ["llama-3.1-8b-instant"]
            except Exception:
                models_to_try = ["llama-3.1-8b-instant"]

            completion = None
            last_err = None

            for model_name in models_to_try:
                try:
                    completion = groq_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_query}
                        ],
                        temperature=0.2,
                        max_tokens=900
                    )
                    break
                except Exception as err:
                    last_err = err
                    continue

            if completion:
                st.markdown("### 📋 Remediation Plan")
                st.markdown(completion.choices[0].message.content)
            else:
                st.error(f"Groq API Error: {str(last_err)}")
            
            # Post-Incident Ingestion Feature
            st.divider()
            with st.expander("💾 Retain New Incident Resolution to Hindsight"):
                new_postmortem = st.text_area("Write Post-Mortem Note to Store:", placeholder="e.g., INC-4301: Resolved by restarting worker with flag --threads=8...")
                if st.button("Store in Memory Bank"):
                    if new_postmortem.strip():
                        if retain_to_hindsight(BANK_ID, new_postmortem):
                            st.success("Successfully retained in Hindsight! Graph links updated.")
                        else:
                            st.error("Failed to retain memory node.")