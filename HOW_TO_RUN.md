# How to Run & Deploy the INDmoney Review Insights Dashboard

This guide walks you through the dependencies required for the project, how to run it locally on your machine, and how to host it publicly on Streamlit Community Cloud.

## 📦 Dependencies

The application relies on several core Python libraries to function. These should be installed via `pip`:

*   **`streamlit`**: Empowers the interactive "Liquid Glass" web UI dashboard.
*   **`google-play-scraper`**: Extracts reviews directly from the Android Play Store.
*   **`groq`**: The official SDK to connect to Groq (running Llama 3) for lightning-fast theme classification.
*   **`google-genai`**: The official SDK to connect to Google Gemini for synthesizing the final Weekly Pulse Note.
*   **`python-dotenv`**: Securely loads your API keys from a `.env` file when running locally.
*   **`pandas`**: Used for data manipulation.

*All dependencies are neatly listed in the `requirements.txt` file at the root of the project.*

---

## Section A: How to Run on Localhost

Running the application locally is the best way to develop, test, and generate insights without worrying about cloud deployments.

**Step 1: Clone the Repository**
Open your terminal and clone the code to your machine, then navigate into the folder:
```bash
git clone https://github.com/Srivenurajulu/NL-BuildHour-Mar8-LIP3.git
cd NL-BuildHour-Mar8-LIP3
```

**Step 2: Install Dependencies**
Install all required libraries listed above using `pip`:
```bash
pip install -r requirements.txt
```

**Step 3: Setup your API Keys**
The application needs API keys to talk to Groq and Gemini.
1. Duplicate the `.env.example` file and rename it to `.env`.
2. Open the new `.env` file in any text editor.
3. Paste your Groq API key (`GROQ_API_KEY`) and Google Gemini API key (`GEMINI_API_KEY`).
4. *(Optional)* If you plan to test the email feature, also add your Gmail address and Gmail App Password.

**Step 4: Launch the Web UI**
Start the Streamlit server from your terminal:
```bash
streamlit run phase5_ui/app.py
```

**Step 5: View the Dashboard**
Your terminal will output a Local URL (usually `http://localhost:8501`). Open this link in your web browser. You can now click the "Analyze Reviews" button to trigger the whole AI pipeline directly from the dashboard!

---

## Section B: How to Host on Streamlit Community Cloud

Hosting on Streamlit Community Cloud allows you to share the live dashboard securely with stakeholders or colleagues via a public URL, without them needing to install anything.

**Step 1: Push your code to GitHub**
Ensure all your latest code, including the `requirements.txt` file, is pushed to your GitHub repository (`Srivenurajulu/NL-BuildHour-Mar8-LIP3`). *Important: Make sure your `.env` file is NOT pushed to GitHub for security reasons.*

**Step 2: Create a Streamlit Account**
Go to [share.streamlit.io](https://share.streamlit.io/) and sign up or log in using your GitHub account.

**Step 3: Deploy a new app**
1. Once logged into the Streamlit dashboard, click the **"New app"** button.
2. Select **"Deploy a public app from GitHub"**.
3. Fill in the deployment details:
   *   **Repository:** `Srivenurajulu/NL-BuildHour-Mar8-LIP3`
   *   **Branch:** `main`
   *   **Main file path:** `phase5_ui/app.py`
4. Do **NOT** click Deploy just yet!

**Step 4: Add your API Keys (Secrets)**
Since you didn't upload your `.env` file, Streamlit needs your API keys through its secure Secrets manager.
1. Click on **"Advanced settings..."** (at the bottom of the deployment window).
2. Under the **"Secrets"** text box, paste your environment variables exactly as they appear in your local `.env` file:
   ```toml
   GROQ_API_KEY="your-groq-api-key"
   GEMINI_API_KEY="your-gemini-api-key"
   SENDER_EMAIL="your-email@gmail.com"
   SENDER_APP_PASSWORD="your-app-password"
   ```
3. Click **"Save"**.

**Step 5: Deploy!**
Now, click the big **"Deploy!"** button. Streamlit will spin up a server, install the dependencies from `requirements.txt`, and launch your app. 

You will be given a public URL (e.g., `https://nl-buildhour-mar8-lip3.streamlit.app`) that you can share with anyone to view your INDmoney Review Insights Dashboard!
