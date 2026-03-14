"""
Phase 5 — Streamlit Web UI
A browser-based dashboard to trigger the pipeline, view results, and send emails.
Matches the localhost dashboard design: dark theme, 3 tabs, same features.

Run:  streamlit run phase5_ui/app.py
"""

import os
import sys
import json
import glob
import subprocess
import threading
import streamlit as st
from datetime import date

# ─── Config ──────────────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
COLORS = ["#6366f1", "#f59e0b", "#ef4444", "#10b981", "#8b5cf6"]


# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="INDmoney — Review Insights",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─── Custom CSS (Responsive Theme) ───────────────────────────────────────────
st.markdown("""
<style>
    /* Use Streamlit native CSS variables for Light/Dark mode support */
    
    /* Stat cards */
    .stat-card {
        background: var(--secondary-background-color); border-radius: 12px; padding: 20px;
        border: 1px solid rgba(128, 128, 128, 0.2); text-align: center;
    }
    .stat-val {
        font-size: 32px; font-weight: 700;
        background: linear-gradient(135deg, #6366f1, #a855f7);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .stat-lbl { color: var(--faded-text-color); font-size: 13px; margin-top: 2px; }

    /* Theme cards */
    .theme-card {
        background: var(--secondary-background-color); border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2); overflow: hidden; margin-bottom: 14px;
    }
    .theme-header {
        display: flex; justify-content: space-between; align-items: flex-start;
        padding: 18px 20px; gap: 12px;
    }
    .theme-label { font-size: 17px; font-weight: 600; color: var(--text-color); margin: 0 0 4px; }
    .theme-desc { color: var(--faded-text-color); font-size: 12px; margin: 0; }
    .theme-badge {
        padding: 5px 14px; border-radius: 20px; font-size: 12px;
        font-weight: 600; color: white; white-space: nowrap;
    }
    .theme-body {
        padding: 0 20px 18px; display: grid;
        grid-template-columns: 220px 1fr; gap: 20px;
    }
    .section-title {
        font-size: 12px; color: var(--faded-text-color); margin: 0 0 10px;
        text-transform: uppercase; letter-spacing: 0.5px;
    }

    /* Rating bars */
    .rating-row { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; font-size: 13px; }
    .star-label { width: 55px; color: #fbbf24; }
    .bar-bg { flex: 1; height: 8px; background: rgba(128, 128, 128, 0.2); border-radius: 4px; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 4px; }
    .bar-count { width: 25px; text-align: right; color: var(--faded-text-color); font-size: 12px; }

    /* Quote cards */
    .quote-card {
        background: var(--background-color); border-radius: 8px; padding: 10px 12px;
        margin-bottom: 6px; border-left: 3px solid rgba(128, 128, 128, 0.3);
    }
    .quote-stars { color: #fbbf24; font-size: 11px; }
    .quote-source { color: var(--faded-text-color); font-size: 10px; margin-left: 6px; }
    .quote-text { font-size: 12px; line-height: 1.5; color: var(--text-color); margin: 5px 0 0; }

    /* Pulse note */
    .pulse-container {
        background: var(--secondary-background-color); border-radius: 12px; padding: 28px;
        border: 1px solid rgba(128, 128, 128, 0.2); line-height: 1.8; color: var(--text-color);
    }
    .pulse-container h2 { font-size: 20px; margin: 14px 0 8px; color: var(--text-color); }
    .pulse-container h3 { font-size: 16px; margin: 18px 0 8px; color: #6366f1; }
    .pulse-container strong { font-weight: 700; }
    .pulse-container li { margin-left: 20px; margin-bottom: 5px; }
    .pulse-container blockquote {
        border-left: 3px solid #6366f1; padding: 8px 16px; margin: 8px 0;
        background: var(--background-color); border-radius: 0 8px 8px 0;
        font-style: italic; color: var(--faded-text-color);
    }

    /* Email preview */
    .email-frame {
        background: var(--secondary-background-color); border-radius: 12px; overflow: hidden;
        border: 1px solid rgba(128, 128, 128, 0.2); margin-bottom: 16px;
    }
    .email-bar {
        padding: 16px 20px; border-bottom: 1px solid rgba(128, 128, 128, 0.2);
    }
    .email-subject { font-weight: 600; font-size: 14px; color: var(--text-color); }

    /* Log area */
    .log-area {
        background: var(--background-color); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px;
        padding: 16px; font-size: 12px; max-height: 300px; overflow-y: auto;
        color: var(--text-color); white-space: pre-wrap; font-family: monospace;
    }

    /* Empty state */
    .empty-state { text-align: center; padding: 60px; color: var(--faded-text-color); }
    .empty-icon { font-size: 48px; margin-bottom: 12px; }

    /* Tabs override */
    .stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid rgba(128, 128, 128, 0.2); }
    .stTabs [data-baseweb="tab"] {
        background: transparent; color: var(--faded-text-color); font-weight: 500;
        border-bottom: 2px solid transparent; padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { color: #6366f1 !important; border-bottom-color: #6366f1 !important; }

    /* Button overrides */
    .stButton > button {
        border: none; border-radius: 8px; font-weight: 600;
        transition: all 0.2s; padding: 10px 24px;
    }
    .stButton > button:hover { transform: translateY(-1px); }

    /* Hide default streamlit elements */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }

    /* Responsive theme body */
    @media (max-width: 768px) {
        .theme-body { grid-template-columns: 1fr !important; }
    }

    /* Make tabs bold */
    button[data-baseweb="tab"] {
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)


# ─── Data Loading ────────────────────────────────────────────────────────────

def load_latest(pattern):
    """Load the most recent file matching the glob pattern."""
    files = sorted(glob.glob(os.path.join(OUTPUT_DIR, pattern)), reverse=True)
    if not files:
        return None
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f) if files[0].endswith(".json") else f.read()


# ─── Pipeline Runner ────────────────────────────────────────────────────────

def run_pipeline():
    """Run Phase 1 → 2 → 3 in sequence, updating session state."""
    st.session_state.pipeline_running = True
    st.session_state.pipeline_log = []
    st.session_state.pipeline_status = "running"

    phases = [
        ("Phase 1: Scraping Reviews", [sys.executable, os.path.join(PROJECT_DIR, "run_phase1.py")]),
        ("Phase 2: Theme Classification", [sys.executable, os.path.join(PROJECT_DIR, "run_phase2.py")]),
        ("Phase 3: Pulse Note Generation", [sys.executable, os.path.join(PROJECT_DIR, "run_phase3.py")]),
    ]

    for label, cmd in phases:
        st.session_state.pipeline_log.append(f"\n{'='*50}")
        st.session_state.pipeline_log.append(f"▶ {label}")
        st.session_state.pipeline_log.append(f"{'='*50}")

        try:
            proc = subprocess.run(
                cmd, cwd=PROJECT_DIR,
                capture_output=True, text=True, timeout=600,
            )
            st.session_state.pipeline_log.extend(proc.stdout.strip().split("\n"))
            if proc.returncode != 0:
                st.session_state.pipeline_log.append(f"❌ {label} FAILED (exit {proc.returncode})")
                if proc.stderr:
                    err_lines = proc.stderr.strip().split("\n")[-5:]
                    st.session_state.pipeline_log.extend(err_lines)
                st.session_state.pipeline_status = "error"
                st.session_state.pipeline_running = False
                return
        except subprocess.TimeoutExpired:
            st.session_state.pipeline_log.append(f"❌ {label} TIMED OUT (10 min limit)")
            st.session_state.pipeline_status = "error"
            st.session_state.pipeline_running = False
            return
        except Exception as e:
            st.session_state.pipeline_log.append(f"❌ {label} ERROR: {e}")
            st.session_state.pipeline_status = "error"
            st.session_state.pipeline_running = False
            return

    st.session_state.pipeline_log.append("\n✅ Pipeline complete!")
    st.session_state.pipeline_status = "done"
    st.session_state.pipeline_running = False


def send_email(recipient):
    """Run Phase 4 to send email."""
    try:
        proc = subprocess.run(
            [sys.executable, os.path.join(PROJECT_DIR, "run_phase4.py"), "--to", recipient],
            cwd=PROJECT_DIR, capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        else:
            err = proc.stderr.strip().split("\n")[-3:]
            return False, "\n".join(err)
    except Exception as e:
        return False, str(e)


# ─── Session State Init ─────────────────────────────────────────────────────

if "pipeline_running" not in st.session_state:
    st.session_state.pipeline_running = False
if "pipeline_log" not in st.session_state:
    st.session_state.pipeline_log = []
if "pipeline_status" not in st.session_state:
    st.session_state.pipeline_status = "idle"


# ─── Header ─────────────────────────────────────────────────────────────────

col_title, col_action = st.columns([3, 1])
with col_title:
    st.markdown('<h1 style="margin:0; padding:0; font-size:42px; font-weight:800; background:linear-gradient(90deg, #fbbf24, #ef4444); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">INDmoney — Review Insights</h1>', unsafe_allow_html=True)
    st.caption(f"{date.today().strftime('%d %b %Y')}")

with col_action:
    status = st.session_state.pipeline_status
    status_map = {
        "idle": ("🔵 Ready", "secondary"),
        "running": ("⏳ Running...", "secondary"),
        "done": ("✅ Complete", "secondary"),
        "error": ("❌ Error", "secondary"),
    }
    badge_text, _ = status_map.get(status, ("—", "secondary"))
    st.caption(badge_text)

    if st.button(
        "⏳ Analyzing..." if st.session_state.pipeline_running else "🔍 Analyze Reviews",
        type="primary",
        disabled=st.session_state.pipeline_running,
        use_container_width=True,
    ):
        with st.spinner("Running pipeline... Phase 2 takes ~5 min due to rate limits."):
            run_pipeline()
        st.rerun()


# ─── Load Data ───────────────────────────────────────────────────────────────

grouped = load_latest("grouped_reviews-*.json") or load_latest("themes.json")
pulse_md = load_latest("weekly_pulse-*.md")
pulse_data = load_latest("pulse_output-*.json")
email_html_raw = None
email_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "email_body-*.html")), reverse=True)
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


# ─── Stats Row ───────────────────────────────────────────────────────────────

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="stat-card"><div class="stat-val">{total_reviews}</div><div class="stat-lbl">Reviews</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-card"><div class="stat-val">{len(themes)}</div><div class="stat-lbl">Themes</div></div>', unsafe_allow_html=True)
with c3:
    words = len(pulse_md.split()) if pulse_md else "—"
    st.markdown(f'<div class="stat-card"><div class="stat-val">{words}</div><div class="stat-lbl">Pulse Words</div></div>', unsafe_allow_html=True)
with c4:
    email_ready = "✅" if email_html_raw else "—"
    st.markdown(f'<div class="stat-card"><div class="stat-val">{email_ready}</div><div class="stat-lbl">Email Ready</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Pipeline Log ────────────────────────────────────────────────────────────

if st.session_state.pipeline_log:
    with st.expander(f"📋 Pipeline Log ({len(st.session_state.pipeline_log)} lines)", expanded=(status in ("running", "error"))):
        log_text = "\n".join(st.session_state.pipeline_log)
        st.markdown(f'<div class="log-area">{log_text}</div>', unsafe_allow_html=True)


# ─── Tabs ────────────────────────────────────────────────────────────────────

tab_themes, tab_pulse, tab_email = st.tabs(["🏷️ Themes", "📝 Pulse Note", "📧 Email"])


# ── Tab 1: Themes ────────────────────────────────────────────────────────────

with tab_themes:
    if has_data:
        sorted_themes = sorted(
            themes,
            key=lambda t: by_theme.get(t["id"], {}).get("review_count", 0),
            reverse=True,
        )

        for i, theme in enumerate(sorted_themes):
            tid = theme["id"]
            data = by_theme.get(tid, {})
            count = data.get("review_count", 0)
            reviews = data.get("reviews", [])
            color = COLORS[i % len(COLORS)]
            pct = round(count / total_reviews * 100) if total_reviews else 0

            # Rating counts
            rating_counts = {}
            for r in reviews:
                star = r.get("rating", 0)
                rating_counts[star] = rating_counts.get(star, 0) + 1

            # Build rating bars HTML (inline styles for iframe rendering)
            rating_bars = ""
            for star in range(5, 0, -1):
                c = rating_counts.get(star, 0)
                bar_pct = round(c / count * 100) if count else 0
                stars_display = "★" * star + "☆" * (5 - star)
                rating_bars += f"""
<div class="rating-row">
    <span class="star-label">{stars_display}</span>
    <div class="bar-bg"><div class="bar-fill" style="width:{bar_pct}%;background:{color}"></div></div>
    <span class="bar-count">{c}</span>
</div>"""

            # Sample quotes HTML (inline styles for iframe rendering)
            quotes = ""
            
            # Filter for meaningful reviews
            valid_reviews = [r for r in reviews if len(r.get("review_text", "")) > 30]
            
            # Try to get a mix of sources
            app_store_reviews = [r for r in valid_reviews if r.get("source") == "App Store"]
            play_store_reviews = [r for r in valid_reviews if r.get("source") != "App Store"]
            
            sample = []
            if app_store_reviews and play_store_reviews:
                # 1 from App Store, 2 from Play Store (or vice versa depending on what's available)
                sample.append(app_store_reviews[0])
                sample.extend(play_store_reviews[:2])
                if len(sample) < 3 and len(app_store_reviews) > 1:
                    sample.append(app_store_reviews[1])
            else:
                sample = valid_reviews[:3]
                
            for r in sample[:3]:
                stars_str = "★" * r.get("rating", 0) + "☆" * (5 - r.get("rating", 0))
                text = r.get("review_text", "")[:180]
                if len(r.get("review_text", "")) > 180:
                    text += "…"
                
                source = r.get('source', 'Play Store')
                source_icon = "🍏" if source == "App Store" else "▶️"
                
                quotes += f"""
<div class="quote-card">
    <span class="quote-stars">{stars_str}</span>
    <span class="quote-source">{source_icon} {source}</span>
    <p class="quote-text">"{text}"</p>
</div>"""

            # Render theme card using st.markdown to inherit Streamlit CSS variables
            card_html = f"""
<div class="theme-card">
    <div class="theme-header" style="border-left:4px solid {color}">
        <div>
            <p class="theme-label">{theme['label']}</p>
            <p class="theme-desc">{theme.get('description', '')}</p>
        </div>
        <span class="theme-badge" style="background:{color}">{count} · {pct}%</span>
    </div>
    <div class="theme-body">
        <div>
            <p class="section-title">Ratings</p>
            {rating_bars}
        </div>
        <div>
            <p class="section-title">Sample Reviews</p>
            {quotes}
        </div>
    </div>
</div>
"""
            st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.markdown("""
<div class="empty-state">
    <div class="empty-icon">🔍</div>
    <p>No data yet. Click <strong>Analyze Reviews</strong> to start the pipeline.</p>
</div>
""", unsafe_allow_html=True)


# ── Tab 2: Pulse Note ────────────────────────────────────────────────────────

with tab_pulse:
    if pulse_md:
        import re as _re
        # Convert markdown to HTML with proper line-by-line rendering
        lines = pulse_md.split('\n')
        html_parts = []
        in_list = False
        for line in lines:
            s = line.strip()
            if s.startswith('## '):
                text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s[3:])
                if "Weekly Review Pulse" in text:
                    # Special case for the main title: don't render it in the markdown block
                    # Instead we will render it using Streamlit columns ABOVE the markdown block
                    in_list = False
                else:
                    if in_list: html_parts.append('</ul>'); in_list = False
                    html_parts.append(f'<h2>{text}</h2>')
            elif s.startswith('### '):
                if in_list: html_parts.append('</ul>'); in_list = False
                text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s[4:])
                html_parts.append(f'<h3>{text}</h3>')
            elif s.startswith('> '):
                if in_list: html_parts.append('</ul>'); in_list = False
                text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s[2:])
                html_parts.append(f'<blockquote style="border-left:3px solid #ef4444;padding:8px 16px;margin:8px 0;background:var(--background-color);border-radius:0 8px 8px 0;font-style:italic;color:#ef4444">{text}</blockquote>')
            elif _re.match(r'^[-*] ', s):
                if not in_list: html_parts.append('<ul style="list-style:disc;padding-left:20px">'); in_list = True
                content = _re.sub(r'^[-*]\s+', '', s)
                content = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
                html_parts.append(f'<li style="margin-bottom:6px">{content}</li>')
            elif _re.match(r'^\d+\.\s', s):
                if not in_list: html_parts.append('<ol style="padding-left:20px">'); in_list = True
                content = _re.sub(r'^\d+\.\s+', '', s)
                content = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
                html_parts.append(f'<li style="margin-bottom:6px">{content}</li>')
            elif s.startswith('**') and s.endswith('**'):
                if in_list: html_parts.append('</ul>'); in_list = False
                text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
                html_parts.append(f'<p>{text}</p>')
            elif s == '':
                if in_list: html_parts.append('</ul>' if not any('ol' in p for p in html_parts[-5:]) else '</ol>'); in_list = False
            else:
                if in_list: html_parts.append('</ul>'); in_list = False
                text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
                html_parts.append(f'<p>{text}</p>')
        if in_list: html_parts.append('</ul>')
        pulse_html_content = '\n'.join(html_parts)
        
        # Render the Header and Download Button side-by-side
        head_col, btn_col = st.columns([4, 1.2], vertical_alignment="bottom")
        with head_col:
            st.markdown("<h2 style='margin-bottom:0px; padding-bottom:0px;'>📊 INDmoney — Weekly Review Pulse</h2>", unsafe_allow_html=True)
        with btn_col:
            st.download_button(
                label="📁 Download (.md)",
                data=pulse_md,
                file_name=f"weekly_pulse-{date.today().strftime('%Y-%m-%d')}.md",
                mime="text/markdown",
                use_container_width=True
            )
            
        # Render the rest of the generated pulse note HTML
        st.markdown(f'<div class="pulse-container" style="margin-top:10px;">{pulse_html_content}</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
<div class="empty-state">
    <div class="empty-icon">📝</div>
    <p>Run the analysis first to generate the pulse note.</p>
</div>
""", unsafe_allow_html=True)


# ── Tab 3: Email ─────────────────────────────────────────────────────────────

with tab_email:
    email_subject = pulse_data.get("email_subject", "") if pulse_data else ""

    # Send form
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        recipient = st.text_input(
            "Recipient Email",
            value="work.rajulu@gmail.com",
            label_visibility="collapsed",
            placeholder="recipient@example.com",
        )
    with col_btn:
        send_disabled = not email_html_raw
        if st.button("📧 Send Email", type="primary", disabled=send_disabled, use_container_width=True):
            if recipient:
                with st.spinner("Sending email..."):
                    ok, output = send_email(recipient)
                if ok:
                    st.success(f"✅ Email sent to **{recipient}**!")
                else:
                    st.error(f"❌ Failed: {output}")
            else:
                st.warning("Please enter a recipient email.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Email preview
    if email_html_raw:
        st.markdown(f"""
<div class="email-frame">
    <div class="email-bar">
        <div class="email-subject">📧 {email_subject}</div>
    </div>
</div>
""", unsafe_allow_html=True)

        # Force realistic email styling (white centered paper)
        import re as _re
        inner_html = _re.sub(r'</?(html|head|body|title|meta)[^>]*>', '', email_html_raw, flags=_re.IGNORECASE)
        display_html = f"""
        <html>
        <body style="margin:0; padding:20px; background-color:transparent; display:flex; justify-content:center;">
            <div style="background-color:#ffffff; padding:40px; border-radius:8px; width:100%; max-width:650px; box-shadow:0 10px 15px -3px rgba(0,0,0,0.1); color:#333333; font-family:Arial,sans-serif; line-height:1.6;">
                {inner_html}
            </div>
        </body>
        </html>
        """

        st.components.v1.html(display_html, height=750, scrolling=True)
    else:
        st.markdown("""
<div class="empty-state">
    <div class="empty-icon">📧</div>
    <p>Run the analysis first to generate the email.</p>
</div>
""", unsafe_allow_html=True)
