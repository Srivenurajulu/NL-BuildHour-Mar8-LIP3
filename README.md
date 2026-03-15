# INDmoney Review Insights & Pulse Generator

An end-to-end, AI-powered pipeline designed for Product Managers to automatically extract, analyze, and distribute insights from public app store reviews. 

This tool scrapes recent reviews from both the Google Play Store and Apple App Store, uses a Local/Cloud hybrid LLM architecture to cluster those reviews into actionable product themes, generates a comprehensive "Weekly Pulse Note", and distributes it via email. All of this is controlled through a beautiful, responsive Streamlit Web UI.

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red?logo=streamlit)
![Groq](https://img.shields.io/badge/LLM-Groq_Llama3-orange)
![Gemini](https://img.shields.io/badge/LLM-Gemini_2.5-blue?logo=google)

---

## ✨ Key Features & Implementation Details

### 1. Robust Data Pipeline (Phases 1-4)
- **Data Extraction (Phase 1):** Scrapes up to 200 of the newest, most relevant reviews. Uses `google-play-scraper` for Android and Apple's RSS JSON feed for iOS. Automatically scrubs Personally Identifiable Information (PII) to ensure data privacy before it ever hits an LLM.
- **Theme Classification (Phase 2):** Leverages **Groq (Llama 3.3 70B)** for blazing-fast inference. It analyzes verbatim review text and categorizes them into dynamic product themes (e.g., "UI/UX Friction", "Payment Gateway Failures").
- **Pulse Note Generation (Phase 3):** Uses **Google Gemini 2.5 Flash** to synthesize the categorized themes into a highly readable, Markdown-formatted "Weekly Pulse Note" tailored for executive and product team reading.
- **Automated Distribution (Phase 4):** Compiles the Markdown into responsive HTML and securely emails it to stakeholders using Gmail's SMTP relay.

### 2. Premium "Liquid Glass" Web UI (Phase 5)
The entire pipeline is wrapped in a highly polished **Streamlit Dashboard** (`phase5_ui/app.py`). 
We bypassed standard Streamlit components using custom CSS injection to create an Apple-inspired **"Glassmorphism"** aesthetic:
- **Translucency & Blur:** UI Cards use `rgba(128, 128, 128, 0.08)` backgrounds with `backdrop-filter: blur(16px)` to create a frosted glass effect that perfectly adapts to Streamlit's Light and Dark modes.
- **Micro-Interactions:** Theme cards organically float upwards (`translateY`) with enhanced drop-shadows on mouse hover.
- **Sentiment Badges:** The UI instantly parses star ratings on the fly (1-5) and injects dynamic, color-coded sentiment pills (`Positive`, `Mixed`, `Critical`) next to sample user quotes.

---

## 🚀 Quick Start (Streamlit UI)

The recommended way to use this application is through the provided web dashboard.

### Prerequisites
1. Python 3.9+ installed.
2. API Keys for **Groq** (`GROQ_API_KEY`) and **Google Gemini** (`GEMINI_API_KEY`).
3. An App Password for a Gmail account (`SENDER_EMAIL`, `SENDER_APP_PASSWORD`) if you wish to use the email feature.

### Setup
```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/indmoney-review-pulse.git
cd indmoney-review-pulse

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure Environment Variables
cp .env.example .env
# Open .env and insert your API keys and Email credentials
```

### Running the App
```bash
streamlit run phase5_ui/app.py
```
Open **http://localhost:8501** in your browser. Click the "**🔍 Analyze Reviews**" button to trigger the pipeline sequence. Please note that Phase 2 incorporates intentional rate-limit delays to comply with Groq's free-tier restrictions (taking ~5 minutes to process 200 reviews).

---

## 🖥️ CLI Execution (Headless Mode)

You can bypass the UI and run the pipeline sequence headless via the CLI. This is ideal for cron jobs or CI/CD scheduling.

```bash
# Run the entire sequence in one command
python3 run_phase1.py && \
python3 run_phase2.py && \
python3 run_phase3.py && \
python3 run_phase4.py --to your_manager@example.com
```

---

## 📊 Outputs & Artifacts

All generated data is saved locally in the `/output` directory, serving as a historical archive. The pipeline creates the following chain of artifacts during a successful run:

1. **`appstore_reviews.json` & `playstore_reviews.json`**
   - Raw, PII-scrubbed JSON dumps directly from the scrapers.
2. **`themes-YYYY-MM-DD.json`**
   - The Groq AI output mapping raw reviews to identified product themes.
3. **`grouped_reviews-YYYY-MM-DD.json`**
   - A structured aggregation showing Theme -> List[Reviews], counts, and percentage shares. This powers the UI Dashboard visualizations.
4. **`weekly_pulse-YYYY-MM-DD.md`**
   - The final Gemini AI synthesized report. Example excerpt:
   ```markdown
   ## 📊 INDmoney — Weekly Review Pulse
   **Reviews Analyzed:** 200 (Play Store: 150, App Store: 50)
   
   ### 🚨 Critical Friction Points
   * **KYC & Onboarding Delays (32%):** Users report being stuck on the video KYC confirmation screen. 
     * *"Stuck on verification for 4 days now, support isn't replying."* (★☆☆☆☆)
   ```
5. **`email_body-YYYY-MM-DD.html` & `pulse_email-YYYY-MM-DD.eml`**
   - The Markdown converted to inline-styled HTML, and the exact `.eml` payload that was dispatched via SMTP.
