# RUBRIC.md — Personalized Care Management Agent (self-scorecard)

Scored against `~/workspace/peaii-hackathon/judging-rubric.md` (100 pts). Honest self-assessment; gaps and student-level fixes included.

| # | Criterion (weight) | Score | Points | Evidence |
|---|---|---|---|---|
| 1 | Problem Definition & Real-World Impact (25) | 4/5 | 20 | Specific user (care managers/coordinators doing population-health outreach) and a named "today" workflow (the generic blast email). The before/after contrast is the story. Gap: patients are fictional and simplified — no real-world validation of message effectiveness. |
| 2 | Meaningful Agentic AI Behavior (20) | 5/5 | 20 | Five-agent pipeline (Auth→Triage→Channel→CarePlan→Message) with printed plan and per-agent steps; triage changes downstream behavior (channel choice, plan content); memory of patient preferences drives channel selection. Answers "why an agent, not a chatbot": multi-step orchestration with state handoff between specialized agents. Gap: agents are deterministic policy code, not LLM reasoners. |
| 3 | Working Prototype (15) | 5/5 | 15 | `python3 demo.py` runs offline in <1s; `python3 app.py` serves a Chrome UI on :8001; TEST-LOG.md shows 10/10 byte-identical CLI runs plus 12/12 web rounds. |
| 4 | Innovation & Creativity (15) | 3/5 | 9 | The before/after narrative framing is the creative core, but personalized outreach is a well-trodden concept; the agent design itself is a straightforward pipeline. |
| 5 | Presentation & Communication (15) | 4/5 | 12 | Plain-English before/after story, timed speaker notes, browser UI with highlighted trace followable by a non-technical audience. Gap: terminal-only fallback; no visuals beyond the web UI. |
| 6 | Responsible AI & Feasibility (10) | 4/5 | 8 | README states explicitly: fictional patients, simplified condition playbooks are NOT medical advice, local data only, no network. Human oversight: care managers review plans before sending. Gap: no discussion of bias in risk triage (who gets labeled HIGH) — a student could add a fairness note on triage criteria. |
| | **TOTAL** | | **84** | |

## How a student team could close the gaps
- **Impact:** partner with a campus clinic or run a small message-clarity survey to validate the before/after difference with real readers.
- **Agentic:** swap the deterministic triage for an LLM-backed planner behind the same tool interface; keep guardrails deterministic.
- **Innovation:** add a feedback loop — track which channel/message got a response and let the agent adapt per patient over time.
- **Responsible AI:** publish the triage criteria and add a bias check (do HIGH-risk labels distribute fairly across the mock panel?).
