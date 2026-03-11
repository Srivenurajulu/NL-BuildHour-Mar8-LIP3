# INDmoney — Weekly App Review Insights

Automated pipeline that scrapes app reviews, discovers themes via AI, generates a weekly pulse note, and emails it to your team — all from a **Streamlit Web UI**.

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red?logo=streamlit)
![Groq](https://img.shields.io/badge/LLM-Groq_Llama3-orange)
![Gemini](https://img.shields.io/badge/LLM-Gemini_2.5-blue?logo=google)

---

## ✨ Features

- **📱 Scrapes** 200+ reviews from Play Store & App Store
- **🧠 AI-powered** theme discovery & classification (Groq Llama 3.3 70B)
- **📊 Generates** a weekly pulse note with top themes, quotes & recommendations (Gemini 2.5 Flash)
- **📧 Emails** the pulse note to your team via Gmail SMTP
- **🖥️ Streamlit Web UI** — click a button to run the full pipeline
- **🔒 PII-free** — all personal data is scrubbed before processing

---

## 📦 Prerequisites

- **Python 3.9+**
- API keys:
  - `GROQ_API_KEY` — [Get from Groq Console](https://console.groq.com/)
  - `GEMINI_API_KEY` — [Get from Google AI Studio](https://aistudio.google.com/apikey)
- For email delivery (optional):
  - `SENDER_EMAIL` — Your Gmail address
  - `SENDER_APP_PASSWORD` — [Generate Gmail App Password](https://myaccount.google.com/apppasswords)

---

## 🔧 Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/indmoney-review-pulse.git
cd indmoney-review-pulse

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env with your API keys
cp .env.example .env
# Edit .env and add your keys
```

---

## 🚀 Quick Start — Streamlit Web UI (Recommended)

```bash
streamlit run phase5_ui/app.py
```

Open **http://localhost:8501** in your browser. From the dashboard you can:
- Click **🔍 Analyze Reviews** to run the full pipeline (Phase 1 → 2 → 3)
- View **theme cards** with rating distributions and sample quotes
- Read the **weekly pulse note** and download as `.md`
- **Send the email** directly from the UI

> ⏱ First run takes ~6 minutes (Phase 2 waits for Groq rate limits).

---

## 🖥️ CLI — Run Phases Individually

```bash
# Phase 1 — Scrape reviews (~30 seconds)
python3 run_phase1.py

# Phase 2 — Theme classification via Groq (~5 minutes)
python3 run_phase2.py

# Phase 3 — Generate pulse note via Gemini (~5 seconds)
python3 run_phase3.py

# Phase 4 — Email the pulse note
python3 run_phase4.py --to recipient@example.com
```

**Or as a single command:**
```bash
python3 run_phase1.py && python3 run_phase2.py && python3 run_phase3.py && python3 run_phase4.py --to recipient@example.com
```

---

## 🗂️ Project Structure

```
indmoney-review-pulse/
├── .env.example              # API key template
├── .gitignore
├── requirements.txt
├── README.md
├── architecture.md           # System architecture docs
│
├── phase1_scraper/           # Phase 1: Data extraction
│   └── scraper.py
├── run_phase1.py
│
├── phase2_themes/            # Phase 2: Groq theme classification
│   └── theme_generator.py
├── run_phase2.py
│
├── phase3_pulse/             # Phase 3: Gemini pulse note
│   └── pulse_generator.py
├── run_phase3.py
│
├── phase4_email/             # Phase 4: Email delivery
│   └── email_sender.py
├── run_phase4.py
│
├── phase5_ui/                # Phase 5: Streamlit Web UI
│   └── app.py
│
├── dashboard.py              # Lightweight localhost preview (no deps)
│
└── output/                   # Generated files (gitignored)
    ├── playstore_reviews.json
    ├── appstore_reviews.json
    ├── themes-YYYY-MM-DD.json
    ├── grouped_reviews-YYYY-MM-DD.json
    ├── weekly_pulse-YYYY-MM-DD.md
    ├── email_body-YYYY-MM-DD.html
    └── pulse_email-YYYY-MM-DD.eml
```

---

## 🔑 Tech Stack

| Component | Technology |
|-----------|------------|
| Play Store Scraper | `google-play-scraper` |
| App Store Scraper | Apple RSS JSON Feed |
| Theme Classification | Groq — Llama 3.3 70B |
| Pulse Note Generation | Gemini 2.5 Flash |
| Email | Gmail SMTP (`smtplib`) |
| Web UI | Streamlit |

---

## 📊 Sample Output

The pipeline generates a weekly pulse note like this:

> ## 📊 INDmoney — Weekly Review Pulse
> **Reviews Analyzed:** 300
>
> ### 🔍 Key Themes
> - **App Functionality & Features** (139 reviews) — Users value core features but want more
> - **User Interface Issues** (55 reviews) — UI changes causing confusion
> - **Transaction & Withdrawal Problems** (49 reviews) — Fund transfer delays
>
> ### 🎯 Recommended Actions
> - Prioritize clean, stable UI with user testing
> - Resolve all transaction failures and withdrawal delays
> - Overhaul customer support for faster response times

---

## 📝 License

