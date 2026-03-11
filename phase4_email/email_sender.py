"""
Phase 4 — Email Delivery
Sends the weekly pulse note to a recipient via SMTP (Gmail App Password).
Falls back to generating a .eml file if SMTP is unavailable.
"""

import os
import json
import smtplib
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

load_dotenv()


# ─── Configuration ───────────────────────────────────────────────────────────

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
OUTPUT_DIR = "output"


# ─── Email Builder ───────────────────────────────────────────────────────────

def _build_email(
    sender: str,
    recipient: str,
    subject: str,
    html_body: str,
    pulse_md_path: str = None,
) -> MIMEMultipart:
    """Build a MIME email with HTML body and optional Markdown attachment."""
    msg = MIMEMultipart("mixed")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject

    # HTML body
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)

    # Attach pulse note as .md file
    if pulse_md_path and os.path.exists(pulse_md_path):
        with open(pulse_md_path, "r", encoding="utf-8") as f:
            md_content = f.read()
        attachment = MIMEBase("text", "markdown")
        attachment.set_payload(md_content.encode("utf-8"))
        encoders.encode_base64(attachment)
        filename = os.path.basename(pulse_md_path)
        attachment.add_header("Content-Disposition", f"attachment; filename={filename}")
        msg.attach(attachment)

    return msg


# ─── SMTP Sender ─────────────────────────────────────────────────────────────

def send_email(
    recipient: str,
    subject: str,
    html_body: str,
    pulse_md_path: str = None,
    sender_email: str = None,
    sender_password: str = None,
) -> bool:
    """
    Send email via Gmail SMTP.

    Args:
        recipient: Recipient email address.
        subject: Email subject line.
        html_body: HTML email body (from Phase 3).
        pulse_md_path: Optional path to pulse note .md file to attach.
        sender_email: Gmail address. Falls back to SENDER_EMAIL env var.
        sender_password: Gmail App Password. Falls back to SENDER_APP_PASSWORD env var.

    Returns:
        True if sent successfully, False otherwise.
    """
    sender = sender_email or os.getenv("SENDER_EMAIL")
    password = sender_password or os.getenv("SENDER_APP_PASSWORD")

    if not sender or not password:
        print("[Phase 4] ⚠ SMTP credentials missing. Set SENDER_EMAIL and SENDER_APP_PASSWORD in .env")
        return False

    if sender == "your_email@gmail.com" or password == "your_app_password_here":
        print("[Phase 4] ⚠ SMTP credentials are still placeholders. Update them in .env")
        return False

    msg = _build_email(sender, recipient, subject, html_body, pulse_md_path)

    try:
        print(f"[Phase 4] Connecting to {SMTP_HOST}:{SMTP_PORT}...")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        print(f"[Phase 4] ✅ Email sent to {recipient}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("[Phase 4] ❌ Authentication failed. Check your Gmail App Password.")
        print("  → Generate one at: https://myaccount.google.com/apppasswords")
        return False
    except smtplib.SMTPException as e:
        print(f"[Phase 4] ❌ SMTP error: {e}")
        return False
    except Exception as e:
        print(f"[Phase 4] ❌ Connection error: {e}")
        return False


# ─── .eml Fallback ───────────────────────────────────────────────────────────

def save_eml(
    recipient: str,
    subject: str,
    html_body: str,
    pulse_md_path: str = None,
    output_dir: str = OUTPUT_DIR,
) -> str:
    """Save the email as a .eml file that can be opened in any email client."""
    today = date.today().strftime("%Y-%m-%d")
    sender = os.getenv("SENDER_EMAIL", "noreply@indmoney-pulse.local")

    msg = _build_email(sender, recipient, subject, html_body, pulse_md_path)

    eml_path = os.path.join(output_dir, f"pulse_email-{today}.eml")
    os.makedirs(output_dir, exist_ok=True)
    with open(eml_path, "w", encoding="utf-8") as f:
        f.write(msg.as_string())

    print(f"[Phase 4] 📎 Saved .eml file → {eml_path}")
    print(f"  (Open this file in any email client to send manually)")
    return eml_path


# ─── Public API ───────────────────────────────────────────────────────────────

def run_phase4(
    input_path: str = "output/pulse_output-{today}.json",
    recipient: str = None,
    output_dir: str = OUTPUT_DIR,
    sender_email: str = None,
    sender_password: str = None,
) -> dict:
    """
    Execute Phase 4:
      1. Load pulse output JSON from Phase 3
      2. Try sending via SMTP
      3. If SMTP fails, save as .eml fallback
    """
    today = date.today().strftime("%Y-%m-%d")

    # Resolve input path
    if "{today}" in input_path:
        input_path = input_path.replace("{today}", today)

    # 1. Load Phase 3 output
    print(f"[Phase 4] Loading pulse output from {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        pulse_data = json.load(f)

    subject = pulse_data.get("email_subject", f"INDmoney Weekly Pulse — {today}")
    html_body = pulse_data.get("email_body_html", "")
    pulse_md_path = os.path.join(output_dir, f"weekly_pulse-{today}.md")

    if not html_body:
        raise ValueError("No email_body_html found in pulse output.")

    print(f"[Phase 4] Subject: {subject}")
    print(f"[Phase 4] Recipient: {recipient or '(not set)'}")

    result = {
        "subject": subject,
        "recipient": recipient,
        "sent_via_smtp": False,
        "eml_path": None,
    }

    # 2. Try SMTP
    if recipient:
        sent = send_email(
            recipient=recipient,
            subject=subject,
            html_body=html_body,
            pulse_md_path=pulse_md_path,
            sender_email=sender_email,
            sender_password=sender_password,
        )
        result["sent_via_smtp"] = sent

    # 3. Always save .eml as backup
    eml_path = save_eml(
        recipient=recipient or "recipient@example.com",
        subject=subject,
        html_body=html_body,
        pulse_md_path=pulse_md_path,
        output_dir=output_dir,
    )
    result["eml_path"] = eml_path

    return result
