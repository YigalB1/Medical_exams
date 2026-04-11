import io
import os
import fitz
from image_processor import crop_page_to_image


def _answer_to_text(answer_value):
    hebrew_to_latin = {"א": "A", "ב": "B", "ג": "C", "ד": "D"}

    if answer_value is None:
        return "-- NO ANSWER --"

    letters = answer_value if isinstance(answer_value, list) else [str(answer_value)]
    latin_parts = [hebrew_to_latin.get(letter, str(letter)) for letter in letters]
    raw_parts = [str(letter) for letter in letters]

    latin_text = " + ".join(latin_parts)
    raw_text = " + ".join(raw_parts)

    if latin_text == raw_text:
        return latin_text
    return f"{latin_text} ({raw_text})"


def export_questions_with_answers_pdf(doc, questions, answers, exam_key):
    os.makedirs("debug_exports", exist_ok=True)
    output_path = os.path.join("debug_exports", f"{exam_key}_questions_with_answers.pdf")

    if not questions:
        # Some PDFs may fail question parsing; avoid creating an invalid 0-page PDF.
        return None

    out_doc = fitz.open()
    page_width = 595
    page_height = 842
    margin = 36
    answer_band = 90

    for q in questions:
        src_page = doc.load_page(q["page_idx"])
        q_img = crop_page_to_image(src_page, q["y_start"], q["y_end"])
        img_bytes = io.BytesIO()
        q_img.save(img_bytes, format="PNG")

        page = out_doc.new_page(width=page_width, height=page_height)
        image_rect = fitz.Rect(margin, margin, page_width - margin, page_height - margin - answer_band)
        page.insert_image(image_rect, stream=img_bytes.getvalue(), keep_proportion=True)

        answer_text = _answer_to_text(answers.get(q["q_num"]))
        footer = (
            f"Question {q['q_num']} | Answer: {answer_text}\n"
            f"Source page: {q['page_idx'] + 1} | y_start={q['y_start']:.1f}, y_end={q['y_end']:.1f}"
        )
        page.insert_textbox(
            fitz.Rect(margin, page_height - margin - answer_band + 10, page_width - margin, page_height - margin),
            footer,
            fontsize=12,
            align=fitz.TEXT_ALIGN_LEFT,
        )

    if out_doc.page_count == 0:
        out_doc.close()
        return None

    out_doc.save(output_path, garbage=4, deflate=True)
    out_doc.close()
    return output_path


def export_question_answer_list(questions, answers, exam_key):
    os.makedirs("debug_exports", exist_ok=True)
    output_path = os.path.join("debug_exports", f"{exam_key}_question_answer_list.txt")

    ordered_q_nums = [q["q_num"] for q in questions]
    seen = set()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Exam: {exam_key}\n")
        f.write("Question -> Answer\n")
        f.write("-" * 32 + "\n")

        for q_num in ordered_q_nums:
            if q_num in seen:
                continue
            seen.add(q_num)
            answer_text = _answer_to_text(answers.get(q_num))
            f.write(f"{q_num}: {answer_text}\n")

    return output_path
