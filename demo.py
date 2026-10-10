#!/usr/bin/env python3
"""
Personalized Care Management Agent — Demo 1 of 4, Agentic AI Workshop.

A pure-Python (stdlib only) simulation of an agentic care-management system.
It contrasts the "prior era" generic patient blast with an "agentic era"
flow that triages risk, picks the patient's preferred outreach channel, and
generates a personalized care plan + a tailored message.

Run non-interactively (canned demo):   python3 demo.py
Run interactively (live Q&A mode):      python3 demo.py --interactive

No network, no API keys, no dependencies. Fully deterministic:
same output on every run.
"""

import argparse
import json
import sys
import textwrap
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# A fixed "today" keeps the demo deterministic (visit recency, risk scores).
DEMO_TODAY = date(2026, 10, 10)

GENERIC_BLAST = (
    "Get yourself checked. Visit a physician."
)

# Condition-specific care-plan playbooks used by the CarePlanAgent.
# These are simplified teaching examples, not medical advice.
CONDITION_PLAYBOOKS = {
    "Type 2 Diabetes": [
        "Track blood sugar daily; log readings in a notebook or phone app.",
        "Take metformin (or prescribed medication) with food, same time each day.",
        "Aim for a low-glycemic diet: vegetables, whole grains, lean protein.",
        "30-minute walk, 5 days a week — start small and build up.",
        "Schedule an A1C blood test every 3 months until it is below 7%.",
        "Check feet daily for cuts or sores; diabetes slows healing.",
    ],
    "Hypertension": [
        "Measure blood pressure at home twice daily and record it.",
        "Reduce salt: under 2,300 mg/day (one level teaspoon).",
        "Take blood pressure medication exactly as prescribed — never skip.",
        "Limit alcohol to 1 drink/day; stop smoking if applicable.",
        "Schedule a blood pressure check-up within 30 days.",
    ],
    "Chronic Kidney Disease": [
        "Avoid NSAID painkillers (e.g. ibuprofen) — they stress the kidneys.",
        "Limit protein and sodium per your doctor's guidance; track fluids.",
        "Take prescribed medications on schedule; never adjust doses yourself.",
        "Schedule kidney function labs (eGFR, creatinine) every 3 months.",
        "Report swelling, fatigue, or foamy urine to your care team promptly.",
    ],
}

# Risk thresholds (total risk points) -> tier
HIGH_RISK_THRESHOLD = 50
MEDIUM_RISK_THRESHOLD = 25

CHANNEL_FORMATS = ("email", "sms", "phone")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def divider(title="", width=72):
    """Print a section divider."""
    bar = "=" * width
    if title:
        print(f"\n{bar}\n{title}\n{bar}\n")
    else:
        print(f"\n{bar}\n")


def wrap(text, indent=0, width=72):
    """Wrap text for clean terminal output."""
    prefix = " " * indent
    return "\n".join(
        textwrap.wrap(text, width=width - indent,
                      initial_indent=prefix, subsequent_indent=prefix)
    )


def load_patients(path=None):
    """Load the local mock patient roster (fictional people only)."""
    if path is None:
        path = Path(__file__).resolve().parent / "mock_patients.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["patients"]


# ---------------------------------------------------------------------------
# AGENT 1 — AuthAgent: verifies the patient "logs in" with an email address.
# ---------------------------------------------------------------------------
def auth_agent(email, patients):
    """Look up a patient by email. Returns the patient dict or None."""
    lookup = email.strip().lower()
    for patient in patients:
        if patient["email"].lower() == lookup:
            return patient
    return None


# ---------------------------------------------------------------------------
# AGENT 2 — TriageAgent: scores clinical risk from structured data.
# ---------------------------------------------------------------------------
def triage_agent(patient):
    """Compute a deterministic risk score and tier from risk factors."""
    factors = patient.get("risk_factors", {})
    score = 0
    reasons = []

    hba1c = factors.get("hba1c")
    if hba1c is not None:
        if hba1c >= 9.0:
            score += 30
            reasons.append(f"A1C {hba1c}% (uncontrolled diabetes)")
        elif hba1c >= 8.0:
            score += 15
            reasons.append(f"A1C {hba1c}% (above target)")

    bp = factors.get("systolic_bp")
    if bp is not None:
        if bp >= 140:
            score += 15
            reasons.append(f"systolic BP {bp} (stage 2 hypertension)")
        elif bp >= 130:
            score += 10
            reasons.append(f"systolic BP {bp} (elevated)")

    egfr = factors.get("egfr")
    if egfr is not None and egfr < 45:
        score += 10
        reasons.append(f"eGFR {egfr} (stage 3b kidney disease)")

    if factors.get("missed_refills", 0) > 0:
        score += 10
        reasons.append(
            f"{factors['missed_refills']} missed medication refills")

    if factors.get("er_visits_last_6mo", 0) > 0:
        score += 10
        reasons.append(
            f"{factors['er_visits_last_6mo']} ER visit(s) in last 6 months")

    try:
        last_visit = date.fromisoformat(patient.get("last_visit", ""))
        if (DEMO_TODAY - last_visit).days > 90:
            score += 10
            reasons.append(f"last visit {last_visit} (>90 days ago)")
    except ValueError:
        reasons.append("last visit date unknown")

    if score >= HIGH_RISK_THRESHOLD:
        tier = "HIGH"
    elif score >= MEDIUM_RISK_THRESHOLD:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    return {"score": score, "tier": tier, "reasons": reasons}


# ---------------------------------------------------------------------------
# AGENT 3 — ChannelAgent: picks the outreach channel.
# ---------------------------------------------------------------------------
def channel_agent(patient, triage):
    """
    Choose the outreach channel. Rules:
      * Respect the patient's stated preference first (personalization).
      * HIGH-risk patients default to a phone call for urgency, unless the
        patient explicitly prefers email or SMS — in which case the message
        carries an urgent follow-up CTA.
    """
    preference = patient.get("preferred_channel", "email")
    if preference not in CHANNEL_FORMATS:
        preference = "email"
    if triage["tier"] == "HIGH" and preference not in ("email", "sms"):
        return "phone"
    return preference


# ---------------------------------------------------------------------------
# AGENT 4 — CarePlanAgent: builds a personalized care plan.
# ---------------------------------------------------------------------------
def care_plan_agent(patient, triage):
    """Assemble a personalized care plan from condition playbooks."""
    plan = []
    for condition in patient.get("conditions", []):
        steps = CONDITION_PLAYBOOKS.get(condition, [])
        if steps:
            plan.append({"condition": condition, "steps": steps})

    if triage["tier"] == "HIGH":
        plan.append({
            "condition": "High-risk follow-up",
            "steps": [
                "Care manager will check in within 7 days.",
                "If any symptoms worsen, call the clinic same-day.",
            ],
        })
    elif triage["tier"] == "MEDIUM":
        plan.append({
            "condition": "Routine follow-up",
            "steps": [
                "Care manager will check in within 30 days.",
            ],
        })
    return plan


# ---------------------------------------------------------------------------
# AGENT 5 — MessageAgent: renders the message for the chosen channel.
# ---------------------------------------------------------------------------
def message_agent(patient, triage, care_plan, channel):
    """Render a personalized, channel-specific outreach message."""
    first_name = patient["name"].split()[0]
    conditions = " and ".join(patient["conditions"])

    if channel == "email":
        subject = (
            f"Your personalized care plan for {conditions} — "
            f"risk level: {triage['tier']}"
        )
        body_lines = [
            f"Hi {first_name},",
            "",
            f"This is your care team. We've reviewed your latest health "
            f"data, and we've put together a care plan made for you — "
            f"because a generic reminder doesn't know that you are managing "
            f"{conditions}.",
            "",
            f"Your current risk level is {triage['tier']} "
            f"(score {triage['score']}). Here is what we recommend:",
            "",
        ]
        for section in care_plan:
            body_lines.append(f"  {section['condition'].upper()}")
            for step in section["steps"]:
                body_lines.append(f"    - {step}")
            body_lines.append("")
        if triage["tier"] == "HIGH":
            body_lines.append(
                "Because this is urgent, please reply to this email or call "
                "the clinic within 7 days so we can review your plan together."
            )
        else:
            body_lines.append(
                "Reply to this email if anything feels off — we're here."
            )
        return f"Subject: {subject}\n\n" + "\n".join(body_lines)

    if channel == "sms":
        urgent = triage["tier"] == "HIGH"
        lines = [
            f"Hi {first_name}! Your care team here. Your personalized plan "
            f"for {conditions} is ready (risk: {triage['tier']}).",
            "Key actions:",
        ]
        # Keep SMS short: top 2 steps of the first condition section.
        top_steps = care_plan[0]["steps"][:2] if care_plan else []
        for i, step in enumerate(top_steps, 1):
            lines.append(f"{i}) {step}")
        if urgent:
            lines.append(
                "This is important — please call the clinic this week."
            )
        else:
            lines.append("Full plan in your patient portal. Reply HELP anytime.")
        return "\n".join(lines)

    # channel == "phone": a call script for the care manager.
    script = [
        f"CALL SCRIPT — outreach call to {patient['name']} "
        f"({patient['email']})",
        "",
        f"INTRO: \"Hi {first_name}, this is your care team calling. Do you "
        f"have 5 minutes? I want to walk you through a care plan we made "
        f"just for you, based on your {conditions}.\"",
        "",
        "TALKING POINTS:",
    ]
    for section in care_plan:
        script.append(f"  - {section['condition']}:")
        for step in section["steps"][:3]:
            script.append(f"      * {step}")
    script += [
        "",
        f"RISKS TO ACKNOWLEDGE: {'; '.join(triage['reasons']) or 'none flagged'}",
        "",
        "CLOSE: \"Can we book your follow-up before we hang up? "
        "And is there anything in the plan that feels hard to do — "
        "we can adjust it together.\"",
    ]
    return "\n".join(script)


# ---------------------------------------------------------------------------
# Orchestrator — runs the full agentic pipeline for one patient.
# ---------------------------------------------------------------------------
def run_agentic_flow(patient, patients):
    """Execute all five agents in sequence for one patient."""
    print(f"[AuthAgent]    Login verified: {patient['email']}")
    print(f"[TriageAgent]  Scoring risk for {patient['name']} "
          f"(conditions: {', '.join(patient['conditions'])})...")
    triage = triage_agent(patient)
    print(f"[TriageAgent]  Score {triage['score']} -> tier {triage['tier']}")
    for reason in triage["reasons"]:
        print(f"               - {reason}")

    channel = channel_agent(patient, triage)
    print(f"[ChannelAgent] Selected channel: {channel.upper()} "
          f"(patient preference: {patient.get('preferred_channel')})")

    plan = care_plan_agent(patient, triage)
    print(f"[CarePlanAgent] Assembled {len(plan)} care-plan section(s)")

    message = message_agent(patient, triage, plan, channel)
    print(f"[MessageAgent] Rendered {channel.upper()} message:\n")
    print("-" * 72)
    print(message)
    print("-" * 72)
    return True


# ---------------------------------------------------------------------------
# Canned (non-interactive) demo
# ---------------------------------------------------------------------------
def run_canned_demo():
    """Full end-to-end canned demo. Deterministic; exits 0 on success."""
    patients = load_patients()
    divider("PERSONALIZED CARE MANAGEMENT AGENT  (Demo 1 of 4)")
    print(wrap(
        "Story: in the 'prior era', a care team sent ONE generic blast "
        "email to every patient. Today, an agentic system verifies the "
        "patient, triages clinical risk, picks the patient's preferred "
        "outreach channel, builds a personalized care plan, and renders a "
        "tailored message — per patient, automatically."
    ))

    divider("ACT 1 — THE PRIOR ERA: one generic blast for everyone")
    print(wrap("The care team sends this to ALL patients, regardless of "
               "condition:"))
    print()
    print("   Subject: Health Reminder")
    print(f"   Body:    \"{GENERIC_BLAST}\"")
    print()
    print(wrap("Notice: no name, no condition, no next step, no channel "
               "choice. A patient with uncontrolled diabetes gets the same "
               "note as a healthy 45-year-old."))

    divider("ACT 2 — THE AGENTIC ERA: personalized, per-patient flow")
    for i, patient in enumerate(patients, 1):
        divider(f"PATIENT {i}/{len(patients)} — {patient['name']}")
        run_agentic_flow(patient, patients)

    divider("ACT 3 — SIDE-BY-SIDE")
    print("PRIOR ERA (generic blast, sent to everyone):")
    print(f'    "{GENERIC_BLAST}"')
    print()
    print("AGENTIC ERA (personalized, e.g. Priya Sharma — email channel):")
    priya = patients[0]
    triage = triage_agent(priya)
    plan = care_plan_agent(priya, triage)
    email_msg = message_agent(priya, triage, plan, "email")
    first_line = email_msg.split("\n")[0]
    print(f"    {first_line}")
    print(wrap("    ...with a personalized care plan, named risks, and a "
               "7-day follow-up CTA — because the agent knows her A1C is "
               "9.2 and her last visit was over 90 days ago.", indent=4))
    print()
    print("Demo complete: 3 patients triaged, 3 personalized plans, "
          "3 channel-tailored messages.")
    return 0


# ---------------------------------------------------------------------------
# Interactive mode — live Q&A with the user.
# ---------------------------------------------------------------------------
def run_interactive():
    """Live Q&A mode: log in as a patient, describe conditions, get a plan."""
    patients = load_patients()
    divider("INTERACTIVE MODE — you are the patient")
    print("Available mock logins (type an email, or Ctrl-C to quit):")
    for patient in patients:
        print(f"  - {patient['email']}  ({patient['name']})")

    try:
        email = input("\nEmail address: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        return 0

    patient = auth_agent(email, patients)
    if patient is None:
        print(f"No patient found for '{email}'. Try one of the mock emails.")
        return 1
    print(f"\nWelcome back, {patient['name']}! (Login verified.)")

    print("\nEnter your conditions (comma-separated). Known conditions:")
    for condition in CONDITION_PLAYBOOKS:
        print(f"  - {condition}")
    try:
        raw = input("Conditions: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        return 0

    chosen = [c.strip() for c in raw.split(",") if c.strip()]
    known = {c.lower(): c for c in CONDITION_PLAYBOOKS}
    conditions = [known[c.lower()] for c in chosen if c.lower() in known]
    if not conditions:
        conditions = patient["conditions"]
        print(f"(Using on-file conditions: {', '.join(conditions)})")
    patient = dict(patient)  # don't mutate the roster
    patient["conditions"] = conditions

    triage = triage_agent(patient)
    print(f"\nTriage result: {triage['tier']} risk (score {triage['score']}).")
    if triage["reasons"]:
        print("Reasons:")
        for reason in triage["reasons"]:
            print(f"  - {reason}")

    print(f"\nYour saved channel preference: "
          f"{patient.get('preferred_channel')}")
    try:
        channel = input(
            "Outreach channel [email/sms/phone, Enter = use preference]: "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        return 0
    if channel not in CHANNEL_FORMATS:
        channel = channel_agent(patient, triage)
    print(f"Using channel: {channel.upper()}")

    plan = care_plan_agent(patient, triage)
    message = message_agent(patient, triage, plan, channel)
    print("\nYour personalized message:\n")
    print("-" * 72)
    print(message)
    print("-" * 72)
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Personalized Care Management Agent — workshop demo.")
    parser.add_argument(
        "--interactive", action="store_true",
        help="Run the live Q&A mode instead of the canned demo.")
    args = parser.parse_args(argv)

    try:
        if args.interactive:
            return run_interactive()
        return run_canned_demo()
    except BrokenPipeError:
        # Allow piping to `head` etc. without a traceback.
        return 0


if __name__ == "__main__":
    sys.exit(main())
