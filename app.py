#from pydoc import doc

"""
Streamlit UI entry point.

Responsibilities in this file:
- Render all exam UI screens (selector, question view, summary).
- Handle user interactions and session-state transitions.
- Delegate non-UI work to helper modules.

Non-UI modules used:
- exam_loader.py: exam metadata + PDF parsing/loading.
- image_processor.py: question image cropping/rendering.
- debug_exporter.py: optional debug QA PDF export (triggered by loader).
"""

import streamlit as st
#import fitz            # MOVED: image_processor.py / debug_exporter.py
#from PIL import Image  # MOVED: image_processor.py
#import io              # MOVED: debug_exporter.py
#import re              # MOVED: pdf_parser.py
import os
#from pdf_web import open_pdf_from_url, get_pdf_bytes  # MOVED: exam_loader.py
from answer_checker import check_answer
from session_state import _init, reset_answer, reset_exam
#from pdf_parser import find_all_questions, parse_answer_pdf
#import pdf_parser  # MOVED: exam_loader.py

from image_processor import get_question_image
from exam_loader import load_exam, EXAMS
from ima_browser import CATEGORIES, fetch_exams_for_specialty

_init()



# ... app.py UI code only ...

# Runtime flow:
# 1) Initialize session state.
# 2) Choose exam.
# 3) Load parsed questions/answers.
# 4) Render active question and process answer checks.
# 5) Show summary when user exits exam.

# ─── Debug mode: set EXAM_DEBUG=1 in VSCode terminal to enable ─────────────────
# In VSCode terminal run:  $env:EXAM_DEBUG="1" ; streamlit run app.py  (Windows)
# In VSCode terminal run:  EXAM_DEBUG=1 streamlit run app.py            (Mac/Linux)
DEBUG = os.environ.get("EXAM_DEBUG", "0") == "1"
# Export one-question-per-page answer PDF when this dedicated flag is enabled.
DEBUG_QA_PDF = os.environ.get("EXAM_DEBUG_QA_PDF", "0") == "1"

# ─── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Medical Exams", layout="centered")


HEBREW_LETTERS = ["א", "ב", "ג", "ד"]


# ─── UI ────────────────────────────────────────────────────────────────────────
st.title("🏥 Medical Exams")

# ── Exam selector ──────────────────────────────────────────────────────────────
if st.session_state.exam_key is None and st.session_state.browsing_category is None:
    st.subheader("Choose an exam:")
    cols = st.columns(3)
    for i, (key, meta) in enumerate(EXAMS.items()):
        with cols[i % 3]:
            if st.button(meta["label"], width="stretch"):
                st.session_state.exam_key = key
                st.session_state.q_index  = 0
                reset_answer()
                st.rerun()

    st.divider()
    st.subheader("Browse by specialty:")

    cat_col1, cat_col2 = st.columns(2)
    with cat_col1:
        dentistry_btn = st.button("🦷 " + CATEGORIES["dentistry"]["label"],
                                  key="cat_dentistry", use_container_width=True)
    with cat_col2:
        lung_btn = st.button("🫁 " + CATEGORIES["lung_diseases"]["label"],
                             key="cat_lung_diseases", use_container_width=True)

    # Color the category buttons: yellow for dentistry, green for lung diseases
    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"]:last-of-type
            [data-testid="column"]:nth-child(1) button {
            background-color: #FFFACD !important;
            border-color: #DAA520 !important;
        }
        div[data-testid="stHorizontalBlock"]:last-of-type
            [data-testid="column"]:nth-child(2) button {
            background-color: #90EE90 !important;
            border-color: #228B22 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if dentistry_btn:
        st.session_state.browsing_category = "dentistry"
        st.rerun()
    if lung_btn:
        st.session_state.browsing_category = "lung_diseases"
        st.rerun()
    st.stop()

# ── Category exam list page ────────────────────────────────────────────────────
if st.session_state.browsing_category is not None and st.session_state.exam_key is None:
    cat_key  = st.session_state.browsing_category
    cat_meta = CATEGORIES[cat_key]

    if st.button("← Back to home"):
        st.session_state.browsing_category = None
        st.rerun()

    st.subheader(f"Exams: {cat_meta['label']}")

    try:
        exams = fetch_exams_for_specialty(cat_meta["specialty_id"])
    except Exception as e:
        st.error(f"Failed to fetch exam list: {e}")
        st.stop()

    if not exams:
        st.warning("No exams with question + answer PDFs were found for this specialty.")
        st.stop()

    for exam in exams:
        label = f"{exam['year']} — {exam['exam_type']}"
        if st.button(label, key=f"dyn_{exam['questions_url']}", use_container_width=True):
            st.session_state.exam_key          = f"dynamic_{cat_key}"
            st.session_state.dyn_questions_url = exam["questions_url"]
            st.session_state.dyn_answers_url   = exam["answers_url"]
            st.session_state.q_index           = 0
            reset_answer()
            st.rerun()
    st.stop()

# ── Load exam data ─────────────────────────────────────────────────────────────
doc, answers, questions, qa_export_path = load_exam(
    st.session_state.exam_key,
    debug=DEBUG,
    debug_qa_pdf=DEBUG_QA_PDF,
    dyn_questions_url=st.session_state.dyn_questions_url,
    dyn_answers_url=st.session_state.dyn_answers_url,
)
total_q = len(questions)

if DEBUG_QA_PDF and qa_export_path:
    st.caption(f"Debug QA PDF written to: {qa_export_path}")

# ── Summary / exit screen ──────────────────────────────────────────────────────
if st.session_state.show_summary:
    good      = st.session_state.score_good
    bad       = st.session_state.score_bad
    attempted = good + bad
    pct       = round(100 * good / attempted) if attempted > 0 else 0

    st.subheader("📊 Exam Summary")
    st.markdown(f"**Questions attempted:** {attempted} / {total_q}")

    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Correct",  good)
    col2.metric("❌ Wrong",    bad)
    col3.metric("🎯 Score",   f"{pct}%")

    if pct >= 60:
        st.success("Well done! Keep it up 💪")
    else:
        st.warning("Keep practicing, you'll get there! 📚")

    st.divider()
    col_back, col_retry = st.columns(2)
    with col_back:
        if st.button("🏠 Back to exam list", width="stretch"):
            reset_exam()
            st.rerun()
    with col_retry:
        if st.button("🔄 Retry this exam", width="stretch"):
            key = st.session_state.exam_key
            reset_exam()
            st.session_state.exam_key = key
            st.rerun()
    st.stop()

# ── Active exam screen ─────────────────────────────────────────────────────────
q_index = st.session_state.q_index
q_info  = questions[q_index]
q_num   = q_info["q_num"]

# ── Top bar: score + exit ──────────────────────────────────────────────────────
top_left, top_mid, top_right = st.columns([2, 3, 2])
with top_left:
    good = st.session_state.score_good
    bad  = st.session_state.score_bad
    st.markdown(f"✅ **{good}** &nbsp;&nbsp; ❌ **{bad}**", unsafe_allow_html=True)
with top_mid:
    attempted = good + bad
    pct = round(100 * good / attempted) if attempted > 0 else 0
    st.markdown(
        f"<p style='text-align:center;margin-top:4px'>Score: {pct}%</p>",
        unsafe_allow_html=True,
    )
with top_right:
    if st.button("🚪 Exit exam", width="stretch"):
        st.session_state.show_summary = True
        st.rerun()

st.divider()

# ── Question image ─────────────────────────────────────────────────────────────
if DEBUG:
    same_page = [q for q in questions if q["page_idx"] == q_info["page_idx"]]
    same_page_compact = [
        {
            "q_num": q["q_num"],
            "y_start": round(q["y_start"], 1),
            "y_end": round(q["y_end"], 1),
        }
        for q in same_page
    ]
    st.info(
        (
            f"DEBUG overlay | q_num={q_num} | q_index={q_index + 1}/{total_q} | "
            f"page_idx={q_info['page_idx']} | y_start={q_info['y_start']:.1f} | y_end={q_info['y_end']:.1f}"
        )
    )
    st.caption(f"Questions detected on this page: {same_page_compact}")

img = get_question_image(doc, q_info)
st.image(img, width="stretch")

# ── Navigation ────────────────────────────────────────────────────────────────
col_prev, col_info, col_next = st.columns([1, 2, 1])
with col_prev:
    if st.button("◀ Prev", disabled=(q_index == 0)):
        st.session_state.q_index -= 1
        reset_answer()
        st.rerun()
with col_info:
    st.markdown(
        f"<p style='text-align:center;margin-top:6px'>Question {q_index+1} of {total_q}</p>",
        unsafe_allow_html=True,
    )
with col_next:
    if st.button("Next ▶", disabled=(q_index >= total_q - 1)):
        st.session_state.q_index += 1
        reset_answer()
        st.rerun()

st.divider()

# ── Answer section ────────────────────────────────────────────────────────────
st.subheader(f"Question #{q_num}")

selected = st.pills(
    "Select your answer(s):",
    options=HEBREW_LETTERS,
    selection_mode="multi",
    default=st.session_state.selected,
    key=f"pills_{q_index}",
)
st.session_state.selected = selected or []

if st.button("✔ Check Answer", type="primary"):
    if not selected:
        st.warning("Please select an answer first.")
    else:
        correct = answers.get(q_num)
        is_correct, message = check_answer(selected, correct)
        
        if is_correct is None:
            st.info(message)
        else:
            if q_index not in st.session_state.answered:
                st.session_state.answered.add(q_index)
                if is_correct:
                    st.session_state.score_good += 1
                else:
                    st.session_state.score_bad += 1
            
            st.session_state.result_msg = message
            st.session_state.result_ok = is_correct

if st.session_state.result_msg:
    if st.session_state.result_ok:
        st.success(st.session_state.result_msg)
    else:
        st.error(st.session_state.result_msg)