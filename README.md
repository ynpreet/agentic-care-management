# Personalized Care Management Agent

**Demo 1 of 4 · Agentic AI Workshop**

> **Educational demo.** Condition playbooks are simplified teaching examples,
> not medical advice. All patients are fictional; all data is local
> (`mock_patients.json`). No network, no API keys, no costs.

## Open in Chrome (fastest way to see it)

One command:

```bash
python3 app.py
```

The terminal prints:

```
============================================================
  Open in Chrome: http://localhost:8001
============================================================
```

Then in Chrome: open **http://localhost:8001** → click **Run live demo**
→ the agent trace renders in the browser (plan highlighted, then each
agent step), with a results panel below. Port **8001**, localhost only,
Python stdlib only — no installs, no network, no API keys.

---

## Real-world problem, target users, market need, and differentiation

**The problem.** Care teams doing population-health outreach have one legacy
tool: the generic blast. One message — *"Get yourself checked. Visit a
physician."* — sent to every patient. No name, no condition, no next step,
no channel choice. The patient with uncontrolled diabetes gets the exact
same note as a healthy 45-year-old. It's cheap to send and nearly useless
to receive.

**Target users.** Care managers and care coordinators at provider
organizations and health plans who run outreach to attributed patient
panels — the people who today do this work manually, one patient at a time.

**Market need.** Personalization is what makes outreach work, but
personalization is labor-intensive: knowing each patient's risk factors,
picking the channel they'll actually read, and writing a plan they can act
on. Every manual hour spent personalizing is an hour not spent on actual
care. The need is a system that does the triage-and-personalize loop
automatically, per patient, without losing the clinical judgment of which
patient needs what.

**Differentiation.** This demo is not a smarter message template. It is a
before/after story: prior-era blast (one message, email-only, manual labor)
versus agentic-era flow (risk-triaged, condition-aware, channel-aware,
executed by a pipeline of five agents). Three fictional patients — Priya
Sharma (Type 2 Diabetes + Hypertension, email), Maria Garcia (Type 2
Diabetes + Chronic Kidney Disease, SMS), James Carter (Hypertension only,
phone call) — show why the blast fails and what an agentic system does
instead.

---

## Meaningful Agentic AI functionality

**Why an agent, not a chatbot?** A chatbot answers a question you ask. This
system *executes a multi-step workflow nobody asked it to explain*:

- **AuthAgent** verifies the patient logs in (email lookup).
- **TriageAgent** scores clinical risk (0–100) from structured risk factors
  — A1C, systolic BP, eGFR, missed refills, ER visits, visit recency — and
  assigns a HIGH / MEDIUM / LOW tier.
- **ChannelAgent** picks the outreach channel: the patient's stated
  preference first, with a HIGH-risk urgency override toward a phone call
  (or an urgent follow-up CTA when the patient prefers email/SMS).
- **CarePlanAgent** assembles a personalized plan from condition-specific
  playbooks plus tier-based follow-ups (7-day check-in for HIGH, 30-day for
  MEDIUM).
- **MessageAgent** renders the message in the channel's native shape: a full
  email with subject line, compressed SMS texts, or a care-manager call
  script with intro, talking points, risks to acknowledge, and a booking
  close.

No single LLM call could do this reliably: the system chains five
specialized steps, each with an input/output contract, per patient,
automatically. That pipeline — not the prose — is the agentic
functionality. (The README's architecture section notes these are
deliberately rule-based functions with no framework and no LLM calls, so
students see the *orchestration* pattern cleanly before adding real models
later in the workshop.)

---

## Project scope, inputs, outputs, constraints, success criteria, and definition of done

**Scope.** A deterministic, offline demo of the personalized-outreach loop:
authenticate → triage → choose channel → build plan → render message — for
three fictional patients in canned mode, plus a live Q&A mode where an
audience member logs in as a patient and gets a plan.

**Inputs.**

- `mock_patients.json`: three fictional patients — name, email, conditions,
  risk factors (A1C, systolic BP, eGFR, missed refills, ER visits in last
  6 months), last-visit date, preferred channel.
- Interactive mode: patient email, conditions (from a known list), channel
  choice.

**Outputs.**

- Triage result per patient: risk score (0–100), tier (HIGH/MEDIUM/LOW),
  named reasons.
- Chosen channel (email / sms / phone).
- Personalized care-plan sections per condition + tier follow-up.
- Channel-tailored message: email with subject line, short SMS texts, or a
  call script.

**Constraints.** Python 3.8+ stdlib only — no frameworks, no LLM calls, no
network, no API keys. Fully deterministic: fixed `DEMO_TODAY`
(2026-10-10), same output every run. Educational content only — condition
playbooks are simplified teaching examples, never medical advice.

**Success criteria.** Three patients triaged with correct tiers (Priya HIGH
75, Maria MEDIUM, James LOW), three channel-correct messages rendered,
interactive mode handles unknown logins gracefully, and `TEST-LOG.md`
records 10/10 byte-identical runs.

**Definition of done.** Canned demo runs end-to-end and exits 0;
interactive mode works live on stage; the README carries all 10 checklist
sections; `TEST-LOG.md` shows the 10/10 determinism gate passing.

---

## Documented single-agent or multi-agent workflow

**Multi-agent workflow** — a pipeline of five single-purpose agents, each
with one input/output contract:

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│  AuthAgent  │────▶│ TriageAgent  │────▶│ ChannelAgent │────▶│ CarePlanAgent │────▶│ MessageAgent │
│             │     │              │     │              │     │               │     │              │
│ Verifies    │     │ Scores risk  │     │ Picks        │     │ Builds a      │     │ Renders the  │
│ patient     │     │ (0–100) from │     │ outreach     │     │ personalized  │     │ message for  │
│ login by    │     │ A1C, BP,     │     │ channel      │     │ plan from     │     │ the channel: │
│ email       │     │ eGFR, ER     │     │ (email/sms/  │     │ condition     │     │ email w/     │
│             │     │ visits,      │     │ phone) from  │     │ playbooks +   │     │ subject,     │
│             │     │ refills,     │     │ patient      │     │ risk-tier     │     │ short SMS,   │
│             │     │ visit        │     │ preference   │     │ follow-ups    │     │ or a call    │
│             │     │ recency      │     │ (+ urgency   │     │               │     │ script       │
│             │     │              │     │ override)    │     │               │     │              │
└─────────────┘     └──────────────┘     └──────────────┘     └───────────────┘     └──────────────┐
                                                                                       │
                                                            mock_patients.json ──────────┘
                                                            (fictional patients,
                                                             local JSON)
```

**Risk tiers** (deterministic rules, no randomness):

| Score | Tier | Follow-up |
|---|---|---|
| ≥ 50 | HIGH | Care manager check-in within 7 days; urgent CTA in the message |
| 25–49 | MEDIUM | Check-in within 30 days |
| < 25 | LOW | Routine messaging |

**Why this shape matters for the workshop:** every agent has a single
input/output contract, so in later demos we can swap a rule-based agent for
an LLM call, add a guardrail agent, or parallelize — without restructuring
anything.

---

## Working prototype evidence, source code, and setup instructions

### Setup (MacBook, step by step)

You need nothing but Python 3, which ships with macOS.

**1. Open Terminal.** (Spotlight → type "Terminal" → Enter.)

**2. Check Python:**

```bash
python3 --version
```

Any Python 3.8+ works.

**3. Go to the demo folder:**

```bash
cd ~/workspace/agentic-ai-workshop/care-management-agent
```

**4. Start the web UI:**

```bash
python3 app.py
```

The terminal prints:

```
============================================================
  Open in Chrome: http://localhost:8001
============================================================
```

That's it — no arguments, no installs. Port 8001, localhost only,
Python stdlib only.

**5. Demo it live in Chrome:** open **http://localhost:8001** in Chrome,
click **Run live demo**, and narrate the trace as it renders — the
highlighted PLAN (the before/after story), then each agent step
(`[AuthAgent]` → `[TriageAgent]` → `[ChannelAgent]` →
`[CarePlanAgent]` → `[MessageAgent]`) for Priya, Maria, and James, and
the results panel with risk tiers and channels. The trace is the real
`python3 demo.py` output — fully deterministic, same every run, so it
never surprises you on stage.

**6. Run the canned demo in the terminal (optional):**

```bash
python3 demo.py
```

The full demo plays end to end and exits 0 on success.

**7. Try the live Q&A mode (optional, terminal):**

```bash
python3 demo.py --interactive
```

You'll be prompted to "log in" with a mock patient email, enter conditions,
and pick an outreach channel. Mock logins are listed in the prompt — e.g.
`priya.sharma@example.com`.

### Files

| File | What it is |
|---|---|
| `demo.py` | The demo. Pure Python stdlib, zero dependencies. Canned mode (`python3 demo.py`) + interactive mode (`--interactive`). |
| `mock_patients.json` | Three fictional patients: conditions, risk factors, channel preferences. |
| `app.py` | The localhost web UI: Python stdlib only (`http.server`), port 8001. Open http://localhost:8001 in Chrome and click "Run live demo" — it runs `python3 demo.py` and renders the trace in the browser. |
| `streamlit-app-legacy.py` | The earlier optional Streamlit UI (needs `pip install streamlit`) — preserved as-is, superseded by `app.py`. |
| `requirements.txt` | Pinned requirements — for the legacy Streamlit app only. `demo.py` and `app.py` need nothing. |
| `TEST-LOG.md` | Reliability gates: 10 consecutive CLI runs (exit code + SHA-256, all passing) and 12 consecutive web-UI rounds (port 8001 serve + `/api/run` markers, all passing). |

### Screenshots

> *(Placeholders — capture during your dry run.)*

- `docs/screenshots/act1-blast.png` — Act 1: the generic blast output
- `docs/screenshots/act2-priya.png` — Act 2: Priya's agent trace + email
- `docs/screenshots/act2-maria.png` — Act 2: Maria's SMS message
- `docs/screenshots/act2-james.png` — Act 2: James's call script
- `docs/screenshots/act3-sidebyside.png` — Act 3: the comparison
- `docs/screenshots/streamlit-ui.png` — the optional Streamlit UI
- `docs/screenshots/web-ui.png` — the localhost web UI: Chrome at
  http://localhost:8001 after clicking "Run live demo" (trace + results)

### The demo script (with speaker notes)

Run `python3 app.py`, open **http://localhost:8001** in Chrome, click
**Run live demo**, and narrate — or run `python3 demo.py` in the terminal
and narrate the same acts. Approximate runtime: 4–5 minutes.

**Act 1 — The prior era (~45 seconds)**

> **Say:** "This is how it used to work. The care team had one job: send a
> health reminder to the whole patient list. So they sent *this* — the same
> line to everyone."

The screen shows the blast: *"Get yourself checked. Visit a physician."*

> **Say:** "Notice what's missing. No name. No condition. No next step. No
> choice of channel. The patient with uncontrolled diabetes gets the exact
> same note as a healthy 45-year-old. It's cheap to send — and nearly
> useless to receive."

**Live-demo cue:** pause here. Ask the room: *"Has anyone ever gotten a
message like this from a hospital? Did it change what you did that week?"*
Let the silence land.

**Act 2 — The agentic era (~3 minutes)**

> **Say:** "Now the agentic system. Watch the trace on the left of each
> output — five agents, one job each, working one patient at a time."

**Patient 1 — Priya Sharma** (Type 2 Diabetes + Hypertension, email):

> **Say:** "Priya logs in with her email. The triage agent scores her risk
> — A1C 9.2, systolic 148, missed refills, an ER visit, no visit in 90
> days. Score 75: HIGH. Her preference is email, so she gets a full email:
> a subject line naming her conditions, a care plan with her actual risk
> factors acknowledged, and a 7-day follow-up call to action."

**Patient 2 — Maria Garcia** (Type 2 Diabetes + Chronic Kidney Disease,
SMS):

> **Say:** "Maria is our diabetes-plus-chronic-disease patient. Triage
> catches her kidney risk — eGFR 38, A1C 8.1 — and lands her at MEDIUM. But
> Maria doesn't read long emails; she prefers SMS. So the message agent
> compresses the plan into a few short texts with the top two actions. Same
> clinical content, completely different shape."

**Patient 3 — James Carter** (Hypertension only, phone):

> **Say:** "James has one condition, low risk — but he prefers a phone
> call. The agent doesn't send him an email he won't open. It generates a
> *call script* for the care manager: intro, talking points pulled from his
> plan, and a closing that asks to book the follow-up before hanging up."

**Live-demo cue:** after each patient, point at the `[TriageAgent] -> tier`
line. That's the moment the system *knows* something the blast never knew.

**Act 3 — Side-by-side (~30 seconds)**

> **Say:** "Same care team, same data, two eras. On the left: twelve words
> sent to everyone. On the right: a plan that knows Priya's A1C is 9.2. The
> blast costs nothing to send and earns nothing back. The agentic flow costs
> the same to *run* — and it actually reaches the patient where they are."

**Optional closer:** re-run `python3 demo.py --interactive`, log in as a
patient, and take a condition + channel suggestion from the audience. This
is the "it's really running live" moment.

---

## Functional and end-to-end testing, realistic scenarios, failure cases, reliability, and human oversight

**Realistic scenarios (end to end).** The canned demo runs all three
fictional patients end to end — Act 1 (the blast), Act 2 (three agentic
flows), Act 3 (side-by-side) — in 4–5 minutes, exiting 0. The interactive
mode is a live scenario: log in as a patient, enter conditions, pick a
channel, get a plan.

**Failure cases the demo handles** (all from `demo.py` behavior):

- **Unknown login.** `auth_agent` returns `None` for an unrecognized email;
  interactive mode prints `No patient found for '<email>'. Try one of the
  mock emails.` and exits 1 — no crash, no default patient assumed.
- **Invalid channel preference.** If `preferred_channel` isn't
  email/sms/phone, `channel_agent` falls back to email rather than failing.
- **Unknown condition.** Interactive mode maps entered text against the
  known playbook list; unrecognized entries are dropped, and if none match
  it falls back to the patient's on-file conditions. `care_plan_agent`
  likewise skips conditions with no playbook (`CONDITION_PLAYBOOKS.get`
  returns `[]`).
- **Unparseable last-visit date.** A bad date string appends the reason
  `"last visit date unknown"` and scoring continues — one bad field never
  kills triage.
- **Missing risk factors.** Every factor is read with `.get()` defaults, so
  a sparse record still produces a score and tier.

**Reliability gate.** `TEST-LOG.md` records 10 consecutive runs of
`python3 demo.py` — exit codes + SHA-256 of full output — with the result
**10/10 PASSED, byte-identical output on every run**. Fixed `DEMO_TODAY`
and no randomness make the demo stage-safe.

**Human oversight.** This is an educational demo, not a clinical tool: the
playbooks are simplified teaching examples, explicitly not medical advice.
A production version would route HIGH-risk patients to licensed care
managers who review and approve every message before it goes out — the demo
generates the call script *for* the care manager, modeling that handoff.

---

## Focus, feasibility, and avoidance of unnecessary complexity

The demo is deliberately small: five agents, three patients, one JSON file,
stdlib only. Complexity was *removed* on purpose:

- **No frameworks, no LLM calls.** Each "agent" is a small, testable
  function with one job. Students see the orchestration pattern — plan,
  tools, contracts — before real models are added later in the workshop.
- **No database.** `mock_patients.json` is the entire data layer; adding
  SQLite or an ORM would teach nothing the demo needs.
- **Deterministic by design.** Fixed "today," no randomness, no wall clock
  — so the demo is reproducible and stage-safe instead of "mostly works."
- **Optional extras stay optional.** The localhost web UI (`app.py`,
  stdlib-only) and the interactive mode are separate entry points; the
  canned demo needs nothing beyond Python 3. (The old Streamlit UI is
  preserved untouched as `streamlit-app-legacy.py`.)

Feasibility is the point: a student can read every line of `demo.py` in one
sitting, then swap one rule-based agent for an LLM call in later sessions —
the extension list in Section 10 shows exactly how.

---

## Interdisciplinary team roles and division of labor

| Role | Owns in this demo | Concrete component |
|---|---|---|
| **Domain researcher** | Clinical realism of the triage rules and care content | `CONDITION_PLAYBOOKS` (diabetes, hypertension, CKD steps), risk-factor weights and HIGH/MEDIUM/LOW thresholds, follow-up cadences (7-day / 30-day), "not medical advice" guardrail wording |
| **Agent engineer** | The five-agent pipeline and its contracts | `auth_agent`, `triage_agent`, `channel_agent`, `care_plan_agent`, `message_agent`, the `run_agentic_flow` orchestrator, the HIGH-risk urgency-override rule |
| **Data engineer** | Patient fixtures and deterministic data flow | `mock_patients.json` schema (email, conditions, risk factors, preferences, last visit), `load_patients`, the fixed `DEMO_TODAY` determinism contract |
| **UX / storyteller** | The before/after narrative and the stage demo | Act 1/2/3 speaker notes, the blast-vs-personalized comparison, the localhost web UI (`app.py`, stdlib-only), screenshot placeholders |
| **QA** | Reliability gate and edge-case coverage | `TEST-LOG.md` 10/10 byte-identical gate, interactive-mode failure paths (unknown login → exit 1, unknown condition → fallback), per-channel rendering checks |

---

## Limitations, risks, and responsible AI (ethics, privacy, security, safety)

- **Not medical advice.** Condition playbooks are simplified teaching
  examples. The demo says this explicitly, and a real deployment would
  require clinician-authored content and regulatory review.
- **Fictional data only.** All patients are fictional; all data is local.
  No real PHI is touched — which is also the design lesson: the pipeline
  never needs real data to teach the pattern.
- **Simplified triage.** The 0–100 score is a teaching heuristic, not a
  validated risk model. Real triage needs validated models, calibration,
  and bias testing across populations.
- **Channel realism.** The demo assumes the preference on file is current;
  real systems must handle opt-outs, consent, and TCPA-style messaging
  rules — none modeled here.
- **Automation bias risk.** A system that "knows" a patient's A1C invites
  over-trust. The demo models the safeguard: the output for HIGH-risk
  patients is a call script *for the care manager*, keeping a human in the
  loop where stakes are highest.

---

## Practical value, adoption path, and measurable outcomes

**Practical value.** The demo's headline is operational: the same care team,
the same data — but outreach that is risk-triaged, condition-aware, and
channel-aware instead of a blast. For a care organization, that pattern is
the difference between messages sent and patients reached.

**Adoption path** (from the demo's own "Extending it" notes):

1. Swap `triage_agent`'s rules for a real model API call — the contract
   (patient → score/tier/reasons) stays the same.
2. Add a sixth agent: a **GuardrailAgent** that scans outgoing messages for
   disallowed content before the MessageAgent renders.
3. Add more conditions to `CONDITION_PLAYBOOKS` and more patients to
   `mock_patients.json` — the pipeline picks them up automatically.
4. Production hardening: real patient data behind auth, consent-gated
   messaging, clinician review of HIGH-risk outputs, and audit logging of
   every message rendered.

**Measurable outcomes.** Today the demo measures reproducibility (TEST-LOG
10/10) and contract correctness (tiers, channels, message shapes). A pilot
would measure what matters next: message open/response rates per channel,
follow-up completion within the 7/30-day windows, and care-manager time
saved per patient touched.

---

*Built for the Agentic AI Workshop · Demo 1 of 4*
