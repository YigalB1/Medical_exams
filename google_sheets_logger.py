"""
Google Sheets logging module.

Appends exam session and question-level results to a shared Google Sheet.
Uses service account credentials from Streamlit secrets.
"""

import gspread
import streamlit as st
from datetime import datetime
from typing import Optional


WORKSHEET_HEADERS = {
    "exam_sessions": [
        "Timestamp",
        "Username",
        "Exam Name",
        "Event",
        "Total Questions",
        "Correct",
        "Score %",
    ],
    "question_answers": [
        "Timestamp",
        "Username",
        "Exam Name",
        "Question #",
        "User Answer",
        "Correct Answer",
        "Result",
    ],
}


def _get_sheets_client():
    """
    Get authenticated Google Sheets client from Streamlit secrets.
    Expects secrets.toml to have GOOGLE_SHEETS_CREDS (JSON service account).
    """
    try:
        section = dict(st.secrets["google_sheets"])
        if "type" in section:
            creds = section
        elif isinstance(section.get("google_sheets"), dict):
            creds = dict(section["google_sheets"])
        else:
            creds = section

        # This key is app config, not part of Google service-account credentials.
        creds.pop("sheets_url", None)
        gc = gspread.service_account_from_dict(creds)
        return gc
    except Exception as e:
        st.error(f"Google Sheets auth failed: {e}")
        return None


@st.cache_resource
def get_sheet(sheet_url: str, worksheet_name: str):
    """
    Get a cached worksheet connection.
    sheet_url: URL or ID of the Google Sheet
    worksheet_name: name of tab (e.g., 'exam_sessions', 'question_answers')
    """
    try:
        gc = _get_sheets_client()
        if not gc:
            return None
        sh = gc.open_by_url(sheet_url)
        try:
            ws = sh.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # Create required tabs automatically on first use.
            ws = sh.add_worksheet(worksheet_name, 5000, 7)
            headers = WORKSHEET_HEADERS.get(worksheet_name)
            if headers:
                ws.append_row(headers)
        return ws
    except Exception as e:
        st.warning(f"Could not open worksheet '{worksheet_name}': {e}")
        return None


def log_exam_start(sheet_url: str, username: str, exam_name: str) -> Optional[datetime]:
    """
    Log exam session start.
    Returns timestamp for reference.
    """
    ws = get_sheet(sheet_url, "exam_sessions")
    if not ws:
        return None

    ts = datetime.now().isoformat()
    try:
        ws.append_row([ts, username, exam_name, "START", "", "", ""])
        return datetime.fromisoformat(ts)
    except Exception as e:
        st.warning(f"Failed to log exam start: {e}")
        return None


def log_startup_ping(sheet_url: str, username: str = "user") -> bool:
    """
    Write a simple startup row to validate Google Sheets logging connectivity.
    Row format follows exam_sessions schema with Event='STARTING'.
    """
    ws = get_sheet(sheet_url, "exam_sessions")
    if not ws:
        return False

    ts = datetime.now().isoformat()
    try:
        ws.append_row([ts, username, "APP", "STARTING", "", "", ""])
        return True
    except Exception as e:
        st.warning(f"Failed to write startup ping: {e}")
        return False


def log_question_result(
    sheet_url: str,
    username: str,
    exam_name: str,
    question_num: int,
    user_answer,
    correct_answer,
    is_correct: bool,
):
    """
    Log individual question result.
    user_answer: what user selected (can be list or string)
    correct_answer: what the answer key says (can be list or string)
    is_correct: boolean result
    """
    ws = get_sheet(sheet_url, "question_answers")
    if not ws:
        return

    ts = datetime.now().isoformat()
    user_ans_str = " + ".join(user_answer) if isinstance(user_answer, list) else str(user_answer)
    correct_ans_str = " + ".join(correct_answer) if isinstance(correct_answer, list) else str(correct_answer)
    result_str = "✓" if is_correct else "✗"

    try:
        ws.append_row([
            ts,
            username,
            exam_name,
            question_num,
            user_ans_str,
            correct_ans_str,
            result_str,
        ])
    except Exception as e:
        st.warning(f"Failed to log question {question_num}: {e}")


def log_exam_end(
    sheet_url: str,
    username: str,
    exam_name: str,
    total_questions: int,
    correct_count: int,
    incorrect_count: int,
):
    """
    Log exam session end with summary stats.
    """
    ws = get_sheet(sheet_url, "exam_sessions")
    if not ws:
        return

    ts = datetime.now().isoformat()
    score_pct = round(100 * correct_count / total_questions) if total_questions > 0 else 0

    try:
        ws.append_row([
            ts,
            username,
            exam_name,
            "END",
            total_questions,
            correct_count,
            score_pct,
        ])
    except Exception as e:
        st.warning(f"Failed to log exam end: {e}")


def setup_sheets(sheet_url: str):
    """
    Ensure the Google Sheet has the required worksheets and headers.
    Call this once during app setup or manually if sheets don't exist.
    """
    gc = _get_sheets_client()
    if not gc:
        st.error("Cannot set up sheets: Google auth failed")
        return

    try:
        sh = gc.open_by_url(sheet_url)

        # exam_sessions sheet
        try:
            ws1 = sh.worksheet("exam_sessions")
        except gspread.exceptions.WorksheetNotFound:
            ws1 = sh.add_worksheet("exam_sessions", 1000, 7)
            ws1.append_row(["Timestamp", "Username", "Exam Name", "Event", "Total Questions", "Correct", "Score %"])

        # question_answers sheet
        try:
            ws2 = sh.worksheet("question_answers")
        except gspread.exceptions.WorksheetNotFound:
            ws2 = sh.add_worksheet("question_answers", 5000, 7)
            ws2.append_row(["Timestamp", "Username", "Exam Name", "Question #", "User Answer", "Correct Answer", "Result"])

        st.success("Google Sheets logging ready!")
    except Exception as e:
        st.error(f"Setup failed: {e}")
