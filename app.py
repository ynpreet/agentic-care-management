#!/usr/bin/env python3
"""
Personalized Care Management Agent — localhost web UI (Demo 1 of 4).

STDLIB ONLY: uses http.server + subprocess + json. No Flask, no Streamlit,
no pip installs, no network access beyond localhost.

Run:
    python3 app.py
Then open in Chrome:  http://localhost:8001

Endpoints:
    GET /         -> the single-page demo UI (inline HTML/CSS/JS)
    GET /api/run  -> executes `python3 demo.py` and returns its stdout
                     as JSON: {"ok": true, "output": "..."}

This file does not change demo.py's behavior; it only runs it as a
subprocess and displays its output.
"""

import errno
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8001
DEMO_TIMEOUT_SECONDS = 120

HERE = Path(__file__).resolve().parent
DEMO_PY = HERE / "demo.py"

# ---------------------------------------------------------------------------
# Single-page UI: inline CSS/JS, zero external assets.
# ---------------------------------------------------------------------------
PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Personalized Care Management Agent &mdash; Live Demo</title>
<style>
  :root {
    --bg: #0f172a;
    --panel: #111c33;
    --panel-border: #1e2d4d;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --accent: #38bdf8;
    --accent-dark: #0369a1;
    --green: #34d399;
    --term-bg: #060b18;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }
  .wrap { max-width: 1080px; margin: 0 auto; padding: 24px 20px 60px; }
  header {
    background: linear-gradient(135deg, #0c4a6e, #1e3a8a);
    border: 1px solid var(--panel-border);
    border-radius: 14px;
    padding: 26px 28px;
    margin-bottom: 22px;
  }
  header h1 { margin: 0 0 8px; font-size: 1.65rem; }
  header h1 .badge {
    display: inline-block; vertical-align: middle;
    font-size: 0.72rem; font-weight: 700;
    background: rgba(255,255,255,.14);
    border: 1px solid rgba(255,255,255,.25);
    border-radius: 999px; padding: 3px 10px; margin-left: 10px;
    letter-spacing: .04em;
  }
  header p { margin: 0; color: #cbd5e1; max-width: 62ch; }
  .card {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 22px;
  }
  .card h2 { margin: 0 0 10px; font-size: 1.1rem; }
  .card h2 .num {
    display: inline-flex; align-items: center; justify-content: center;
    width: 26px; height: 26px; border-radius: 50%;
    background: var(--accent-dark); color: #fff;
    font-size: .85rem; margin-right: 8px;
  }
  button.run {
    display: inline-flex; align-items: center; gap: 10px;
    background: var(--accent); color: #04121f;
    border: 0; border-radius: 10px;
    font-size: 1rem; font-weight: 700;
    padding: 12px 22px; cursor: pointer;
  }
  button.run:hover { background: #7dd3fc; }
  button.run:disabled { opacity: .55; cursor: default; }
  .hint { color: var(--muted); font-size: .9rem; margin: 10px 0 0; }
  /* Terminal-like trace panel */
  .term {
    background: var(--term-bg);
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 16px 18px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: .83rem; line-height: 1.55;
    white-space: pre-wrap; word-break: break-word;
    max-height: 640px; overflow-y: auto;
    color: #cbd5e1;
  }
  .term .divider { color: #475569; }
  .term .act { color: var(--accent); font-weight: 700; }
  .term .plan {
    display: block;
    background: rgba(56, 189, 248, .08);
    border-left: 3px solid var(--accent);
    padding: 8px 12px; margin: 8px 0;
    color: #e0f2fe;
  }
  .term .plan .plan-tag {
    display: inline-block; font-weight: 800;
    background: var(--accent-dark); color: #fff;
    border-radius: 4px; padding: 0 8px; margin-right: 8px;
    font-size: .72rem; letter-spacing: .06em;
  }
  .term .step { color: var(--green); font-weight: 600; }
  .term .msg { color: #f1f5f9; }
  .term .ok-line { color: var(--green); font-weight: 700; }
  .term .err { color: #f87171; font-weight: 700; }
  .placeholder { color: #64748b; font-style: italic; }
  /* Results panel */
  #results .cols { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  @media (max-width: 760px) { #results .cols { grid-template-columns: 1fr; } }
  .patient {
    background: #0b1426; border: 1px solid var(--panel-border);
    border-radius: 10px; padding: 14px 16px;
  }
  .patient h3 { margin: 0 0 6px; font-size: 1rem; }
  .patient .tier {
    display: inline-block; font-size: .75rem; font-weight: 800;
    border-radius: 999px; padding: 2px 10px; margin-bottom: 8px;
    letter-spacing: .05em;
  }
  .tier-high { background: #7f1d1d; color: #fecaca; }
  .tier-medium { background: #78350f; color: #fde68a; }
  .tier-low { background: #064e3b; color: #a7f3d0; }
  .patient dl { margin: 0; font-size: .88rem; }
  .patient dt { color: var(--muted); float: left; width: 92px; }
  .patient dd { margin: 0 0 4px 98px; color: var(--text); }
  /* Spinner */
  .spinner {
    display: inline-block; width: 16px; height: 16px;
    border: 3px solid rgba(4,18,31,.25); border-top-color: #04121f;
    border-radius: 50%; animation: spin 0.8s linear infinite;
    vertical-align: -3px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .status { margin-top: 10px; font-size: .9rem; color: var(--muted); }
  footer { color: #64748b; font-size: .82rem; margin-top: 8px; }
</style>
</head>
<body>
<div class="wrap">

  <header>
    <h1>Personalized Care Management Agent
      <span class="badge">DEMO 1 OF 4 &middot; AGENTIC AI WORKSHOP</span></h1>
    <p>One-line story: instead of one generic health blast sent to every
    patient, five agents &mdash; Auth, Triage, Channel, Care Plan, Message
    &mdash; verify, risk-triage, and personally message each patient.</p>
  </header>

  <div class="card">
    <h2><span class="num">1</span>Run the demo</h2>
    <button class="run" id="runBtn" onclick="runDemo()">Run live demo</button>
    <p class="hint">Runs <code>python3 demo.py</code> on this machine and
    streams the agent trace below. Fully deterministic &mdash; same output
    every run.</p>
    <div class="status" id="status"></div>
  </div>

  <div class="card">
    <h2><span class="num">2</span>Agent trace</h2>
    <div class="term" id="trace">
      <span class="placeholder">Press &ldquo;Run live demo&rdquo; and the
      full agent trace will appear here.</span>
    </div>
  </div>

  <div class="card" id="results" style="display:none">
    <h2><span class="num">3</span>Results</h2>
    <div class="cols">
      <div class="patient">
        <span class="tier tier-high">HIGH RISK &middot; 75</span>
        <h3>Priya Sharma</h3>
        <dl>
          <dt>Conditions</dt><dd>Type 2 Diabetes + Hypertension</dd>
          <dt>Channel</dt><dd>Email (patient preference)</dd>
          <dt>Outcome</dt><dd>Full personalized email + 7-day follow-up CTA</dd>
        </dl>
      </div>
      <div class="patient">
        <span class="tier tier-medium">MEDIUM RISK &middot; 35</span>
        <h3>Maria Garcia</h3>
        <dl>
          <dt>Conditions</dt><dd>Type 2 Diabetes + Chronic Kidney Disease</dd>
          <dt>Channel</dt><dd>SMS (patient preference)</dd>
          <dt>Outcome</dt><dd>Short texts with the top 2 actions</dd>
        </dl>
      </div>
      <div class="patient">
        <span class="tier tier-low">LOW RISK &middot; 10</span>
        <h3>James Carter</h3>
        <dl>
          <dt>Conditions</dt><dd>Hypertension</dd>
          <dt>Channel</dt><dd>Phone (patient preference)</dd>
          <dt>Outcome</dt><dd>Call script for the care manager</dd>
        </dl>
      </div>
    </div>
    <p class="hint">Deterministic canned output &mdash; same scores, tiers
    and messages on every run. Educational demo; condition playbooks are
    simplified teaching examples, not medical advice.</p>
  </div>

  <footer>
    localhost only &middot; stdlib only (http.server) &middot; no network,
    no API keys &middot; demo output rendered from the real
    <code>demo.py</code> subprocess.
  </footer>
</div>

<script>
function esc(s) {
  return s.replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;");
}

function renderTrace(text) {
  var lines = text.split("\\n");
  var html = [];
  var inPlan = false;
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    var e = esc(line);
    if (/^[=]{10,}/.test(line)) { html.push('<span class="divider">' + e + '</span>'); inPlan = false; continue; }
    if (/^ACT \\d/.test(line))   { html.push('<span class="act">' + e + '</span>'); continue; }
    if (/^PATIENT \\d/.test(line)){ html.push('<span class="act">' + e + '</span>'); continue; }
    if (/^Story:/.test(line))    { inPlan = true;
      html.push('<span class="plan"><span class="plan-tag">PLAN</span>' + e.replace(/^Story:\\s*/, '') + '</span>');
      continue; }
    if (inPlan && line.trim() === '') { inPlan = false; html.push(e); continue; }
    if (inPlan) { html.push('<span class="plan">' + e + '</span>'); continue; }
    if (/^\\[\\w+Agent\\]/.test(line)) { html.push('<span class="step">' + e + '</span>'); continue; }
    if (/^Demo complete/.test(line)) { html.push('<span class="ok-line">' + e + '</span>'); continue; }
    if (/^Subject:|^Hi |^CALL SCRIPT/.test(line)) { html.push('<span class="msg">' + e + '</span>'); continue; }
    html.push(e);
  }
  return html.join("\\n");
}

function runDemo() {
  var btn = document.getElementById('runBtn');
  var status = document.getElementById('status');
  var trace = document.getElementById('trace');
  var results = document.getElementById('results');
  btn.disabled = true;
  results.style.display = 'none';
  status.innerHTML = '<span class="spinner"></span> Running the agent pipeline&hellip;';
  trace.innerHTML = '<span class="placeholder">Running <code>python3 demo.py</code>&hellip;</span>';
  fetch('/api/run')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.ok) {
        trace.innerHTML = renderTrace(data.output);
        results.style.display = 'block';
        status.textContent = 'Done — the demo exited 0. Trace rendered above.';
      } else {
        trace.innerHTML = '<span class="err">Demo failed: ' + esc(data.error || 'unknown error') + '</span>';
        status.textContent = 'The demo run failed — see the trace panel.';
      }
    })
    .catch(function (err) {
      trace.innerHTML = '<span class="err">Request failed: ' + esc(String(err)) + '</span>';
      status.textContent = 'Could not reach the server. Is app.py still running?';
    })
    .finally(function () { btn.disabled = false; });
}
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------
class DemoHandler(BaseHTTPRequestHandler):
    server_version = "CareDemo/1.0"

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self):
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 (http.server naming convention)
        path = self.path.split("?", 1)[0]
        if path == "/":
            self._send_html()
        elif path == "/api/run":
            self._run_demo()
        else:
            self.send_error(404, "Not found")

    def _run_demo(self):
        """Execute `python3 demo.py` as a subprocess, return its stdout."""
        try:
            proc = subprocess.run(
                ["python3", str(DEMO_PY)],
                cwd=str(HERE),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=DEMO_TIMEOUT_SECONDS,
            )
        except FileNotFoundError:
            self._send_json(
                {"ok": False, "error": "python3 not found on PATH."},
                status=500,
            )
            return
        except subprocess.TimeoutExpired:
            self._send_json(
                {"ok": False,
                 "error": f"demo.py timed out after "
                          f"{DEMO_TIMEOUT_SECONDS} seconds."},
                status=500,
            )
            return
        if proc.returncode != 0:
            self._send_json(
                {"ok": False,
                 "error": f"demo.py exited with code {proc.returncode}: "
                          f"{proc.stderr.strip()}"},
                status=500,
            )
            return
        self._send_json({"ok": True, "output": proc.stdout})

    def log_message(self, fmt, *args):  # quieter logs
        sys.stderr.write(f"[app] {self.address_string()} {fmt % args}\n")


def main():
    print(f"Personalized Care Management Agent — web UI (port {PORT})",
          flush=True)
    print("Serving demo.py output; demo itself is untouched.", flush=True)
    try:
        server = HTTPServer((HOST, PORT), DemoHandler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            print(f"\nERROR: port {PORT} is already in use.", file=sys.stderr)
            print(
                "Another instance of `python3 app.py` may already be running.\n"
                "Find its PID with `lsof -ti:8001` and stop it with "
                "`kill <PID>`, or pick a free port, then try again.",
                file=sys.stderr,
            )
            sys.exit(2)
        raise
    print()
    print("============================================================", flush=True)
    print(f"  Open in Chrome: http://localhost:{PORT}", flush=True)
    print("============================================================", flush=True)
    print("Press Ctrl-C to stop.\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
