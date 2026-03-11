#!/usr/bin/env python3
"""
Interactive Local Dashboard — Run the full pipeline from your browser.
Usage:  python3 dashboard.py
Then open: http://localhost:8080

Features:
  - Click "Analyze" to run Phase 1 → 2 → 3 (scrape, classify, pulse note)
  - View themes, pulse note, and email preview
  - Enter email and click Send to deliver via Phase 4
"""

import os
import sys
import json
import glob
import subprocess
import threading
import re
from datetime import date
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

OUTPUT_DIR = "output"
PORT = 8080
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Pipeline state (shared across requests) ────────────────────────────────
pipeline_state = {
    "running": False,
    "log": [],
    "last_status": "idle",  # idle | running | done | error
}


def _load_latest(pattern):
    files = sorted(glob.glob(os.path.join(OUTPUT_DIR, pattern)), reverse=True)
    if not files:
        return None
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f) if files[0].endswith(".json") else f.read()


def _run_pipeline():
    """Run Phase 1 → 2 → 3 in sequence, capturing output."""
    pipeline_state["running"] = True
    pipeline_state["log"] = []
    pipeline_state["last_status"] = "running"

    phases = [
        ("Phase 1: Scraping Reviews", [sys.executable, "run_phase1.py"]),
        ("Phase 2: Theme Classification", [sys.executable, "run_phase2.py"]),
        ("Phase 3: Pulse Note Generation", [sys.executable, "run_phase3.py"]),
    ]

    for label, cmd in phases:
        pipeline_state["log"].append(f"\n{'='*50}")
        pipeline_state["log"].append(f"▶ {label}")
        pipeline_state["log"].append(f"{'='*50}")

        try:
            proc = subprocess.run(
                cmd, cwd=PROJECT_DIR,
                capture_output=True, text=True, timeout=600,
            )
            pipeline_state["log"].extend(proc.stdout.strip().split("\n"))
            if proc.returncode != 0:
                pipeline_state["log"].append(f"❌ {label} FAILED (exit {proc.returncode})")
                if proc.stderr:
                    # Only take last 5 lines of stderr to keep it readable
                    err_lines = proc.stderr.strip().split("\n")[-5:]
                    pipeline_state["log"].extend(err_lines)
                pipeline_state["last_status"] = "error"
                pipeline_state["running"] = False
                return
        except subprocess.TimeoutExpired:
            pipeline_state["log"].append(f"❌ {label} TIMED OUT (10 min limit)")
            pipeline_state["last_status"] = "error"
            pipeline_state["running"] = False
            return
        except Exception as e:
            pipeline_state["log"].append(f"❌ {label} ERROR: {e}")
            pipeline_state["last_status"] = "error"
            pipeline_state["running"] = False
            return

    pipeline_state["log"].append(f"\n✅ Pipeline complete!")
    pipeline_state["last_status"] = "done"
    pipeline_state["running"] = False


def _send_email(recipient):
    """Run Phase 4 to send email."""
    try:
        proc = subprocess.run(
            [sys.executable, "run_phase4.py", "--to", recipient],
            cwd=PROJECT_DIR, capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        else:
            err = proc.stderr.strip().split("\n")[-3:]
            return False, "\n".join(err)
    except Exception as e:
        return False, str(e)


def _md_to_html(md):
    """Convert markdown to HTML with proper list handling."""
    lines = md.split('\n')
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        # Headers
        if stripped.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h2>{stripped[3:]}</h2>')
        elif stripped.startswith('### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h3>{stripped[4:]}</h3>')
        # Blockquotes
        elif stripped.startswith('> '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<blockquote>{stripped[2:]}</blockquote>')
        # List items (- or * or 1.)
        elif re.match(r'^[-*] ', stripped) or re.match(r'^\d+\.\s', stripped):
            if not in_list:
                html_lines.append('<ul style="list-style:disc;padding-left:20px">')
                in_list = True
            content = re.sub(r'^[-*]\s+', '', stripped)
            content = re.sub(r'^\d+\.\s+', '', content)
            html_lines.append(f'<li style="margin-bottom:6px">{content}</li>')
        # Empty line
        elif stripped == '':
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append('<br>')
        # Regular text
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<p>{stripped}</p>')

    if in_list:
        html_lines.append('</ul>')

    result = '\n'.join(html_lines)
    # Bold
    result = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', result)
    return result


# ─── HTML Builder ────────────────────────────────────────────────────────────

def _build_html(message=None, msg_type="info"):
    grouped = _load_latest("grouped_reviews-*.json") or _load_latest("themes.json")
    pulse_md = _load_latest("weekly_pulse-*.md")
    pulse_data = _load_latest("pulse_output-*.json")

    email_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "email_body-*.html")), reverse=True)
    email_html_raw = ""
    if email_files:
        with open(email_files[0], "r", encoding="utf-8") as f:
            email_html_raw = f.read()

    themes = []
    by_theme = {}
    total_reviews = 0
    if grouped:
        themes = grouped.get("themes", [])
        by_theme = grouped.get("by_theme", {})
        total_reviews = grouped.get("metadata", {}).get("total_reviews", 0)

    has_data = len(themes) > 0

    # ── Alert banner ──
    alert = ""
    if message:
        bg = "#065f46" if msg_type == "success" else "#7f1d1d" if msg_type == "error" else "#1e3a5f"
        border = "#10b981" if msg_type == "success" else "#ef4444" if msg_type == "error" else "#3b82f6"
        alert = f"""<div style="background:{bg};border:1px solid {border};border-radius:8px;padding:14px 20px;margin-bottom:20px;font-size:14px">{message}</div>"""

    # ── Pipeline status ──
    status = pipeline_state["last_status"]
    status_badge = {
        "idle": ("Ready", "#64748b"),
        "running": ("⏳ Running...", "#f59e0b"),
        "done": ("✅ Complete", "#10b981"),
        "error": ("❌ Error", "#ef4444"),
    }.get(status, ("—", "#64748b"))

    # ── Log output ──
    log_html = ""
    if pipeline_state["log"]:
        log_text = "\n".join(pipeline_state["log"])
        log_html = f"""
        <div style="margin-top:16px">
            <details {"open" if status in ("running","error") else ""}>
                <summary style="cursor:pointer;color:#94a3b8;font-size:13px">Pipeline Log ({len(pipeline_state['log'])} lines)</summary>
                <pre style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:16px;margin-top:8px;font-size:12px;max-height:300px;overflow-y:auto;color:#cbd5e1;white-space:pre-wrap">{log_text}</pre>
            </details>
        </div>"""

    # ── Theme cards ──
    theme_cards = ""
    if has_data:
        sorted_themes = sorted(themes, key=lambda t: by_theme.get(t["id"], {}).get("review_count", 0), reverse=True)
        colors = ["#6366f1", "#f59e0b", "#ef4444", "#10b981", "#8b5cf6"]

        for i, theme in enumerate(sorted_themes):
            tid = theme["id"]
            data = by_theme.get(tid, {})
            count = data.get("review_count", 0)
            reviews = data.get("reviews", [])
            color = colors[i % len(colors)]
            pct = round(count / total_reviews * 100) if total_reviews else 0

            rating_counts = {}
            for r in reviews:
                star = r.get("rating", 0)
                rating_counts[star] = rating_counts.get(star, 0) + 1

            rating_bars = ""
            for star in range(5, 0, -1):
                c = rating_counts.get(star, 0)
                bar_pct = round(c / count * 100) if count else 0
                rating_bars += f"""
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;font-size:13px">
                    <span style="width:55px;color:#fbbf24">{"★"*star}{"☆"*(5-star)}</span>
                    <div style="flex:1;height:8px;background:#334155;border-radius:4px;overflow:hidden">
                        <div style="height:100%;width:{bar_pct}%;background:{color};border-radius:4px"></div>
                    </div>
                    <span style="width:25px;text-align:right;color:#94a3b8;font-size:12px">{c}</span>
                </div>"""

            quotes = ""
            sample = [r for r in reviews if len(r.get("review_text", "")) > 30][:3]
            for r in sample:
                stars_str = "★" * r.get("rating", 0) + "☆" * (5 - r.get("rating", 0))
                text = r.get("review_text", "")[:180]
                if len(r.get("review_text", "")) > 180:
                    text += "…"
                quotes += f"""
                <div style="background:#0f172a;border-radius:8px;padding:10px 12px;margin-bottom:6px;border-left:3px solid #334155">
                    <span style="color:#fbbf24;font-size:11px">{stars_str}</span>
                    <span style="color:#64748b;font-size:10px;margin-left:6px">{r.get('source','')}</span>
                    <p style="font-size:12px;line-height:1.5;color:#cbd5e1;margin:5px 0 0">"{text}"</p>
                </div>"""

            theme_cards += f"""
            <div style="background:#1e293b;border-radius:12px;margin-bottom:14px;border:1px solid #334155;overflow:hidden">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;padding:18px 20px;border-left:4px solid {color};gap:12px">
                    <div>
                        <h3 style="font-size:17px;margin:0 0 4px">{theme['label']}</h3>
                        <p style="color:#94a3b8;font-size:12px;margin:0">{theme.get('description','')}</p>
                    </div>
                    <span style="background:{color};padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;color:white;white-space:nowrap">{count} · {pct}%</span>
                </div>
                <div style="padding:0 20px 18px;display:grid;grid-template-columns:220px 1fr;gap:20px">
                    <div>
                        <h4 style="font-size:12px;color:#94a3b8;margin:0 0 10px;text-transform:uppercase;letter-spacing:0.5px">Ratings</h4>
                        {rating_bars}
                    </div>
                    <div>
                        <h4 style="font-size:12px;color:#94a3b8;margin:0 0 10px;text-transform:uppercase;letter-spacing:0.5px">Sample Reviews</h4>
                        {quotes}
                    </div>
                </div>
            </div>"""
    else:
        theme_cards = """<div style="text-align:center;padding:60px;color:#64748b">
            <p style="font-size:48px;margin-bottom:12px">🔍</p>
            <p style="font-size:16px">No data yet. Click <strong>Analyze Reviews</strong> to start the pipeline.</p>
        </div>"""

    # ── Pulse note ──
    pulse_html = ""
    if pulse_md:
        pulse_html = f"""<div style="background:#1e293b;border-radius:12px;padding:28px;border:1px solid #334155;line-height:1.8">{_md_to_html(pulse_md)}</div>"""
    else:
        pulse_html = """<div style="text-align:center;padding:60px;color:#64748b">
            <p style="font-size:48px;margin-bottom:12px">📝</p>
            <p>Run the analysis first to generate the pulse note.</p></div>"""

    # ── Email preview ──
    email_subject = pulse_data.get("email_subject", "") if pulse_data else ""
    email_preview = ""
    if email_html_raw:
        safe_html = email_html_raw.replace("'", "&#39;").replace('"', "&quot;")
        email_preview = f"""
        <div style="background:#1e293b;border-radius:12px;overflow:hidden;border:1px solid #334155;margin-bottom:16px">
            <div style="padding:16px 20px;border-bottom:1px solid #334155">
                <div style="font-weight:600;font-size:14px">📧 {email_subject}</div>
            </div>
            <iframe srcdoc='{safe_html}' style="width:100%;min-height:500px;border:none;background:white" sandbox></iframe>
        </div>"""
    else:
        email_preview = """<div style="text-align:center;padding:60px;color:#64748b">
            <p style="font-size:48px;margin-bottom:12px">📧</p>
            <p>Run the analysis first to generate the email.</p></div>"""

    # ── Auto-refresh when pipeline is running ──
    auto_refresh = '<meta http-equiv="refresh" content="3">' if pipeline_state["running"] else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {auto_refresh}
    <title>INDmoney — Review Insights Dashboard</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0f172a; color:#e2e8f0; min-height:100vh; }}
        .nav {{ background:linear-gradient(135deg,#1e293b,#0f172a); border-bottom:1px solid #334155; padding:14px 28px; display:flex; justify-content:space-between; align-items:center; }}
        .nav h1 {{ font-size:20px; background:linear-gradient(135deg,#6366f1,#a855f7); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
        .container {{ max-width:1100px; margin:0 auto; padding:20px; }}
        .btn {{ padding:10px 24px; border:none; border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; transition:all 0.2s; }}
        .btn:hover {{ transform:translateY(-1px); }}
        .btn-primary {{ background:linear-gradient(135deg,#6366f1,#8b5cf6); color:white; }}
        .btn-primary:hover {{ box-shadow:0 4px 15px rgba(99,102,241,0.4); }}
        .btn-green {{ background:linear-gradient(135deg,#059669,#10b981); color:white; }}
        .btn-green:hover {{ box-shadow:0 4px 15px rgba(16,185,129,0.4); }}
        .btn:disabled {{ opacity:0.5; cursor:not-allowed; transform:none; }}
        .stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:20px; }}
        .stat {{ background:#1e293b; border-radius:10px; padding:16px; border:1px solid #334155; }}
        .stat .val {{ font-size:28px; font-weight:700; background:linear-gradient(135deg,#6366f1,#a855f7); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
        .stat .lbl {{ color:#94a3b8; font-size:12px; margin-top:2px; }}
        .tabs {{ display:flex; gap:6px; margin-bottom:20px; border-bottom:1px solid #334155; }}
        .tab {{ padding:10px 20px; cursor:pointer; border:none; background:transparent; color:#94a3b8; font-size:14px; font-weight:500; border-bottom:2px solid transparent; transition:all 0.2s; }}
        .tab:hover {{ color:#e2e8f0; }}
        .tab.active {{ color:#6366f1; border-bottom-color:#6366f1; }}
        .tc {{ display:none; }} .tc.active {{ display:block; }}
        input[type=email] {{ background:#0f172a; border:1px solid #334155; border-radius:8px; padding:10px 14px; color:#e2e8f0; font-size:14px; width:300px; outline:none; }}
        input[type=email]:focus {{ border-color:#6366f1; }}
        blockquote {{ border-left:3px solid #6366f1; padding:8px 16px; margin:8px 0; background:#0f172a; border-radius:0 8px 8px 0; font-style:italic; color:#cbd5e1; }}
        h2 {{ font-size:20px; margin:14px 0 8px; }} h3 {{ font-size:16px; margin:18px 0 8px; color:#a5b4fc; }}
        li {{ margin-left:20px; margin-bottom:5px; }}
        strong {{ color:#f1f5f9; }}
    </style>
</head>
<body>
    <nav class="nav">
        <h1>📊 INDmoney — Review Insights</h1>
        <div style="display:flex;gap:12px;align-items:center">
            <span style="background:{status_badge[1]};padding:4px 12px;border-radius:12px;font-size:12px;font-weight:600">{status_badge[0]}</span>
            <form method="POST" action="/analyze" style="margin:0">
                <button type="submit" class="btn btn-primary" {"disabled" if pipeline_state["running"] else ""}>
                    {"⏳ Analyzing..." if pipeline_state["running"] else "🔍 Analyze Reviews"}
                </button>
            </form>
        </div>
    </nav>

    <div class="container">
        {alert}

        <div class="stats">
            <div class="stat"><div class="val">{total_reviews}</div><div class="lbl">Reviews</div></div>
            <div class="stat"><div class="val">{len(themes)}</div><div class="lbl">Themes</div></div>
            <div class="stat"><div class="val">{len(pulse_md.split()) if pulse_md else '—'}</div><div class="lbl">Pulse Words</div></div>
            <div class="stat"><div class="val">{'✅' if email_html_raw else '—'}</div><div class="lbl">Email Ready</div></div>
        </div>

        {log_html}

        <div class="tabs">
            <button class="tab active" onclick="showTab('themes',this)">🏷️ Themes</button>
            <button class="tab" onclick="showTab('pulse',this)">📝 Pulse Note</button>
            <button class="tab" onclick="showTab('email',this)">📧 Email</button>
        </div>

        <div id="themes" class="tc active">{theme_cards}</div>

        <div id="pulse" class="tc">{pulse_html}</div>

        <div id="email" class="tc">
            <form method="POST" action="/send-email" style="display:flex;gap:10px;align-items:center;margin-bottom:20px;flex-wrap:wrap">
                <input type="email" name="recipient" placeholder="recipient@example.com" required value="work.rajulu@gmail.com">
                <button type="submit" class="btn btn-green" {"disabled" if not email_html_raw else ""}>📧 Send Email</button>
            </form>
            {email_preview}
        </div>
    </div>

    <script>
        function showTab(id, btn) {{
            document.querySelectorAll('.tc').forEach(e => e.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(e => e.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            btn.classList.add('active');
        }}
    </script>
</body>
</html>"""


# ─── HTTP Handler ────────────────────────────────────────────────────────────

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_build_html().encode("utf-8"))

    def do_POST(self):
        if self.path == "/analyze":
            if not pipeline_state["running"]:
                t = threading.Thread(target=_run_pipeline, daemon=True)
                t.start()
            # Redirect back to dashboard
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

        elif self.path == "/send-email":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            params = parse_qs(body)
            recipient = params.get("recipient", [""])[0]

            if recipient:
                ok, output = _send_email(recipient)
                msg = f"✅ Email sent to <strong>{recipient}</strong>!" if ok else f"❌ Failed: {output}"
                msg_type = "success" if ok else "error"
            else:
                msg = "⚠ Please enter a recipient email."
                msg_type = "error"

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(_build_html(msg, msg_type).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass


def main():
    server = HTTPServer(("localhost", PORT), DashboardHandler)
    print(f"🌐 Dashboard running at: http://localhost:{PORT}")
    print(f"   Features:")
    print(f"   • Click 'Analyze Reviews' to run Phase 1 → 2 → 3")
    print(f"   • View themes, pulse note, email preview")
    print(f"   • Enter email + click Send to deliver via Phase 4")
    print(f"   Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
