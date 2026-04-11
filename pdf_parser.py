import io
import re
import fitz
from typing import Dict, List, Union

def parse_answer_pdf(source: Union[bytes, io.BufferedReader]) -> Dict[int, str]:
    """
    Parse answer-key PDF and return a mapping of question number -> answer.
    """
    if isinstance(source, bytes):
        doc = fitz.open(stream=source, filetype="pdf")
    else:
        doc = fitz.open(stream=source.read(), filetype="pdf")

    answers: Dict[int, str] = {}
    for page in doc:
        text = page.get_text("text")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            match = re.match(r"^(\d+)\s*[.)]?\s*([אבגד])", line)
            if match:
                q_num = int(match.group(1))
                answers[q_num] = match.group(2)

    return answers


def find_all_questions(doc: fitz.Document) -> List[Dict[str, Union[int, float]]]:
    page_height_map = {i: doc.load_page(i).rect.height for i in range(doc.page_count)}

    candidates = []
    for page_idx in range(doc.page_count):
        page = doc.load_page(page_idx)
        blocks = page.get_text("blocks", sort=True)
        for block in blocks:
            x0, y0, x1, y1, text, *_ = block
            if not text.strip():
                continue

            first_line = text.strip().splitlines()[0].strip()

            # 1-digit headers like: "1 .", "2.", "3 . text..."
            if re.match(r"^\d\s*\.(?!\d)", first_line):
                m = re.match(r"^(\d)\s*\.(?!\d)", first_line)
                q_num = int(m.group(1))
            # 1-3 digit number-only headers: "1", "10", "11", "100"
            elif re.match(r"^[1-9]\d{0,2}\s*\.?\s*$", first_line):
                m = re.match(r"^([1-9]\d{0,2})", first_line)
                q_num = int(m.group(1))
            # 2-3 digit headers with trailing text: "10. text..."
            elif re.match(r"^[1-9]\d{1,2}\s*\.(?!\d)\s*\S", first_line):
                m = re.match(r"^([1-9]\d{1,2})", first_line)
                q_num = int(m.group(1))
            else:
                continue

            if q_num < 1 or q_num > 200:
                continue
            if y0 > page_height_map[page_idx] * 0.90:
                continue

            candidates.append((q_num, page_idx, y0))

    # Accept only increasing question numbers to avoid false positives (e.g., decimals in tables).
    accepted = []
    expected = 1
    for q_num, page_idx, y0 in candidates:
        if q_num == expected:
            accepted.append((q_num, page_idx, y0))
            expected += 1

    questions: List[Dict[str, Union[int, float]]] = []
    for i, (q_num, page_idx, y_start) in enumerate(accepted):
        if i + 1 < len(accepted):
            _, next_page_idx, next_y = accepted[i + 1]
            y_end = next_y if next_page_idx == page_idx else page_height_map[page_idx] * 0.90
        else:
            y_end = page_height_map[page_idx] * 0.90

        questions.append({
            "q_num": q_num,
            "page_idx": page_idx,
            "y_start": y_start,
            "y_end": y_end,
        })

    return questions