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

# ─── Answer PDF parser ─────────────────────────────────────────────────────────
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



def find_all_questions(doc):
    page_height_map = {i: doc.load_page(i).rect.height for i in range(doc.page_count)}
    
    candidates = []
    for page_idx in range(doc.page_count):
        page   = doc.load_page(page_idx)
        blocks = page.get_text("blocks", sort=True)
        for block in blocks:
            x0, y0, x1, y1, text, *_ = block
            if not text.strip():
                continue
            first_line = text.strip().splitlines()[0].strip()

            # Match EITHER:
            # 1-digit:  "1 ."  "2."  "3 .  text..."
            # 2-digit:  "10"  "11"  "12"  (number alone, no dot)
            m = re.match(r"^(\d{1,2})\s*\.?", first_line)
            if not m:
                continue

            q_num = int(m.group(1))
            if q_num < 1 or q_num > 150:
                continue

            # For 1-digit: must have a dot
            if q_num < 10:
                if not re.match(r"^\d\s*\.", first_line):
                    continue

            # For 2-digit: block must be just the number (no dot, short text)
            if q_num >= 10:
                # Accept if line is just the number, optionally with a dot
                if not re.match(r"^\d{2}\s*\.?\s*$", first_line):
                    # Also accept if line starts with number+dot+text
                    if not re.match(r"^\d{2}\s*\.\s+\S", first_line):
                        continue

            # Ignore footer area
            if y0 > page_height_map[page_idx] * 0.90:
                continue

            candidates.append((q_num, page_idx, y0))

    # Enforce sequential order
    accepted = []
    expected = 1
    for q_num, page_idx, y0 in candidates:
        if q_num == expected:
            accepted.append((q_num, page_idx, y0))
            expected += 1

    # Build y_end for each question
    questions = []
    for i, (q_num, page_idx, y_start) in enumerate(accepted):
        if i + 1 < len(accepted):
            next_q_num, next_page, next_y = accepted[i + 1]
            if next_page == page_idx:
                y_end = next_y
            else:
                y_end = page_height_map[page_idx] * 0.90
        else:
            y_end = page_height_map[page_idx] * 0.90

        questions.append({
            "q_num":    q_num,
            "page_idx": page_idx,
            "y_start":  y_start,
            "y_end":    y_end,
        })

    return questions


# ─── Question splitter ─────────────────────────────────────────────────────────
# to be replaced with find_all_questions
def find_question_boundaries(page):
    page_height = page.rect.height
    blocks = page.get_text("blocks", sort=True)

    boundaries = []
    for block in blocks:
        x0, y0, x1, y1, text, *_ = block
        if not text.strip():
            continue
        first_line = text.strip().splitlines()[0].strip()

        # Match patterns like: "1 .", "4 .  ", "10 .", "6."  (number then optional space then dot)
        m = re.match(r"^(\d{1,2})\s*\.", first_line)
        if not m:
            continue

        q_num = int(m.group(1))

        # Ignore answer choices: .א .ב .ג .ד lines (single letter answers)
        # These are short blocks near bottom, but safer to filter by q_num range
        if q_num < 1 or q_num > 150:
            continue

        # Ignore page numbers / footers near bottom
        if y0 > page_height * 0.90:
            continue

        boundaries.append((q_num, y0))

    if not boundaries:
        return []

    # Keep first occurrence of each q_num (in case of duplicates)
    seen = {}
    for q_num, y_top in boundaries:
        if q_num not in seen:
            seen[q_num] = y_top
    boundaries = sorted(seen.items(), key=lambda x: x[1])

    result = []
    for i, (q_num, y_top) in enumerate(boundaries):
        y_bottom = boundaries[i+1][1] if i+1 < len(boundaries) else page_height * 0.90
        result.append((q_num, y_top, y_bottom))

    return result


def crop_page_to_image(page, y_start, y_end, dpi=150):
    padding = 10
    clip = fitz.Rect(page.rect.x0, max(0, y_start - padding),
                     page.rect.x1, min(page.rect.height, y_end + padding))
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, clip=clip)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


# ─── Load exam ─────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading exam…")
def load_exam(exam_key):
    exam    = EXAMS[exam_key]
    doc     = open_pdf_from_url(exam["questions_url"])
    # DEBUG 
    # Add temporarily in load_exam() right after doc = open_pdf_from_url(...)
    for page_idx in range(5,10):  # check first 5 pages
        page = doc.load_page(page_idx)
        blocks = page.get_text("blocks", sort=True)
        print(f"\n=== PAGE {page_idx} ===")
        for block in blocks:
            x0, y0, x1, y1, text, *_ = block
            first_line = text.strip().splitlines()[0][:80] if text.strip() else ""
            print(f"  y={y0:.1f}-{y1:.1f} | {repr(first_line)}")
    # end of debug

    abytes  = get_pdf_bytes(exam["answers_url"])
    answers = parse_answer_pdf(abytes)

    questions = find_all_questions(doc)

    """questions = []
    for page_idx in range(doc.page_count):
        page   = doc.load_page(page_idx)
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
            questions.append({
                "q_num":    page_idx + 1,
                "page_idx": page_idx,
                "y_start":  0,
                "y_end":    page.rect.height,
            })
    """

    questions.sort(key=lambda q: q["q_num"])
    return doc, answers, questions


def get_question_image(doc, q_info) -> Image.Image:
    page = doc.load_page(q_info["page_idx"])
    return crop_page_to_image(page, q_info["y_start"], q_info["y_end"])


# ─── Session state ─────────────────────────────────────────────────────────────
def _init():
    defaults = dict(
        exam_key    = None,
        q_index     = 0,
        selected    = [],
        result_msg  = "",
        result_ok   = None,
        score_good  = 0,       # correct answers count
        score_bad   = 0,       # wrong answers count
        answered    = set(),   # set of q_index already checked
        show_summary= False,   # show exit summary screen
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


def reset_answer():
    st.session_state.selected   = []
    st.session_state.result_msg = ""
    st.session_state.result_ok  = None


def reset_exam():
    st.session_state.exam_key     = None
    st.session_state.q_index      = 0
    st.session_state.score_good   = 0
    st.session_state.score_bad    = 0
    st.session_state.answered     = set()
    st.session_state.show_summary = False
    reset_answer()


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
        if correct is None:
            st.info(f"No answer key found for question {q_num}.")
        else:
            correct_list = correct if isinstance(correct, list) else [correct]
            # Only count score once per question
            if q_index not in st.session_state.answered:
                st.session_state.answered.add(q_index)
                if sorted(selected) == sorted(correct_list):
                    st.session_state.score_good += 1
                else:
                    st.session_state.score_bad += 1

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