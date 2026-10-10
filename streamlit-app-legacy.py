"""Streamlit UI for the Personalized Care Management Agent demo.

This is OPTIONAL — it only needs `pip install streamlit`. The core demo
(demo.py) is pure Python stdlib and does not depend on this file.

Run with:  streamlit run app.py
"""

import json
from pathlib import Path

import streamlit as st

# Import the agent pipeline from the stdlib-only demo script.
import demo

st.set_page_config(
    page_title="Personalized Care Management Agent",
    page_icon="🏥",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🏥 Personalized Care Management Agent")
st.caption("Demo 1 of 4 · Agentic AI Workshop — prior era vs. agentic era")

# ---------------------------------------------------------------------------
# Act 1 — the prior era
# ---------------------------------------------------------------------------
st.subheader("Act 1 — The Prior Era")
st.warning(
    f'**Generic blast sent to every patient:**\n\n'
    f'> "{demo.GENERIC_BLAST}"\n\n'
    "No name. No condition. No next step. No channel choice."
)

st.divider()

# ---------------------------------------------------------------------------
# Act 2 — the agentic era
# ---------------------------------------------------------------------------
st.subheader("Act 2 — The Agentic Era")

patients = demo.load_patients()

patient_labels = {
    f"{p['name']} ({p['email']})": p for p in patients
}
selection = st.selectbox("Log in as a patient (mock email login):",
                         list(patient_labels.keys()))
patient = patient_labels[selection]

# Run the agent pipeline
triage = demo.triage_agent(patient)
channel = demo.channel_agent(patient, triage)
plan = demo.care_plan_agent(patient, triage)
message = demo.message_agent(patient, triage, plan, channel)

# Agent trace
st.markdown("#### 🕵️ Agent trace")
col1, col2, col3 = st.columns(3)
col1.metric("AuthAgent", "verified ✅", patient["email"])
col2.metric("TriageAgent",
            f"{triage['tier']} risk",
            f"score {triage['score']}")
col3.metric("ChannelAgent", channel.upper(),
            f"preference: {patient['preferred_channel']}")
with st.expander("Why this risk tier?"):
    if triage["reasons"]:
        st.markdown("\n".join(f"- {r}" for r in triage["reasons"]))
    else:
        st.write("No risk flags.")

# Care plan
st.markdown("#### 🩺 CarePlanAgent — personalized care plan")
for section in plan:
    with st.expander(section["condition"], expanded=True):
        st.markdown("\n".join(f"- {s}" for s in section["steps"]))

# Message
st.markdown(f"#### ✉️ MessageAgent — tailored {channel} message")
st.code(message, language=None)

# ---------------------------------------------------------------------------
# Act 3 — side-by-side
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Act 3 — Side by Side")
c1, c2 = st.columns(2)
c1.markdown("**Prior era (blast):**")
c1.info(f'"{demo.GENERIC_BLAST}"')
c2.markdown(f"**Agentic era ({patient['name']}, {channel}):**")
c2.success(message.split("\n")[0])

st.caption(
    "All patients are fictional. Mock data lives in "
    "`mock_patients.json`. Educational demo — not medical advice."
)
