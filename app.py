#!/usr/bin/env python3
"""Personalized Care Management Agent -- localhost web UI (stdlib only).

Run:  python3 app.py   then open http://localhost:8001
Serves a guided, personalized tour of demo.py (the tested artifact --
demo.py is never modified here; it is only imported as a module and its
canned subprocess run is unchanged).
"""

import contextlib
import http.server
import io
import json
import mimetypes
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8001
HERE = Path(__file__).resolve().parent
DEMO_PY = HERE / "demo.py"

sys.path.insert(0, str(HERE))
import demo as DEMO  # the tested artifact: imported, never modified

# ---- personalized triage (app.py only; demo.py untouched) ----
# Red-flag patterns are checked FIRST -- any match escalates to URGENT and
# bypasses routine scoring entirely. This demo is not medical advice.

_CRITICAL_PATTERNS = [
    (r"\bcancer\b", "cancer"),
    (r"\btumou?rs?\b", "tumor"),
    (r"(4th|fourth)\s*stage|stage\s*(4|iv)\b", "advanced stage (stage 4/IV)"),
    (r"\bmetastatic\b", "metastatic disease"),
    (r"heart attack", "heart attack"),
    (r"\bstroke\b", "stroke"),
    (r"chest pain", "chest pain"),
    (r"difficulty breathing|can'?t breathe|cannot breathe|shortness of breath|trouble breathing|can not breathe", "breathing difficulty"),
    (r"\bbleeding\b", "bleeding"),
    (r"\bseizures?\b", "seizure"),
    (r"suicid|self-?harm|kill myself|end my life|end it all", "self-harm risk"),
    (r"\b(want to die|wish (i was|i were) dead|better off dead)\b", "self-harm risk"),
    (r"\b(hurt|harm|cut)\s+(myself|my\s+self)\b", "self-harm risk"),
    (r"\bkill\s+(you|him|her|them|someone|somebody|people|others?)\b", "threat to others"),
    (r"\b(hurt|harm|attack|stab|shoot)\s+(you|him|her|them|someone|somebody|people|others?)\b", "threat to others"),
    (r"\bmurder\b", "threat to others"),
    (r"\b(going to|gonna)\s+kill\b", "threat to others"),
    (r"\boverdose\b", "overdose"),
    (r"anaphyla", "anaphylaxis"),
]

# Requests for OTHER patients' data. The personalized endpoint can never see
# the roster, but the request must be declined explicitly (privacy guard) --
# never processed as a health condition or echoed into a routine message.
_PRIVACY_PATTERNS = [
    r"every patient", r"all patients", r"other patients", r"another patient",
    r"list of patients", r"patient list", r"patient roster", r"full roster",
    r"show me.*patients?", r"patients?.*(name|email).*(list|show|give|tell)",
    r"someone else'?s (data|record|information)",
    r"\bphi\b",
]

_WELLNESS_PATTERNS = [
    r"\bi feel fine\b",
    r"\bfeeling (fine|great|good|healthy)\b",
    r"\bhealthy\b",
    r"\bno conditions\b",
    r"\bnone\b",
    r"\bnothing wrong\b",
    r"\ball good\b",
]

# (aliases, canonical display name, risk weight) -- checked in order.
_CONDITION_MAP = [
    (("type 1 diabetes", "t1d", "diabetes type 1"), "Type 1 Diabetes", 25),
    (("type 2 diabetes", "t2d", "diabetes type 2"), "Type 2 Diabetes", 20),
    (("diabetes",), "Type 2 Diabetes", 20),
    (("hypertension", "high blood pressure", "hbp", "htn", "high bp"), "Hypertension", 15),
    (("heart disease", "coronary", "heart failure", "chf"), "Heart Disease", 20),
    (("kidney disease", "ckd", "chronic kidney", "renal failure"), "Chronic Kidney Disease", 15),
    (("copd", "emphysema", "chronic bronchitis"), "COPD", 15),
    (("asthma",), "Asthma", 10),
    (("depression", "depressive"), "Depression", 10),
    (("anxiety",), "Anxiety", 8),
    (("hyperlipidemia", "high cholesterol", "cholesterol"), "High Cholesterol", 10),
    (("arthritis", "osteoarthritis", "rheumatoid"), "Arthritis", 5),
    (("migraine",), "Migraine", 5),
    (("obesity", "obese", "overweight"), "Obesity", 10),
    (("dementia", "alzheimer"), "Dementia", 10),
    (("seasonal allergies", "hay fever", "allergies", "allergy"), "Seasonal Allergies", 3),
    (("knee surgery", "hip surgery", "surgery", "post-surgery", "post surgery",
      "recovering from", "recovery from"), "Post-Surgery Recovery", 8),
    (("smoking", "smoker", "tobacco", "quit smoking", "vaping", "nicotine"), "Smoking Cessation", 10),
    (("sleep apnea", "apnea", "loud snoring", "snoring"), "Sleep Apnea", 10),
    (("gerd", "acid reflux", "heartburn"), "GERD", 5),
    (("osteoporosis", "bone loss", "brittle bones"), "Osteoporosis", 8),
    (("parkinson",), "Parkinson's Disease", 12),
    (("epilepsy",), "Epilepsy", 12),
    (("thyroid", "hypothyroid", "hashimoto", "hyperthyroid"), "Thyroid Disorder", 5),
    (("anemia", "anemic", "low iron", "iron deficiency"), "Anemia", 5),
    (("back pain", "sciatica", "herniated disc", "slipped disc"), "Back Pain", 5),
    (("fibromyalgia", "fibro"), "Fibromyalgia", 5),
    (("afib", "a-fib", "atrial fibrillation"), "Atrial Fibrillation", 15),
    (("eczema", "psoriasis", "dermatitis"), "Eczema / Psoriasis", 3),
    (("ibs", "irritable bowel"), "IBS", 5),
    (("gout",), "Gout", 5),
]

_HIGH_TIER_AT = 50
_MEDIUM_TIER_AT = 25

# Safe, general self-management information for recognized conditions that have
# no playbook entry in demo.py. General information only -- never prescriptive.
_EXTRA_SECTIONS = {
    "Type 1 Diabetes": [
        "Check blood sugar as your doctor advised and log the readings.",
        "Take insulin exactly as prescribed; never skip or adjust doses on your own.",
        "Know the signs of low blood sugar and keep fast-acting glucose nearby.",
    ],
    "Heart Disease": [
        "Take heart medications exactly as prescribed.",
        "Note any chest discomfort, unusual shortness of breath, or swelling -- report promptly.",
        "Ask your doctor what activity level is safe for you.",
    ],
    "COPD": [
        "Avoid smoke and strong fumes; make sure your inhaler technique is right.",
        "Notice changes in breathlessness or mucus -- report flare-ups early.",
        "Ask about pulmonary rehab and vaccinations (flu, pneumonia).",
    ],
    "Asthma": [
        "Keep your reliever inhaler where you can reach it.",
        "Learn your personal triggers and note them.",
        "Follow the asthma action plan you made with your doctor.",
    ],
    "Depression": [
        "Stay connected -- tell someone you trust how you are feeling.",
        "Keep a regular sleep schedule; daylight and gentle movement help.",
        "If thoughts of self-harm arise, call or text 988 (US) right away.",
    ],
    "Anxiety": [
        "Practice slow breathing when anxiety spikes; note what triggers it.",
        "Keep caffeine and alcohol in check -- both can worsen anxiety.",
        "If anxiety interferes with daily life, ask your doctor about options.",
    ],
    "High Cholesterol": [
        "Take cholesterol medication as prescribed, if any.",
        "Favor vegetables, whole grains, and lean proteins; limit fried foods.",
        "Recheck lipids on the schedule your doctor sets.",
    ],
    "Arthritis": [
        "Keep joints moving with gentle, doctor-approved activity.",
        "Use heat or cold for stiffness as advised.",
        "Report new swelling or hot-feeling joints to your care team.",
    ],
    "Migraine": [
        "Track attacks: when they start, how long they last, possible triggers.",
        "Rest in a dark, quiet room during an attack if you can.",
        "If attacks are frequent or suddenly different, tell your doctor.",
    ],
    "Obesity": [
        "Aim for small, steady changes in eating and activity -- not crash diets.",
        "Track weight weekly, same time of day.",
        "Ask your doctor about programs covered by your plan.",
    ],
    "Dementia": [
        "Keep a consistent daily routine; labels on rooms and drawers help.",
        "Caregivers: take breaks and ask about respite support -- burnout is real.",
        "Report sudden confusion changes promptly; they can signal something treatable.",
    ],
    "Seasonal Allergies": [
        "Check local pollen counts and limit outdoor time on high days.",
        "Shower and change clothes after being outside.",
        "If breathing is ever affected, treat it as urgent -- not just allergies.",
    ],
    "Post-Surgery Recovery": [
        "Follow your surgeon's wound-care and activity instructions exactly.",
        "Watch for redness, swelling, fever, or unusual pain -- report promptly.",
        "Do your prescribed rehab exercises even when they are uncomfortable.",
    ],
    "Smoking Cessation": [
        "Set a quit date and tell someone about it.",
        "Ask your doctor about quit aids covered by your plan.",
        "Cravings pass in minutes -- have a walk or a glass of water ready.",
    ],
    "Sleep Apnea": [
        "Loud snoring with daytime sleepiness deserves a sleep evaluation -- ask your doctor.",
        "Avoid alcohol before bed; it worsens apnea.",
        "If you use a CPAP, wear it every night and keep it clean.",
    ],
    "GERD": [
        "Avoid lying down right after meals; raise the head of your bed.",
        "Note which foods trigger symptoms and limit them.",
        "If symptoms persist despite lifestyle changes, ask your doctor.",
    ],
    "Osteoporosis": [
        "Weight-bearing exercise and enough calcium/vitamin D support bone strength.",
        "Ask your doctor about a bone density scan schedule.",
        "Reduce fall risks at home: clear clutter, secure rugs, good lighting.",
    ],
    "Parkinson's Disease": [
        "Take Parkinson's medications on the exact schedule prescribed.",
        "Regular movement and physical therapy help maintain mobility.",
        "Report new falls, swallowing trouble, or mood changes promptly.",
    ],
    "Epilepsy": [
        "Take anti-seizure medication exactly as prescribed; never skip doses.",
        "Get enough sleep -- sleep deprivation is a common trigger.",
        "Know your state's rules about driving with epilepsy.",
    ],
    "Thyroid Disorder": [
        "Take thyroid medication on an empty stomach, same time daily.",
        "Recheck thyroid labs on the schedule your doctor sets.",
        "Report major energy, weight, or temperature-sensitivity changes.",
    ],
    "Anemia": [
        "Take iron as directed, if prescribed -- with vitamin C it absorbs better.",
        "Report unusual fatigue, dizziness, or pale skin to your doctor.",
        "Ask about checking iron levels again after treatment starts.",
    ],
    "Back Pain": [
        "Stay gently active -- prolonged bed rest usually makes back pain worse.",
        "Use heat or ice as advised; note what helps.",
        "Seek prompt care for numbness, weakness, or bladder/bowel changes.",
    ],
    "Fibromyalgia": [
        "Gentle, regular activity and good sleep hygiene help most people.",
        "Track flares: stress, weather, and activity patterns.",
        "Tell your doctor what is and isn't working -- treatment is trial and error.",
    ],
    "Atrial Fibrillation": [
        "Take blood thinners exactly as prescribed if you have them.",
        "Seek urgent care for chest pain, fainting, or a racing heartbeat.",
        "Limit alcohol and caffeine, which can trigger episodes.",
    ],
    "Eczema / Psoriasis": [
        "Moisturize daily; short lukewarm showers beat long hot ones.",
        "Note flare triggers: stress, soaps, fabrics, weather.",
        "If skin cracks, bleeds, or looks infected, see your doctor.",
    ],
    "IBS": [
        "Track foods and symptoms -- patterns emerge in a week or two.",
        "Eat slowly and regularly; large rushed meals often trigger symptoms.",
        "Report blood in stool, unexplained weight loss, or night symptoms promptly.",
    ],
    "Gout": [
        "During a flare: rest the joint, ice it, and use prescribed medication early.",
        "Limit alcohol (especially beer) and high-purine foods.",
        "Ask your doctor about long-term uric-acid-lowering treatment.",
    ],
}

_GENERIC_STEPS = [
    "Keep a simple symptom diary: what you feel, when, and what seems to help.",
    "Keep an up-to-date list of medications and bring it to every appointment.",
    "If symptoms worsen or worry you, contact your care team promptly.",
]

_WELLNESS_STEPS = [
    "Keep your annual checkup -- prevention beats treatment.",
    "Stay current on age-appropriate screenings (your doctor can list them).",
    "If anything changes, come back and tell us -- we will triage you then.",
]

_URGENT_HANDOFF_STEPS = [
    "Contact your doctor, specialist, or care team right away -- today, not next week.",
    "If symptoms are severe, new, or getting worse, call emergency services (911 in the US) or go to urgent care now.",
    "Do not wait for an email or app message for anything urgent -- call.",
    "Bring your medication list and recent test results to every appointment.",
]


def _parse_phrases(raw):
    """Split free text into condition phrases. Never iterate characters."""
    phrases = []
    for part in re.split(r"[;,]", raw.lower()):
        for q in re.split(r"\s+and\s+|\s*&\s*|\s+plus\s+", part):
            q = q.strip(" .")
            if q:
                phrases.append(q)
    seen, deduped = set(), []
    for q in phrases:
        if q not in seen:
            seen.add(q)
            deduped.append(q)
    return deduped


_NEG_RE = re.compile(r"\b(no|not|without|never|n't)\b(\s+[a-z'\-]+){1,4}")

def _strip_negations(phrase):
    """Blank out negated segments ('no diabetes', 'not hypertensive') so a
    denial is never misread as a diagnosis."""
    return _NEG_RE.sub("", phrase).strip()

def _map_phrases(phrase):
    """Return EVERY condition matched in one phrase (comma-less input like
    'diabetes high blood pressure' yields two conditions). Deduped by display
    name, keeping the highest weight. Negated segments are ignored."""
    clean = _strip_negations(phrase)
    found = {}
    for aliases, display, weight in _CONDITION_MAP:
        for a in aliases:
            if a and a in clean:
                if display not in found or weight > found[display]:
                    found[display] = weight
                break
    return list(found.items())


def _build_plan(display_names, tier, unknown):
    plan = []
    for dn in display_names:
        steps = DEMO.CONDITION_PLAYBOOKS.get(dn) or _EXTRA_SECTIONS.get(dn)
        if steps:
            plan.append({"condition": dn, "steps": list(steps)})
    if tier == "HIGH":
        plan.append({"condition": "High-risk follow-up",
                     "steps": ["Care manager will check in within 7 days.",
                               "If any symptoms worsen, call the clinic same-day."]})
    elif tier == "MEDIUM":
        plan.append({"condition": "Routine follow-up",
                     "steps": ["Care manager will check in within 30 days."]})
    if not plan or unknown or tier == "NEEDS REVIEW":
        plan.append({"condition": "General guidance (confirm with your care team)",
                     "steps": list(_GENERIC_STEPS)})
    return plan


def _print_pipeline(name, email, chan, display_names, tier, score, reasons, plan):
    patient = {
        "id": "WEB-001",
        "name": name,
        "age": 50,
        "email": email,
        "conditions": display_names,
        "last_visit": "not provided",
        "preferred_channel": chan,
        "risk_factors": {"from_user_input": True},
    }
    triage = {"tier": tier, "score": score, "reasons": reasons}
    print(f"[AuthAgent]    Login verified: {email}")
    print(f"[TriageAgent]  Scoring risk for {name} (conditions: {', '.join(display_names)})...")
    print(f"[TriageAgent]  Score {score} -> tier {tier}")
    for r in reasons:
        print(f"               - {r}")
    channel = DEMO.channel_agent(patient, triage)
    print(f"[ChannelAgent] Selected channel: {channel.upper()} (patient preference: {chan})")
    print(f"[CarePlanAgent] Assembled {len(plan)} care-plan section(s)")
    message = DEMO.message_agent(patient, triage, plan, channel)
    print(f"[MessageAgent] Rendered {channel.upper()} message:")
    print()
    print("-" * 72)
    print(message)
    print("-" * 72)

def _capture_canned():
    """Run the canned demo exactly as before (subprocess), capture stdout."""
    proc = subprocess.run(
        [sys.executable, str(DEMO_PY)],
        cwd=str(HERE),
        capture_output=True,
        text=True,
        timeout=600,
    )
    return proc.stdout or proc.stderr

def _capture_fn(fn, params):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            return fn(params)
    except Exception as exc:  # never crash the page on a bad input
        return "[web-ui] The personalized run hit an error and stopped safely.\n%s: %s" % (type(exc).__name__, exc)

# _capture_custom: personalized handlers may return a dict carrying a follow-up decision.
def _capture_custom(fn, params):
    try:
        res = fn(params)
    except Exception as exc:  # never crash the page on a bad input
        return {"output": "[web-ui] The personalized run hit an error and stopped safely.", "decision": None}
    if isinstance(res, dict):
        res.setdefault("decision", None)
        return res
    return {"output": res, "decision": None}

# ---- personalized run: input handling lives in app.py; demo.py untouched ----

def run_custom(params):
    if not isinstance(params, dict):
        params = {}
    name = (params.get("name") or "Guest").strip() or "Guest"
    raw = (params.get("conditions") or "").strip()
    chan = (params.get("channel") or "email").strip().lower()
    if chan not in ("email", "sms", "phone"):
        chan = "email"
    email = f"{re.sub(r'[^a-z0-9]', '', name.lower()) or 'guest'}@example.com"
    first = name.split()[0]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        _run_custom_body(name, raw, chan, email, first)
    return out.getvalue()


def _run_custom_body(name, raw, chan, email, first):
    print("=" * 70)
    print("YOUR RUN -- the five-agent pipeline triages YOUR input")
    print(f"You told us: name={name} | conditions={raw or '(none entered)'} | channel={chan}")

    if not raw:
        print("=" * 70)
        print("The agent needs something to triage: please type your health")
        print("conditions above (for example: 'type 2 diabetes, high blood")
        print("pressure') and press 'Triage me' again.")
        return

    low = raw.lower()
    # Negated denials ("no chest pain") must not escalate: strip them before
    # the critical check, so a denial is never misread as a symptom.
    low_denied = _strip_negations(low)

    # Gate 1 -- critical red flags, checked FIRST.
    hits = []
    for pat, label in _CRITICAL_PATTERNS:
        m = re.search(pat, low_denied)
        if m:
            hits.append((m.group(0), label))
    if hits:
        print("Critical-pattern check: RED FLAGS -> %s" % [h[0] for h in hits])
        print("=" * 70)
        print("[AuthAgent]    Login verified: " + email)
        print("[TriageAgent]  RED FLAG detected -- routine scoring bypassed.")
        for text, label in hits:
            print("               - %r: matched critical pattern (%s)" % (text, label))
        print("[TriageAgent]  Score 100 -> tier URGENT (escalation overrides routine scoring)")
        print("[ChannelAgent] Selected channel: PHONE (URGENT cases always use a phone")
        print("               call -- this cannot wait for an email)")
        print("[CarePlanAgent] Routine care-plan generation SKIPPED for URGENT cases.")
        print("[CarePlanAgent] Urgent clinical handoff instead:")
        for s in _URGENT_HANDOFF_STEPS:
            print("    - " + s)
        print("[MessageAgent] Rendered PHONE call script (urgent):")
        print()
        print("-" * 72)
        print("URGENT CARE OUTREACH -- call script for the care manager")
        print("Calling: %s (%s)" % (name, email))
        print()
        print("INTRO: \"Hi %s, this is your care team calling. You mentioned" % first)
        print("\"%s\" -- I want to be direct: this needs a real clinician" % raw)
        print("urgently, so I am not going to handle it with a routine care plan.\"")
        print()
        print("TALKING POINTS:")
        print("  - \"Please contact your doctor or specialist today -- not next week.\"")
        print("  - \"If anything feels severe or is getting worse, call emergency")
        print("     services (911 in the US) or go to urgent care right now.\"")
        print("  - \"Bring your medication list and recent test results.\"")
        print()
        print("CLOSE: \"I am flagging your record for a clinician follow-up within")
        print("24 hours. Your health comes before any automated plan.\"")
        print("-" * 72)
        print()
        print("IMPORTANT: this demo is not medical advice. It cannot diagnose or")
        print("treat you. For anything urgent, call your doctor, your specialist,")
        print("or emergency services right away.")
        return

    # Gate 1b -- privacy: requests for OTHER patients' data are refused
    # explicitly. Nothing is listed, shown, or disclosed, and no routine
    # care plan is generated for the request itself.
    if any(re.search(p, low) for p in _PRIVACY_PATTERNS):
        print("=" * 70)
        print("[AuthAgent]    Login verified: " + email)
        print("[PrivacyGuard] DATA-ACCESS REQUEST DECLINED.")
        print("               This demo never shares another patient's name,")
        print("               email address, conditions, or risk scores -- not")
        print("               listed, not summarized, not compared. Nothing was")
        print("               disclosed. If you want triage for YOURSELF, describe")
        print("               your own conditions above.")
        print("=" * 70)
        return

    # Gate 2 -- explicit wellness / no conditions.
    if any(re.search(p, low) for p in _WELLNESS_PATTERNS):
        display = ["(no conditions reported)"]
        tier, score = "LOW", 0
        reasons = ["no conditions reported by user (wellness path)"]
        plan = [{"condition": "Staying healthy", "steps": list(_WELLNESS_STEPS)}]
        print("Parsed condition phrases: [] (wellness path -- nothing to triage)")
        print("=" * 70)
        _print_pipeline(name, email, chan, display, tier, score, reasons, plan)
        print()
        print("Honesty note: you reported no conditions, so there is nothing to")
        print("triage -- the guidance above is general prevention only. If anything")
        print("changes, come back and tell us.")
        return

    # Gate 3 -- parse into phrases, map to known conditions.
    phrases = _parse_phrases(raw)
    recognized, unknown = [], []
    for ph in phrases:
        hits = _map_phrases(ph)
        if hits:
            for display, weight in hits:
                if all(d != display for d, _ in recognized):
                    recognized.append((display, weight))
        else:
            if _strip_negations(ph):
                unknown.append(ph)

    if not recognized:
        tier, score = "NEEDS REVIEW", 0
        reasons = ["unrecognized input %r: no weight assigned" % u for u in unknown]
        display_names = [raw]
    else:
        score = sum(w for _, w in recognized)
        if score >= _HIGH_TIER_AT:
            tier = "HIGH"
        elif score >= _MEDIUM_TIER_AT:
            tier = "MEDIUM"
        else:
            tier = "LOW"
        reasons = ["%s (+%d risk points)" % (d, w) for d, w in recognized]
        if unknown:
            reasons.append("unrecognized: %s (no weight assigned -- see honesty note)"
                           % ", ".join(repr(u) for u in unknown))
        display_names = [d for d, _ in recognized]

    print("Parsed condition phrases: %s" % phrases)
    if recognized:
        print("Recognized: %s" % ", ".join(d for d, _ in recognized))
    if unknown:
        print("Not recognized: %s" % ", ".join(unknown))
    print("=" * 70)

    plan = _build_plan([d for d, _ in recognized], tier, unknown)
    _print_pipeline(name, email, chan, display_names, tier, score, reasons, plan)
    print()
    if unknown:
        print("Honesty note: I don't recognize %s --"
              % ", ".join(repr(u) for u in unknown))
        print("I can't build condition-specific advice for it, so the plan above")
        print("covers only what I recognized, plus general guidance. Please confirm")
        print("the unrecognized part with your care team.")
    print("Honesty note: this web triage is rule-based and deterministic. It parses")
    print("your words into condition phrases, checks red-flag patterns first (those")
    print("always escalate to URGENT), and weighs recognized conditions. It is not")
    print("medical advice -- for anything urgent, call your doctor or emergency services.")

PAGE = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>Personalized Care Management Agent &mdash; Live Demo</title>\n<style>\n:root{\n  --bg:#0b1220; --bg2:#0e1626; --panel:#131e33; --panel2:#182742;\n  --ink:#eaf0f9; --muted:#9db0c9; --faint:#6b7f99;\n  --teal:#2dd4bf; --teal-dim:rgba(45,212,191,.12);\n  --accent:#5aa9ff; --warn:#fbbf24; --danger:#f87171; --ok:#34d399;\n  --line:#233451; --radius:14px;\n}\n*{box-sizing:border-box}\nbody{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;\n  background:var(--bg);color:var(--ink);line-height:1.6}\nheader{background:linear-gradient(135deg,#0a2540 0%,#0e3a5c 60%,#0b4f4a 100%);\n  padding:42px 32px 34px;border-bottom:1px solid var(--line)}\n.wrap{max-width:1060px;margin:0 auto}\nheader h1{margin:0 0 8px;font-size:30px;letter-spacing:-.01em}\nheader .sub{margin:0;color:#c8d6ea;font-size:16px;max-width:800px}\n.badge{display:inline-block;margin-top:14px;font-size:11.5px;letter-spacing:.1em;\n  text-transform:uppercase;color:#06281f;background:var(--teal);\n  padding:5px 14px;border-radius:999px;font-weight:800}\nmain{padding:8px 32px 48px}\nsection.card{background:var(--panel);border:1px solid var(--line);\n  border-radius:var(--radius);padding:26px 28px;margin:26px 0}\nsection.card h2{margin:0 0 12px;font-size:18px;color:var(--teal)}\nsection.card h2 .n{display:inline-block;width:28px;height:28px;border-radius:50%;\n  background:var(--teal-dim);border:1px solid var(--teal);color:var(--teal);\n  text-align:center;line-height:26px;font-size:14px;margin-right:10px}\nsection.card p{margin:0 0 12px;color:#d5e0f1;font-size:15.5px}\nsection.card p:last-child{margin-bottom:0}\n.watch{list-style:none;margin:6px 0 0;padding:0}\n.watch li{position:relative;padding:8px 0 8px 30px;color:#d5e0f1;font-size:15px;\n  border-bottom:1px dashed var(--line)}\n.watch li:last-child{border-bottom:0}\n.watch li::before{content:"\\25b8";position:absolute;left:8px;color:var(--teal);font-weight:700}\nlabel.f{display:block;margin:14px 0 6px;font-size:13px;font-weight:700;\n  letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}\ninput[type=text],input[type=number],select,textarea{\n  width:100%;background:var(--bg2);border:1px solid var(--line);color:var(--ink);\n  border-radius:10px;padding:11px 14px;font-size:15px;font-family:inherit}\ntextarea{min-height:76px;resize:vertical}\ninput:focus,select:focus,textarea:focus{outline:none;border-color:var(--teal)}\n.row2{display:grid;grid-template-columns:1fr 1fr;gap:14px}\n@media(max-width:700px){.row2{grid-template-columns:1fr}}\n.btnrow{display:flex;gap:14px;align-items:center;margin-top:20px;flex-wrap:wrap}\nbutton.run{background:linear-gradient(135deg,#14b8a6,#0d9488);border:0;\n  color:#04211c;font-weight:800;font-size:17px;padding:15px 34px;\n  border-radius:12px;cursor:pointer;box-shadow:0 6px 22px rgba(45,212,191,.25)}\nbutton.run:hover{filter:brightness(1.08)}\nbutton.run:disabled{opacity:.45;cursor:default;box-shadow:none}\nbutton.ghost{background:transparent;border:1px solid var(--teal);color:var(--teal);\n  font-weight:700;font-size:15px;padding:13px 26px;border-radius:12px;cursor:pointer}\nbutton.ghost:hover{background:var(--teal-dim)}\nbutton.ghost:disabled{opacity:.45;cursor:default}\n.hint{color:var(--muted);font-size:13.5px}\n.spinner{display:none;align-items:center;gap:10px;color:var(--muted);font-size:14px;margin-top:14px}\n.spinner.show{display:flex}\n.dot{width:12px;height:12px;border-radius:50%;background:var(--teal);\n  animation:pulse 1s infinite ease-in-out}\n@keyframes pulse{0%,100%{transform:scale(.6);opacity:.5}50%{transform:scale(1.2);opacity:1}}\n#output{display:none;margin-top:6px}\n#output.show{display:block}\n.out{background:#0a0f1c;border:1px solid var(--line);border-radius:12px;\n  padding:20px 22px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;\n  font-size:13px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;\n  max-height:640px;overflow:auto;color:#c9d6ea}\n.sechead{color:var(--accent);font-weight:800;margin:18px 0 2px;font-size:13.5px}\n.sechead:first-child{margin-top:0}\n.seccap{background:var(--teal-dim);border-left:3px solid var(--teal);\n  padding:8px 12px;margin:4px 0 12px;border-radius:0 8px 8px 0;\n  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;\n  font-size:13.5px;color:#bfe9e2}\n.tok-orch{color:var(--accent);font-weight:700}\n.tok-tool{color:var(--ok);font-weight:700}\n.tok-guard{color:var(--warn);font-weight:700}\n.tok-mem{color:#c084fc;font-weight:700}\n#takeaways{display:none}\n#takeaways.show{display:block}\n.take{background:rgba(52,211,153,.07);border:1px solid rgba(52,211,153,.4);\n  border-radius:var(--radius);padding:22px 26px;margin:26px 0}\n.take h2{color:var(--ok);margin:0 0 10px;font-size:18px}\n.take ul{margin:0;padding-left:20px}\n.take li{margin:8px 0;color:#d5e0f1;font-size:15px}\ntable.dec{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px}\ntable.dec th{background:var(--panel2);color:var(--teal);text-align:left;\n  padding:10px 12px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;\n  border-bottom:1px solid var(--line)}\ntable.dec td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}\n.pill{display:inline-block;padding:3px 12px;border-radius:999px;font-weight:800;font-size:12px}\n.pill.v{background:var(--ok);color:#04281c}\n.pill.s{background:var(--faint);color:#0b1220}\nfooter{padding:26px 32px 40px;color:var(--faint);font-size:13.5px;text-align:center}\nfooter a{color:var(--teal);text-decoration:none}\nfooter a:hover{text-decoration:underline}\ndetails.raw{margin-top:14px}\ndetails.raw summary{cursor:pointer;color:var(--muted);font-size:13.5px}\n\n/* --- care revamp: why-section + sidebar layout --- */\n.care-layout{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:26px;align-items:start}\n.care-main{min-width:0}\n.care-sidebar{position:sticky;top:20px;min-width:0}\n@media(max-width:960px){.care-layout{grid-template-columns:1fr}.care-sidebar{position:static}}\n.side-card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:20px;margin-bottom:20px}\n.side-card h3{margin:0 0 10px;font-size:15px;color:var(--teal)}\n.side-vid{margin-bottom:18px}\n.side-vid:last-child{margin-bottom:0}\n.side-vid iframe{width:100%;aspect-ratio:16/9;border:0;border-radius:10px;display:block;background:#000}\n.side-vid p{font-size:13px;color:var(--muted);margin:8px 0 0;line-height:1.5}\n.why-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin:16px 0}\n@media(max-width:700px){.why-grid{grid-template-columns:1fr}}\n.why-grid figure{margin:0}\n.why-grid img{width:100%;aspect-ratio:16/10;object-fit:cover;border-radius:10px;border:1px solid var(--line);display:block;background:#0a0f1c}\n.why-grid figcaption{font-size:12.5px;color:var(--muted);margin-top:6px;line-height:1.5}\n.chips{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 4px}\n.chip{background:var(--panel2);border:1px solid var(--teal);color:var(--teal);font-size:13px;padding:7px 14px;border-radius:999px;cursor:pointer;font-family:inherit;line-height:1.4}\n.chip:hover{background:var(--teal-dim)}\n.chal{list-style:none;margin:10px 0 0;padding:0}\n.chal li{position:relative;padding:7px 0 7px 28px;color:#d5e0f1;font-size:15px}\n.chal li::before{content:"!";position:absolute;left:9px;color:var(--warn);font-weight:800}\n\n\n.blog-list{list-style:none;margin:0;padding:0}\n.blog-list li{margin:0 0 14px;padding-bottom:14px;border-bottom:1px dashed var(--line)}\n.blog-list li:last-child{margin-bottom:0;padding-bottom:0;border-bottom:0}\n.blog-list a{color:var(--teal);font-weight:700;font-size:14.5px;text-decoration:none}\n.blog-list a:hover{text-decoration:underline}\n.blog-list span{display:block;font-size:13px;color:var(--muted);margin-top:3px;line-height:1.5}</style>\n</head>\n<body>\n<header><div class="wrap">\n  <h1>Personalized Care Management Agent</h1>\n  <p class="sub">From one generic blast email to a personal care plan for every patient.</p>\n</div></header>\n<main><div class="wrap care-layout"><div class="care-main">\n\n\n<section class="card" id="why">\n  <h2><span class="n">&#9733;</span>Why personalized care?</h2>\n  <p>Most health outreach still works like a megaphone: one generic message &mdash; <i>&ldquo;get yourself checked&rdquo;</i> &mdash; blasted at everyone. But a 70-year-old managing diabetes and a healthy 40-year-old do not need the same message, the same urgency, or even the same channel. One-size-fits-all care plans fail because people are not one size.</p>\n  <p>Chronic conditions need steady follow-up <b>between</b> visits, not a pamphlet handed out once a year. Patients fall through the cracks when nobody checks in the right way at the right time. And a perfect care plan sent over a channel the patient never reads might as well not exist.</p>\n  <div class="why-grid">\n    <figure><img src="/assets/img/doctor-consult.svg" alt="Doctor consulting with a patient in an exam room" loading="lazy"><figcaption>A real care conversation: the plan starts with the person, not the protocol.</figcaption></figure>\n    <figure><img src="/assets/img/nurse-senior.svg" alt="Nurse attending to a senior patient" loading="lazy"><figcaption>Older patients with chronic conditions need continuous, personal follow-up.</figcaption></figure>\n    <figure><img src="/assets/img/telehealth.svg" alt="Doctor on a telehealth video call" loading="lazy"><figcaption>Outreach on the patient\'s preferred channel &mdash; video, phone, text, or email.</figcaption></figure>\n    <figure><img src="/assets/img/homecare.svg" alt="Home nursing care" loading="lazy"><figcaption>Care that reaches people where they are &mdash; including at home.</figcaption></figure>\n  </div>\n  <p><b>The purpose of this demo:</b> it shows an AI agent that builds a care plan around <b>you</b> &mdash; your conditions, your preferred way of being contacted &mdash; instead of handing everyone the same generic pamphlet. Try it on yourself below.</p>\n  <p><b>The challenges it tackles:</b></p>\n  <ul class="chal">\n    <li>Generic blast messages that patients ignore</li>\n    <li>No follow-up between doctor visits for chronic conditions</li>\n    <li>The right message sent on the wrong channel</li>\n    <li>One person can\'t do it all &mdash; triage, channel choice, and messaging have to work together</li>\n  </ul>\n</section>\n\n<section class="card" id="story">\n  <h2><span class="n">1</span>The story</h2>\n  <p>Care teams doing health outreach have one legacy tool: the generic blast. One message — <i>"Get yourself checked. Visit a physician."</i> — sent to every patient. The patient with uncontrolled diabetes gets the exact same note as a healthy 45-year-old. It is cheap to send and nearly useless to receive.</p>\n<p>This demo shows the before and after. First the prior-era blast, then five agents — <b>Auth</b>, <b>Triage</b>, <b>Channel</b>, <b>Care Plan</b>, <b>Message</b> — working three fictional patients: Priya Sharma (diabetes + hypertension, prefers email), Maria Garcia (diabetes + kidney disease, prefers SMS), James Carter (hypertension, prefers a phone call). Each gets a risk tier and a message on the channel they will actually read.</p>\n</section>\n\n<section class="card" id="watch">\n  <h2><span class="n">2</span>What to watch for</h2>\n  <ul class="watch">\n<li>Watch the same five-agent pipeline run three times — and produce three different risk tiers (HIGH, MEDIUM, LOW) from the same rules.</li>\n<li>Notice how the channel changes per patient: email for Priya, SMS for Maria, a phone-call script for James.</li>\n<li>In Act 3, compare the generic blast side-by-side with the personalized plans — the whole business case on one screen.</li>\n  </ul>\n</section>\n\n\n\n<section class="card" id="tryown">\n  <h2><span class="n">✎</span>Try your own</h2>\n  <p>Give the agent your own details and it will triage <b>you</b> — same five-agent pipeline, same rules, personalized plan and message.</p>\n  <label class="f" for="c_name">Your name</label>\n  <input type="text" id="c_name" value="Alex Morgan">\n  \n  <label class="f">Not sure what to type? Try one of these:</label>\n  <div class="chips">\n    <button type="button" class="chip">Type 2 diabetes, high blood pressure</button>\n    <button type="button" class="chip">Asthma and seasonal allergies</button>\n    <button type="button" class="chip">Recovering from knee surgery</button>\n    <button type="button" class="chip">High cholesterol, trying to quit smoking</button>\n    <button type="button" class="chip">Migraines, sensitive to light</button>\n    <button type="button" class="chip">Caring for a parent with dementia</button>\n    <button type="button" class="chip">Sleep apnea and loud snoring</button>\n    <button type="button" class="chip">Thyroid problems, always tired</button>\n    <button type="button" class="chip">Back pain and sciatica</button>\n    <button type="button" class="chip">Eczema flare-ups</button>\n  </div>\n\n  <label class="f" for="c_cond">Your health conditions (free text)</label>\n  <input type="text" id="c_cond" value="type 2 diabetes, high blood pressure">\n  <label class="f" for="c_chan">How should we reach you?</label>\n  <select id="c_chan">\n    <option value="email">Email</option>\n    <option value="sms">SMS (text message)</option>\n    <option value="phone">Phone call</option>\n  </select>\n  <div class="btnrow">\n    <button class="ghost" id="customRun">Triage me</button>\n    <span class="hint">Same inputs → same output. Deterministic.</span>\\n  </div>\\n  <p class="hint" style="margin-top:10px">Safety: this demo is not medical advice. Red-flag symptoms always escalate &mdash; and for anything urgent, call your doctor or emergency services.</p>\n  <div class="spinner" id="cspin"><div class="dot"></div>Personalizing your care plan…</div>\n</section>\n\n\n<section class="card" id="runbox">\n  <h2><span class="n">3</span>Run the demo</h2>\n  <p>Click below to run the full canned demonstration. It takes a few seconds.</p>\n  <div class="btnrow">\n    <button class="run" id="run">&#9654; Run live demo</button>\n  </div>\n  <div class="spinner" id="spin"><div class="dot"></div><span>The five agents are triaging the three patients…</span></div>\n  <div id="output">\n    <div class="out" id="outtext"></div>\n    <details class="raw"><summary>Show raw terminal output</summary>\n      <div class="out" id="rawtext"></div>\n    </details>\n  </div>\n</section>\n\n<section class="card" id="takeaways" style="display:none">\n  <div class="take">\n    <h2>What just happened</h2>\n    <ul>\n<li>One pipeline, three different outcomes: the agents produced HIGH, MEDIUM, and LOW risk tiers from identical rules — personalization comes from the data, not from hand-writing.</li>\n<li>Channel matters as much as content: the same plan delivered by email, SMS, or phone script reaches different patients.</li>\n<li>The side-by-side in Act 3 is the business case: generic outreach is cheap to send and nearly useless to receive.</li>\n<li>Try it on yourself: type your name and conditions in “Try your own” above and watch the same five agents triage you.</li>\n    </ul>\n  </div>\n</section>\n\n</div>\n<aside class="care-sidebar">\n  <div class="side-card">\n    <h3>Learn more</h3>\n    <p style="font-size:13.5px;color:var(--muted);margin:0 0 14px">Want to go deeper on personalized care? Start with these.</p>\n    <div class="side-vid">\n      <iframe src="https://www.youtube-nocookie.com/embed/GUJ-yTThzho" title="Genomics and personalized medicine explained" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n      <p>A human geneticist explains how your genes can shape treatment &mdash; the science behind &ldquo;care built around you.&rdquo;</p>\n    </div>\n    <div class="side-vid">\n      <iframe src="https://www.youtube-nocookie.com/embed/irafmjNvr6A" title="Personalized healthcare: biology, provider insight, and patient choice" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n      <p>Doctors discuss what personalizing care really means &mdash; beyond genetics, it&rsquo;s about the patient&rsquo;s values and goals.</p>\n    </div>\n    <div class="side-vid">\n      <iframe src="https://www.youtube-nocookie.com/embed/pbSHdjvG3Bk" title="Mayo Clinic: precision medicine patient story" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n      <p>Mayo Clinic shows precision medicine in action through a real patient&rsquo;s story.</p>\n    </div>\n  </div>\n<div class="side-card">\n<h3>Go deeper &mdash; articles</h3>\n<ul class="blog-list">\n<li><a href="https://www.patientpartner.com/blog/how-personalized-care-plans-improve-chronic-disease-outcomes" target="_blank" rel="noopener">How Personalized Care Plans Improve Chronic Disease Outcomes</a><span>PatientPartner &mdash; What the evidence says about tailored plans: engagement, adherence, fewer complications.</span></li>\n<li><a href="https://www.madisonintegrativemedicine.com/personalized-care-plans-why-one-size-fits-all-doesnt-work-for-chronic-conditions/" target="_blank" rel="noopener">Why One-Size-Fits-All Fails for Chronic Conditions</a><span>Madison Integrative Medicine &mdash; A clinician\'s walkthrough of building a plan around the person, not the protocol.</span></li>\n<li><a href="https://www.einnews.com/pr_news/947828326/walmart-and-scan-launch-co-branded-medicare-advantage-plans-designed-to-deliver-more-personalized-health-support-for-older-adults" target="_blank" rel="noopener">Walmart and SCAN Launch Personalized Medicare Advantage Plans</a><span>EIN News &mdash; Real-world news: a retailer and a health plan teaming up on personalized senior care.</span></li>\n</ul>\n</div>\n</aside>\n</div></main>\n<footer><div class="wrap">\n  <a href="https://github.com/ynpreet/agentic-care-management" target="_blank" rel="noopener">View the project on GitHub</a>\n  &nbsp;&middot;&nbsp; All data in this demo is synthetic / fictional.\n</div></footer>\n\n<script>\nconst SECTIONS = [["ACT 1", "The prior era: one generic message blasted to every patient \\u2014 no name, no condition, no next step."], ["ACT 2", "The agentic era: five agents triage and personalize, one patient at a time."], ["PATIENT 1/3", "Priya Sharma: Auth verifies her login, Triage scores her risk, Channel picks email \\u2014 then her personal plan and message."], ["PATIENT 2/3", "Maria Garcia: the same pipeline, a different patient \\u2014 different tier, different channel (SMS)."], ["PATIENT 3/3", "James Carter: the lowest risk of the three, but he still gets a plan \\u2014 on his preferred channel, a phone script."], ["ACT 3", "Side-by-side: the blast versus the personalized plans. This is the entire argument in one screen."]];\nfunction esc(s){return s.replace(/&/g,\'&amp;\').replace(/</g,\'&lt;\').replace(/>/g,\'&gt;\');}\nfunction decorate(line){\n  let h = esc(line);\n  h = h.replace(/\\[ORCHESTRATOR\\]/g,\'<span class="tok-orch">[ORCHESTRATOR]</span>\');\n  h = h.replace(/\\[TOOL [^\\]]+\\]/g,function(m){return \'<span class="tok-tool">\'+m+\'</span>\';});\n  h = h.replace(/\\[MEMORY\\]/g,\'<span class="tok-mem">[MEMORY]</span>\');\n  h = h.replace(/GUARDRAIL/g,\'<span class="tok-guard">GUARDRAIL</span>\');\n  return h;\n}\nfunction renderOut(text){\n  document.getElementById(\'rawtext\').textContent = text;\n  const lines = text.split(\'\\n\');\n  let html = \'\';\n  for(const line of lines){\n    let matched = null;\n    for(const s of SECTIONS){ if(line.indexOf(s.m) !== -1){ matched = s; break; } }\n    if(matched){\n      html += \'<div class="sechead">\'+decorate(line)+\'</div>\'+\n              \'<div class="seccap">\'+matched.c+\'</div>\';\n      continue;\n    }\n    html += decorate(line) + \'\\n\';\n  }\n  document.getElementById(\'outtext\').innerHTML = html;\n  document.getElementById(\'output\').classList.add(\'show\');\n  document.getElementById(\'output\').scrollIntoView({behavior:\'smooth\',block:\'start\'});\n}\nfunction showTakeaways(){\n  const t = document.getElementById(\'takeaways\');\n  t.style.display=\'block\'; t.classList.add(\'show\');\n  t.scrollIntoView({behavior:\'smooth\',block:\'start\'});\n}\ndocument.getElementById(\'run\').addEventListener(\'click\',function(){\n  const btn=this, spin=document.getElementById(\'spin\');\n  btn.disabled=true; spin.classList.add(\'show\');\n  fetch(\'/api/run\').then(r=>r.json()).then(j=>{\n    spin.classList.remove(\'show\'); btn.disabled=false;\n    renderOut(j.output);\n    if(typeof loadDecisionTable===\'function\') loadDecisionTable();\n    showTakeaways();\n  }).catch(e=>{spin.classList.remove(\'show\');btn.disabled=false;alert(\'Run failed: \'+e);});\n});\n\nfunction collectCustom(){\n  return {name:document.getElementById(\'c_name\').value,\n          conditions:document.getElementById(\'c_cond\').value,\n          channel:document.getElementById(\'c_chan\').value};\n}\n\nfunction wireCustom(){\n  const b=document.getElementById(\'customRun\');\n  if(!b) return;\n  b.addEventListener(\'click\',function(){\n    const spin=document.getElementById(\'cspin\');\n    b.disabled=true; spin.classList.add(\'show\');\n    fetch(\'/api/custom\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},\n      body:JSON.stringify(collectCustom())})\n    .then(r=>r.json()).then(j=>{\n      spin.classList.remove(\'show\'); b.disabled=false;\n      if(j.error){alert(j.error);return;}\n      renderOut(j.output); showTakeaways();\n    }).catch(e=>{spin.classList.remove(\'show\');b.disabled=false;alert(\'Run failed: \'+e);});\n  });\n}\nwireCustom();\n\n/* care revamp: example chips fill the conditions input */\ndocument.querySelectorAll(\'.chip\').forEach(function(ch){\n  ch.addEventListener(\'click\', function(){\n    var inp = document.getElementById(\'c_cond\');\n    inp.value = ch.textContent.trim();\n    inp.scrollIntoView({behavior:\'smooth\', block:\'center\'});\n    inp.focus();\n  });\n});\n\n</script>\n</body>\n</html>\n'

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "WorkshopUI/1.0"

    def _send(self, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        self._send(json.dumps(obj), "application/json; charset=utf-8")

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            length = 0
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return {}

    def _serve_asset(self, path):
        safe = (HERE / path.lstrip("/")).resolve()
        try:
            safe.relative_to(HERE / "assets")
        except ValueError:
            return self.send_error(403, "forbidden")
        if not safe.is_file():
            return self.send_error(404, "not found")
        ctype, _ = mimetypes.guess_type(str(safe))
        data = safe.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path in ("/", "/index.html"):
            self._send(PAGE)
        elif path == "/api/run":
            self._json({"output": _capture_canned()})
        elif path.startswith("/assets/"):
            self._serve_asset(path)
        else:
            self.send_error(404, "not found")

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/api/custom":
            params = self._read_json()
            self._json(_capture_custom(run_custom, params))
        else:
            self.send_error(404, "not found")

    def log_message(self, fmt, *args):
        sys.stderr.write("ui: " + (fmt % args) + "\n")


def main():
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    print("Personalized Care Management Agent demo UI -> http://localhost:8001")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
