import streamlit as st
import fitz
from PIL import Image
import io
import re
from pdf_web import open_pdf_from_url, get_pdf_bytes

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

# ─── Answer PDF parser (unchanged from your original) ─────────────────────────
def parse_answer_pdf(source):
    if isinstance(source, bytes):
        doc = fitz.open(stream=source, filetype="pdf")
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


# ─── Question splitter ─────────────────────────────────────────────────────────
def find_question_boundaries(page):
    """
    Returns a list of (q_num, y_start, y_end) for each question found on this page.
    Questions are detected by lines starting with a number followed by a dot,
    e.g. '1.' or '2.' at the start of a text block (RTL Hebrew pages).
    y coordinates are in PDF points.
    """
    page_height = page.rect.height

    # Extract text blocks with their bounding boxes
    blocks = page.get_text("blocks", sort=True)  # sorted top-to-bottom

    # Find lines that start a new question: match "N." or ".N" (RTL)
    # In Hebrew PDFs the number can appear as the last token due to RTL
    q_pattern = re.compile(r"^(\d+)\s*\.|\.(\s*\d+)$")

    boundaries = []  # list of (q_num, y_top)
    for block in blocks:
        x0, y0, x1, y1, text, *_ = block
        first_line = text.strip().splitlines()[0].strip() if text.strip() else ""
        # Try matching question number at start or end of line (RTL)
        m = re.match(r"^(\d+)\s*\.", first_line) or re.search(r"\.?\s*(\d+)\s*$", first_line)
        if m:
            q_num = int(m.group(1))
            if 1 <= q_num <= 200:  # sanity check
                boundaries.append((q_num, y0))

    if not boundaries:
        return []

    # Build (q_num, y_start, y_end) triples
    result = []
    for i, (q_num, y_top) in enumerate(boundaries):
        y_bottom = boundaries[i + 1][1] if i + 1 < len(boundaries) else page_height
        result.append((q_num, y_top, y_bottom))

    return result


def crop_page_to_image(page, y_start, y_end, dpi=150):
    """Crop a page between y_start and y_end and return a PIL Image."""
    # Add small padding
    padding = 10
    clip = fitz.Rect(page.rect.x0, max(0, y_start - padding),
                     page.rect.x1, min(page.rect.height, y_end + padding))
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, clip=clip)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


# ─── Build question list from entire PDF ──────────────────────────────────────
@st.cache_resource(show_spinner="Loading exam…")
def load_exam(exam_key):
    exam    = EXAMS[exam_key]
    doc     = open_pdf_from_url(exam["questions_url"])
    # 28March debug
    
    abytes  = get_pdf_bytes(exam["answers_url"])
    answers = parse_answer_pdf(abytes)

    # Build list of questions: {q_num, page_idx, y_start, y_end}
    questions = []
    for page_idx in range(doc.page_count):
        page = doc.load_page(page_idx)
        bounds = find_question_boundaries(page)
        if bounds:
            for q_num, y_start, y_end in bounds:
                questions.append({
                    "q_num":    q_num,
                    "page_idx": page_idx,
                    "y_start":  y_start,
                    "y_end":    y_end,
                })
        else:
            # fallback: treat full page as one question
            questions.append({
                "q_num":    page_idx + 1,
                "page_idx": page_idx,
                "y_start":  0,
                "y_end":    page.rect.height,
            })


    # Add this temporarily in load_exam(), after building the questions list
    for q in questions[:10]:
        print(f"Q{q['q_num']} | page {q['page_idx']} | y: {q['y_start']:.1f} → {q['y_end']:.1f}")

    # Sort by question number
    questions.sort(key=lambda q: q["q_num"])
    return doc, answers, questions


def get_question_image(doc, q_info, dpi=150) -> Image.Image:
    page = doc.load_page(q_info["page_idx"])
    return crop_page_to_image(page, q_info["y_start"], q_info["y_end"], dpi)


# ─── Session state ─────────────────────────────────────────────────────────────
def _init():
    defaults = dict(
        exam_key   = None,
        q_index    = 0,       # index into questions list
        selected   = [],
        result_msg = "",
        result_ok  = None,
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


def reset_answer():
    st.session_state.selected   = []
    st.session_state.result_msg = ""
    st.session_state.result_ok  = None


# ─── UI ────────────────────────────────────────────────────────────────────────
st.title("🏥 Medical Exams")

# ── Exam selector ──────────────────────────────────────────────────────────────
if st.session_state.exam_key is None:
    st.subheader("Choose an exam:")
    cols = st.columns(3)
    for i, (key, meta) in enumerate(EXAMS.items()):
        with cols[i % 3]:
            if st.button(meta["label"], use_container_width=True):
                st.session_state.exam_key = key
                st.session_state.q_index  = 0
                reset_answer()
                st.rerun()
    st.stop()

# ── Load exam ──────────────────────────────────────────────────────────────────
doc, answers, questions = load_exam(st.session_state.exam_key)
total_q   = len(questions)
q_index   = st.session_state.q_index
q_info    = questions[q_index]
q_num     = q_info["q_num"]

# ── Back button ────────────────────────────────────────────────────────────────
if st.button("← Back to exam list"):
    st.session_state.exam_key = None
    st.rerun()

# ── Question image ─────────────────────────────────────────────────────────────
img = get_question_image(doc, q_info)
st.image(img, use_container_width=True)

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
        if correct is None:
            st.info(f"No answer key found for question {q_num}.")
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