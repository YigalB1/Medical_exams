# Google Sheets Logging Setup

This app can log exam sessions and question results to a Google Sheet for tracking and analytics.

## Quick Start

### 1. Create a Google Sheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new blank spreadsheet
3. Name it "Medical Exams Log" (or whatever you prefer)
4. Copy the sheet URL from the address bar: `https://docs.google.com/spreadsheets/d/SHEET_ID/edit`

### 2. Set up Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. Enable the Google Sheets API:
   - Search for "Google Sheets API"
   - Click Enable
4. Create a Service Account:
   - Go to "Service Accounts" in the left menu
   - Click "Create Service Account"
   - Name: `streamlit-sheets`
   - Click Create and Continue
   - Grant it `Editor` role (or create custom role with Sheets permissions)
5. Create a JSON key:
   - Click the newly created service account
   - Go to Keys tab
   - Click "Add Key" → "Create new key" → JSON
   - Download the JSON file (save it safely)

### 3. Share the Google Sheet with the Service Account

1. In the JSON file, find the `client_email` value (looks like `streamlit-sheets@project.iam.gserviceaccount.com`)
2. Open your Google Sheet
3. Click Share (top right)
4. Paste the service account email
5. Grant Editor access
6. Click Share

### 4. Configure Streamlit Secrets

**For local development** (in the project root, create `.streamlit/secrets.toml`):
```toml
[google_sheets]
sheets_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"

[google_sheets.google_sheets]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key_id = "..."
private_key = "..."
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Simply paste the entire JSON service account file content under `[google_sheets.google_sheets]`.

**For Streamlit Community Cloud**:
1. Open your app settings on share.streamlit.io
2. Go to Secrets
3. Paste the same TOML as above

### 5. The App Will Auto-Create Sheets

When you run the app with SHEETS_URL configured, it will:
- Create an `exam_sessions` sheet with headers: Timestamp, Username, Exam Name, Event, Total Questions, Correct, Score %
- Create a `question_answers` sheet with headers: Timestamp, Username, Exam Name, Question #, User Answer, Correct Answer, Result

### Logging Behavior

- **Exam Start**: When a user selects an exam, a START row is logged
- **Question Results**: After each answer is checked, a row is logged with the answer and outcome
- **Exam End**: When the user views the summary, an END row is logged with the final score

### Future Features

- User registration (currently defaults to "user")
- Analytics dashboard
- Export data to CSV

### No Logging?

If logging doesn't appear in your sheet:
1. Check that secrets are correctly configured
2. Check Streamlit logs for auth errors
3. Verify service account has Editor access to the sheet
4. Verify the sheet URL is correct

