import io
import re
import fitz
from typing import Dict, List, Union

def parse_answer_pdf(source):
    """
    Parse an answer-key PDF and return a mapping of question number -> answer.
    """
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


# ─── Question finder (sequential, whole-doc scan) ─────────────────────────────
def find_all_questions(doc):
    """
    Scan the PDF document and return question metadata for each detected question.
    """
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

            # 1-digit questions: "1 ."  "2."  "3 .  text..."
            if re.match(r"^\d\s*\.", first_line):
                m = re.match(r"^(\d)\s*\.", first_line)
                q_num = int(m.group(1))
            # 2-or-3-digit questions: "10"  "11"  "100" (number alone, no dot)
            elif re.match(r"^\d{2,3}\s*\.?\s*$", first_line):
                m = re.match(r"^(\d{2,3})", first_line)
                q_num = int(m.group(1))
            # 2-or-3-digit questions with dot+text: "10. text..."
            elif re.match(r"^\d{2,3}\s*\.\s+\S", first_line):
                m = re.match(r"^(\d{2,3})", first_line)
                q_num = int(m.group(1))
            else:
                continue

            if q_num < 1 or q_num > 200:
                continue
            if y0 > page_height_map[page_idx] * 0.90:
                continue

            candidates.append((q_num, page_idx, y0))

    # Enforce sequential order — only accept q_num == expected next
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
            y_end = next_y if next_page == page_idx else page_height_map[page_idx] * 0.90
        else:
            y_end = page_height_map[page_idx] * 0.90
        questions.append({
            "q_num":    q_num,
            "page_idx": page_idx,
            "y_start":  y_start,
            "y_end":    y_end,
        })

    return questions