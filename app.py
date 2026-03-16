import streamlit as st
import fitz
from PIL import Image
import io
from pdf_web import open_pdf_from_url, get_pdf_bytes
import re

# ─── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Medical Exams", layout="centered")

# ─── Exam catalogue  (add more rows as needed) ─────────────────────────────────
EXAMS = {
    "lung": {
        "label": "Lung Exams",
        "questions_url": "https://ima-files.s3.amazonaws.com/814180_114e80b1-0a46-4046-a7ee-9a69972b31f9.pdf",
        "answers_url":   "https://ima-files.s3.amazonaws.com/822587_8ebf6f4b-843b-4807-abf2-16767431b006.pdf",
    },
    # "cardio": { "label": "Cardiology", "questions_url": "...", "answers_url": "..." },
}

HEBREW_LETTERS = ["א", "ב", "ג", "ד"]

# ─── Helpers ───────────────────────────────────────────────────────────────────

def parse_answer_pdf(source):
    if isinstance(source, (str, bytes)):
        doc = fitz.open(stream=source, filetype="pdf") if isinstance(source, bytes) else fitz.open(source)
    else:
        doc = fitz.open(stream=source.read(), filetype="pdf")

    lines = []
    for page in doc:
        for line in page.get_text(sort=True).splitlines():
            line = line.strip()
            if line:
                lines.append(line)

    hebrew_letters = set("אבגד")
    skip_words     = {"מספר", "שאלה", "תשובה", "נכונה", "הערה", "מפתח", "תשובות"}
    page_marker    = re.compile(r"^\d+/\d+$")

    answers = {}
    for line in lines[3:]:
        if any(w in line for w in skip_words) or page_marker.match(line):
            continue
        match = re.match(r"^([אבגד][\s אבגד]*)\s+(\d+)\s*$", line)
        if match:
            letters = [c for c in match.group(1) if c in hebrew_letters]
            q_num   = int(match.group(2))
            answers[q_num] = letters if len(letters) > 1 else letters[0]
    return answers


@st.cache_resource(show_spinner="Loading PDF…")
def load_exam(exam_key):
    exam  = EXAMS[exam_key]
    doc   = open_pdf_from_url(exam["questions_url"])
    abytes = get_pdf_bytes(exam["answers_url"])
    answers = parse_answer_pdf(abytes)
    return doc, answers


def render_page(doc, page_index: int) -> Image.Image:
    page = doc.load_page(page_index)
    pix  = page.get_pixmap(dpi=150)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


# ─── Session-state defaults ────────────────────────────────────────────────────
def _init():
    defaults = dict(
        exam_key   = None,
        page_idx   = 0,
        checked    = False,
        result_msg = "",
        result_ok  = None,
        selected   = [],
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

# ─── UI ────────────────────────────────────────────────────────────────────────
st.title("🏥 Medical Exams")

# ── Exam selector (acts like the homepage buttons for now) ──────────────────
if st.session_state.exam_key is None:
    st.subheader("Choose an exam:")
    cols = st.columns(3)
    for i, (key, meta) in enumerate(EXAMS.items()):
        with cols[i % 3]:
            if st.button(meta["label"], use_container_width=True):
                st.session_state.exam_key = key
                st.session_state.page_idx = 0
                st.rerun()
    st.stop()

# ── Load PDF & answers ──────────────────────────────────────────────────────
doc, answers = load_exam(st.session_state.exam_key)
total_pages  = doc.page_count
page_idx     = st.session_state.page_idx
question_num = page_idx + 1

# ── Back button ────────────────────────────────────────────────────────────
if st.button("← Back to exam list"):
    st.session_state.exam_key = None
    st.rerun()

# ── Page image ─────────────────────────────────────────────────────────────
img = render_page(doc, page_idx)
st.image(img, use_container_width=True)

# ── Navigation ─────────────────────────────────────────────────────────────
col_prev, col_info, col_next = st.columns([1, 2, 1])
with col_prev:
    if st.button("◀ Prev", disabled=(page_idx == 0)):
        st.session_state.page_idx -= 1
        st.session_state.selected   = []
        st.session_state.result_msg = ""
        st.session_state.result_ok  = None
        st.rerun()
with col_info:
    st.markdown(f"<p style='text-align:center;margin-top:6px'>Page {page_idx+1} / {total_pages}</p>",
                unsafe_allow_html=True)
with col_next:
    if st.button("Next ▶", disabled=(page_idx >= total_pages - 1)):
        st.session_state.page_idx += 1
        st.session_state.selected   = []
        st.session_state.result_msg = ""
        st.session_state.result_ok  = None
        st.rerun()

st.divider()

# ── Answer section ─────────────────────────────────────────────────────────
st.subheader(f"Question #{question_num}")

selected = st.pills(
    "Select answer(s):",
    options=HEBREW_LETTERS,
    selection_mode="multi",
    default=st.session_state.selected,
    key=f"pills_{page_idx}",
)
st.session_state.selected = selected or []

if st.button("✔ Check Answer", type="primary"):
    if not selected:
        st.warning("Please select an answer first.")
    else:
        correct = answers.get(question_num)
        if correct is None:
            st.info("No answer key found for this question.")
        else:
            correct_list = correct if isinstance(correct, list) else [correct]
            if sorted(selected) == sorted(correct_list):
                st.session_state.result_msg = f"✔ Correct!  Answer: {' '.join(correct_list)}"
                st.session_state.result_ok  = True
            else:
                st.session_state.result_msg = f"✘ Wrong.  Correct answer: {' '.join(correct_list)}"
                st.session_state.result_ok  = False

if st.session_state.result_msg:
    if st.session_state.result_ok:
        st.success(st.session_state.result_msg)
    else:
        st.error(st.session_state.result_msg)