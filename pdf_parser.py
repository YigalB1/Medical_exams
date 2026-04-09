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
    questions: List[Dict[str, Union[int, float]]] = []

    for page_idx, page in enumerate(doc):
        blocks = page.get_text("blocks")
        found = []

        for block in blocks:
            x0, y0, x1, y1, text, _, _ = block
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                match = re.match(r"^(\d+)\s*[.)]", line)
                if match:
                    found.append({"page_idx": page_idx, "q_num": int(match.group(1)), "y_start": y0, "x0": x0, "x1": x1})
                    break

        for idx, q in enumerate(found):
            next_y = found[idx + 1]["y_start"] if idx + 1 < len(found) else page.rect.height
            questions.append({
                "page_idx": q["page_idx"],
                "q_num": q["q_num"],
                "y_start": q["y_start"],
                "y_end": next_y,
            })

    return questions