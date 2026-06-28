# Medical Exams App - User Guide

## 1) What this app does
This app lets users practice medical board-style exams in Streamlit.

Main capabilities:
- Browse exams by specialty (currently Dentistry and Lung Diseases).
- Open exam question PDFs and answer-key PDFs from IMA links.
- Show one question at a time as an image.
- Check user answers and track score.
- Tag each question with attributes.
- Optionally log activity and attributes to Google Sheets.

## 2) High-level data flow
The app combines data from several sources:

1. IMA website exam catalog
- Source: https://www.ima.org.il/internship/Exams.aspx
- Module: ima_browser.py
- Purpose: fetch exam list (year, type, question PDF URL, answer PDF URL) by specialty.

2. Exam and answer PDFs
- Question PDF + answer PDF URLs are loaded at runtime.
- Modules: exam_loader.py, pdf_web.py, pdf_parser.py
- Purpose: parse questions and answer key from PDFs.

3. Optional Google Sheets logging
- Module: google_sheets_logger.py
- Purpose: store exam sessions, question answers, and question attributes.
- Worksheet tabs used:
  - exam_sessions
  - question_answers
  - question_attributes

4. Session state in Streamlit
- Module: session_state.py
- Purpose: keep active exam, question index, score, selected attributes, and filter state.

## 3) Attribute model
### Lung Diseases attribute list
Current predefined list:
- COPD
- Asthma
- Sleep medicine
- Infectious disease
- Pulmonary HTN
- Transplantation
- ILD
- Interventional pulmonology
- Oncology
- NIV, ICU
- Lung function testing
- others

### Attribute behavior rules
- If a question has no selected attribute, it is automatically set to others.
- If any other attribute is selected, others is automatically removed.
- Selected attributes can be saved to Google Sheets (if Sheets is configured).

## 4) Run locally (laptop)
### Prerequisites
- Python 3.12 recommended.
- Internet access (IMA URLs and PDF downloads).

### Steps
1. Open terminal in project folder.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run app:

```bash
streamlit run app.py
```

5. Open the local URL shown by Streamlit (usually http://localhost:8501).

### Optional: set visible app version locally
You can override the on-screen version label:

```bash
# Windows PowerShell
$env:APP_VERSION="local-test-1"; streamlit run app.py
```

## 5) Run on web (Streamlit Community Cloud)
### Deploy
1. Push your code to GitHub.
2. In Streamlit Community Cloud, create app from the target branch.
3. Set main file path to app.py.
4. Deploy.

### Secrets (for Google Sheets)
Add secrets in Streamlit Cloud app settings. Use service account credentials JSON values.

Recommended structure:

```toml
[google_sheets]
sheets_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"

[google_sheets.google_sheets]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = """-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
"""
client_email = "...@...iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Important:
- client_email must be the service account email (not personal Gmail).
- private_key must be the full key from the downloaded JSON file.
- Share your target Google Sheet with the service account email as Editor.

## 6) Operational checks after deploy
After each deployment:
1. Confirm version label on homepage.
2. Confirm homepage shows Browse by specialty.
3. Open a Lung exam question and verify attributes are shown.
4. Confirm others behavior:
  - No selection -> others is selected.
  - Selecting another tag removes others.
5. If Google Sheets is enabled, verify no auth warning appears.

## 7) Common issues and fixes
1. Google Sheets auth failed
- Usually malformed or partial private_key in secrets.
- Re-copy full JSON credentials and reboot app.

2. Cloud app shows old behavior
- App may be deployed from a different branch.
- Redeploy correct branch or merge changes into tracked branch.

3. No attributes shown
- Verify exam key/specialty resolution in runtime debug panel.
- Confirm latest deployed version is running.

## 8) Key project files
- app.py: main Streamlit UI and exam flow.
- exam_loader.py: loads and parses exam PDFs.
- ima_browser.py: fetches specialty exam list from IMA.
- google_sheets_logger.py: Google Sheets auth and logging.
- session_state.py: app state defaults and reset behavior.
- requirements.txt: Python dependencies.
- GOOGLE_SHEETS_SETUP.md: setup reference for Sheets logging.
