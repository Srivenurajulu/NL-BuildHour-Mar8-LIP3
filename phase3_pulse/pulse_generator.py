"""
Phase 3 — Weekly Pulse Note Generation (Powered by Gemini)
Reads the grouped themes JSON from Phase 2, sends to Gemini,
and produces a ≤250-word pulse note (Markdown) + email body (HTML).

Uses the new `google-genai` SDK (replaces deprecated `google.generativeai`).
"""

import os
import json
from datetime import datetime, date
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


# ─── Configuration ───────────────────────────────────────────────────────────

GEMINI_MODEL = "gemini-2.5-flash"
OUTPUT_DIR = "output"


# ─── Prompt ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Lead Product Manager for the fintech app "INDmoney".
You are writing a concise weekly pulse note based on categorized user reviews from the Play Store and App Store.

You will receive a JSON object with:
- "themes": array of theme definitions (id, label, description)
- "by_theme": object mapping theme IDs to their reviews

Your task is to generate TWO outputs:

---

**OUTPUT 1: Weekly Pulse Note** (Markdown, ≤ 250 words)

Structure:
## 📊 INDmoney — Weekly Review Pulse
**Period:** [use dates from the reviews]
**Reviews Analyzed:** [total number]

### 🔍 Key Themes
For each theme (ordered by review count, descending):
- **Theme Label** (N reviews) — one-line takeaway

### 💬 User Voices
Pick 3 impactful, representative quotes from different themes. Include the star rating:
> ★N: "exact quote from a review"

### 🎯 Recommended Actions
3 specific, actionable recommendations for the product team based on the themes.

---

**OUTPUT 2: Email Body** (HTML)

- Subject line (compelling, includes week reference)
- Professional HTML email with the pulse note content inline
- Clean formatting with a brief intro
- Sign off with: "Best regards, Your Friendly Informer !!"

---

Return ONLY a valid JSON object:
{
  "pulse_note": "full markdown content here",
  "email_subject": "subject line here",
  "email_body_html": "full HTML email body here"
}

Constraints:
- Use ONLY data from the provided reviews. Do NOT invent quotes or statistics.
- Zero PII — no names, emails, phone numbers.
- Keep the pulse note ≤ 250 words.
- Make it scannable with bullets and headers.
"""


def _prepare_input(grouped_data: dict) -> str:
    """Prepare a compact version of the grouped data for Gemini."""
    compact = {
        "total_reviews": grouped_data["metadata"]["total_reviews"],
        "themes": grouped_data["themes"],
        "by_theme": {},
    }

    for tid, theme_data in grouped_data["by_theme"].items():
        # Include reviews with only essential fields, trim long text
        reviews_compact = []
        for r in theme_data["reviews"]:
            reviews_compact.append({
                "sr_no": r["sr_no"],
                "rating": r["rating"],
                "text": r["review_text"][:300],
                "source": r["source"],
            })

        compact["by_theme"][tid] = {
            "label": theme_data["label"],
            "review_count": theme_data["review_count"],
            "reviews": reviews_compact,
        }

    return json.dumps(compact, ensure_ascii=False)


# ─── Gemini API Call ─────────────────────────────────────────────────────────

def generate_pulse(grouped_data: dict, api_key: str = None) -> dict:
    """
    Send grouped themes + reviews to Gemini and get back a pulse note + email body.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY not found. Set it in .env or pass it directly.")

    client = genai.Client(api_key=key)
    input_text = _prepare_input(grouped_data)

    print(f"[Phase 3] Sending {grouped_data['metadata']['total_reviews']} reviews "
          f"({len(grouped_data['themes'])} themes) to Gemini ({GEMINI_MODEL})...")

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"{SYSTEM_PROMPT}\n\nHere is the grouped review data:\n\n{input_text}",
        config=types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=8192,
            response_mime_type="application/json",
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
            ]
        ),
    )

    raw = response.text
    print(f"[Phase 3] Received response ({len(raw)} chars).")

    # Parse JSON
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[Phase 3] ❌ JSON parse failed: {e}")
        print(f"[Phase 3] Raw:\n{raw[:500]}")
        raise

    # Validate required keys
    for key_name in ("pulse_note", "email_subject", "email_body_html"):
        if key_name not in result:
            raise ValueError(f"Gemini response missing '{key_name}' key.")

    print(f"[Phase 3] ✅ Pulse note generated ({len(result['pulse_note'].split())} words)")
    print(f"[Phase 3] ✅ Email subject: {result['email_subject']}")

    return result


# ─── Public API ───────────────────────────────────────────────────────────────

def run_phase3(
    input_path: str = "output/themes.json",
    output_dir: str = OUTPUT_DIR,
    api_key: str = None,
) -> dict:
    """
    Execute the full Phase 3 pipeline:
      1. Load grouped themes JSON from Phase 2
      2. Send to Gemini for pulse note generation
      3. Save pulse note (Markdown) + email body (HTML) + full JSON
    """
    today = date.today().strftime("%Y-%m-%d")

    # 1. Load grouped data
    print(f"[Phase 3] Loading grouped themes from {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        grouped_data = json.load(f)

    themes = grouped_data.get("themes", [])
    total = grouped_data.get("metadata", {}).get("total_reviews", 0)
    print(f"[Phase 3] Loaded {len(themes)} themes, {total} reviews.")

    # 2. Generate pulse note via Gemini
    result = generate_pulse(grouped_data, api_key=api_key)

    # 3. Save outputs
    os.makedirs(output_dir, exist_ok=True)

    # Pulse note as Markdown
    pulse_path = os.path.join(output_dir, f"weekly_pulse-{today}.md")
    with open(pulse_path, "w", encoding="utf-8") as f:
        f.write(result["pulse_note"])
    print(f"[Phase 3] 📝 Saved pulse note → {pulse_path}")

    # Email body as HTML
    email_path = os.path.join(output_dir, f"email_body-{today}.html")
    with open(email_path, "w", encoding="utf-8") as f:
        f.write(result["email_body_html"])
    print(f"[Phase 3] 📧 Saved email body → {email_path}")

    # Full JSON output
    full_output = {
        "metadata": {
            "generated_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "model": GEMINI_MODEL,
            "input_file": input_path,
        },
        **result,
    }
    json_path = os.path.join(output_dir, f"pulse_output-{today}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2, ensure_ascii=False)
    print(f"[Phase 3] 📁 Saved full output → {json_path}")

    return full_output
