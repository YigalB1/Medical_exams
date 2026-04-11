"""
IMA exam browser module.

Fetches the list of written exams for a given medical specialty
from https://www.ima.org.il/internship/Exams.aspx and returns
structured data ready for the Streamlit UI.
"""

import re
import requests
import streamlit as st

IMA_EXAMS_URL = "https://www.ima.org.il/internship/Exams.aspx"

# Categories exposed in the UI: key → {label (Hebrew), specialty_id in IMA dropdown}
CATEGORIES = {
    "dentistry":     {"label": "רפואת שיניים", "specialty_id": "110420"},
    "lung_diseases": {"label": "מחלות ריאה",    "specialty_id": "9"},
}


def _get_form_tokens(session: requests.Session) -> dict:
    """GET the IMA page and extract ASP.NET form tokens."""
    r = session.get(IMA_EXAMS_URL, timeout=15)
    r.raise_for_status()
    html = r.text
    vs  = re.search(r'id="__VIEWSTATE"\s+value="([^"]+)"', html).group(1)
    ev  = re.search(r'id="__EVENTVALIDATION"\s+value="([^"]+)"', html).group(1)
    vsg = re.search(r'id="__VIEWSTATEGENERATOR"\s+value="([^"]+)"', html).group(1)
    return {"vs": vs, "ev": ev, "vsg": vsg}


def _parse_rows(html: str) -> list:
    """
    Parse the IMA results table into a list of exam dicts.
    Each dict: {year, exam_type, questions_url, answers_url}
    Only exams that have both a שאלון (questions) and מפתח תשובות (answers) are included.
    """
    rows = re.findall(
        r'(?s)<div class="filter-results__tr">(.*?)(?=<div class="filter-results__tr"|</div>\s*</div>\s*</div>\s*</div>\s*</div>)',
        html,
    )
    results = []
    for row in rows:
        year_m = re.search(r'dvYear[^>]+class="[^"]+">(.*?)</span>', row)
        type_m = re.search(r'spnExam[^>]+class="[^"]+">(.*?)</span>', row)
        files  = re.findall(r'href="(https://[^"]+\.pdf)"[^>]*>(.*?)</a>', row)

        if not year_m:
            continue

        year      = year_m.group(1).strip()
        exam_type = type_m.group(1).strip() if type_m else ""

        q_url = a_url = None
        for url, label in files:
            label = label.strip()
            if "שאלון" in label:
                q_url = url
            elif "מפתח" in label and "ודרור" not in label:
                a_url = url

        if q_url and a_url:
            results.append({
                "year":          year,
                "exam_type":     exam_type,
                "questions_url": q_url,
                "answers_url":   a_url,
            })

    return results


@st.cache_data(show_spinner="Fetching exam list…", ttl=3600)
def fetch_exams_for_specialty(specialty_id: str) -> list:
    """
    Fetch all exams for `specialty_id` from the IMA website.
    Results are cached for 1 hour (ttl=3600).
    Returns a list of dicts: [{year, exam_type, questions_url, answers_url}, ...]
    """
    sess = requests.Session()
    tokens = _get_form_tokens(sess)
    data = {
        "__VIEWSTATE":          tokens["vs"],
        "__VIEWSTATEGENERATOR": tokens["vsg"],
        "__EVENTVALIDATION":    tokens["ev"],
        "__EVENTTARGET":        (
            "ctl00$ctl00$ContentPlaceHolderGeneral"
            "$ContentPlaceHolderInternship$lnkbSearch"
        ),
        "__EVENTARGUMENT": "",
        "ctl00$ctl00$ContentPlaceHolderGeneral$ContentPlaceHolderInternship$ddlSpecializations": specialty_id,
        "ctl00$ctl00$ContentPlaceHolderGeneral$ContentPlaceHolderInternship$ddlExams":           "0",
        "ctl00$ctl00$ContentPlaceHolderGeneral$ContentPlaceHolderInternship$ddlFromYear":        "2017",
        "ctl00$ctl00$ContentPlaceHolderGeneral$ContentPlaceHolderInternship$ddlToYear":          "2025",
    }
    r = sess.post(
        IMA_EXAMS_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    r.raise_for_status()
    return _parse_rows(r.text)
