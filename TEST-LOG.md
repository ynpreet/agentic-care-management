# Test Log — 10x Reliability Gate

Date: 2026-10-10 (coordinator verification, independent of builder's own tests)
Machine: Linux VM, Python 3.12.3, stdlib only

## Result: 10/10 PASSED, byte-identical output on every run

Method: `python3 demo.py` executed 10 consecutive times; each run's stdout
was hashed (SHA-256). All 10 runs exited 0; all 10 hashes matched (1 unique
hash), confirming the demo is fully deterministic and stage-safe.

- Run 1: exit 0
- Run 2: exit 0
- Run 3: exit 0
- Run 4: exit 0
- Run 5: exit 0
- Run 6: exit 0
- Run 7: exit 0
- Run 8: exit 0
- Run 9: exit 0
- Run 10: exit 0

The demo requires no network, no API keys, and no pip installs.

---

# Web UI test log

Date: 2026-10-10 (web-UI verification, after the 10x CLI gate above)
Machine: Linux VM, Python 3.12.3, stdlib only
Target: `app.py` — stdlib-only `http.server` web UI on port 8001
  (`GET /` serves the page; `GET /api/run` runs `python3 demo.py` as a
  subprocess and returns its stdout as JSON `{"ok": true, "output": "..."}`)

Method (12 consecutive rounds): each round (a) ran `python3 demo.py` and
required exit 0; (b) started `python3 app.py` in the background on port
8001, asserted `curl http://localhost:8001/` -> HTTP 200, asserted
`curl http://localhost:8001/api/run` -> HTTP 200 with valid JSON
(`ok: true`, `output` a string >1000 chars) containing three stable
markers read from demo.py's output — `"ACT 2 — THE AGENTIC ERA"`,
`"[AuthAgent]"`, and `"Demo complete"` — then killed the server by PID.
Servers were killed by PID (`$!`), never `pkill -f`, after one round of
testing confirmed `pkill -f 'python3 app.py'` matches the wrapper shell's
own command line and kills the tester itself.

## Result: 12/12 PASSED, 0 failures — no flakiness, no fixes needed

- Round 1–12: PASS (demo.py exit 0; `/` = 200; `/api/run` = 200 with all 3 markers)

Also verified separately (not part of the 12 rounds):
- Startup banner prints `Open in Chrome: http://localhost:8001` (flushed immediately).
- Port-in-use: a second `python3 app.py` while one is running prints
  `ERROR: port 8001 is already in use.` with remediation steps and exits 2.
- The served page is a single HTML file with inline CSS/JS and zero
  external assets; the "Run live demo" button shows a spinner, then renders
  the agent trace in a terminal-like panel with the Story/PLAN section
  highlighted, followed by a results panel.
- The pre-existing Streamlit UI was preserved untouched as
  `streamlit-app-legacy.py`; `app.py` is now the stdlib web UI.
- `demo.py` was not modified in any way (behavior and output identical).
