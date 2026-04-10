#from pydoc import doc

import streamlit as st
import fitz
from PIL import Image
import io
import re
import os
from pdf_web import open_pdf_from_url, get_pdf_bytes
from answer_checker import check_answer
from session_state import _init, reset_answer, reset_exam
#from pdf_parser import find_all_questions, parse_answer_pdf
import pdf_parser

#from image_processor import get_question_image
#from exam_loader import load_exam

_init()



# ... app.py UI code only ...

# ─── Debug mode: set EXAM_DEBUG=1 in VSCode terminal to enable ─────────────────
# In VSCode terminal run:  $env:EXAM_DEBUG="1" ; streamlit run app.py  (Windows)
# In VSCode terminal run:  EXAM_DEBUG=1 streamlit run app.py            (Mac/Linux)
DEBUG = os.environ.get("EXAM_DEBUG", "0") == "1"

# ─── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Medical Exams", layout="centered")

# ─── Exam catalogue ────────────────────────────────────────────────────────────
EXAMS = {
    "lung": {
        "label": "Lung Exams",
        "questions_url": "https://ima-files.s3.amazonaws.com/814180_114e80b1-0a46-4046-a7ee-9a69972b31f9.pdf",
        "answers_url":   "https://ima-files.s3.amazonaws.com/822587_8ebf6f4b-843b-4807-abf2-16767431b006.pdf",
    },
}

HEBREW_LETTERS = ["א", "ב", "ג", "ד"]



def crop_page_to_image1(page, y_start, y_end, dpi=150):
    padding = 10
    clip = fitz.Rect(page.rect.x0, max(0, y_start - padding),
                     page.rect.x1, min(page.rect.height, y_end + padding))
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, clip=clip)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def crop_page_to_image(page, y_start, y_end, dpi=150):
    padding = 10
    clip = fitz.Rect(
        page.rect.x0,
        max(0, y_start - padding),
        page.rect.x1,
        min(page.rect.height, y_end + padding),
    )
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)



# ─── Load exam ─────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading exam…")
def load_exam(exam_key):
    exam = EXAMS[exam_key]
    try:
        doc = open_pdf_from_url(exam["questions_url"])
        abytes = get_pdf_bytes(exam["answers_url"])
        #answers = parse_answer_pdf(abytes)
        #questions = find_all_questions(doc)
        answers = pdf_parser.parse_answer_pdf(abytes)
        questions = pdf_parser.find_all_questions(doc)
        

        # ── DEBUG: write Q<->A alignment file (only in dev mode) ──────────────────
        if DEBUG:
            with open("debug_qa_alignment.txt", "w", encoding="utf-8") as f:
                f.write(f"Exam: {exam_key}\n")
                f.write(f"Total questions found: {len(questions)}\n")
                f.write(f"Total answers found:   {len(answers)}\n\n")
                f.write(f"{'Q#':<6} {'Page':<6} {'Y-start':<10} {'Y-end':<10} {'Answer'}\n")
                f.write("-" * 50 + "\n")
                for q in questions:
                    ans = answers.get(q["q_num"], "-- NO ANSWER --")
                    if isinstance(ans, list):
                        ans = " + ".join(ans)
                    f.write(f"{q['q_num']:<6} {q['page_idx']:<6} {q['y_start']:<10.1f} {q['y_end']:<10.1f} {ans}\n")
            print(f"[DEBUG] Wrote debug_qa_alignment.txt  ({len(questions)} questions, {len(answers)} answers)")

    except Exception as e:
        st.error(f"Failed to load exam: {e}")
        st.stop()

    return doc, answers, questions


def get_question_image(doc, q_info) -> Image.Image:
    page = doc.load_page(q_info["page_idx"])
    return crop_page_to_image(page, q_info["y_start"], q_info["y_end"])



# ─── UI ────────────────────────────────────────────────────────────────────────
st.title("🏥 Medical Exams")

# ── Exam selector ──────────────────────────────────────────────────────────────
if st.session_state.exam_key is None:
    st.subheader("Choose an exam:")
    cols = st.columns(3)
    for i, (key, meta) in enumerate(EXAMS.items()):
        with cols[i % 3]:
            if st.button(meta["label"], width="stretch"):
                st.session_state.exam_key = key
                st.session_state.q_index  = 0
                reset_answer()
                st.rerun()
    st.stop()

# ── Load exam data ─────────────────────────────────────────────────────────────
doc, answers, questions = load_exam(st.session_state.exam_key)
total_q = len(questions)

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