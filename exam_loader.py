import streamlit as st
import pdf_parser
from pdf_web import open_pdf_from_url, get_pdf_bytes
from debug_exporter import export_questions_with_answers_pdf

EXAMS = {
    "lung": {
        "label": "Lung Exams",
        "questions_url": "https://ima-files.s3.amazonaws.com/814180_114e80b1-0a46-4046-a7ee-9a69972b31f9.pdf",
        "answers_url":   "https://ima-files.s3.amazonaws.com/822587_8ebf6f4b-843b-4807-abf2-16767431b006.pdf",
    },
}


@st.cache_resource(show_spinner="Loading exam…")
def load_exam(exam_key, debug=False, debug_qa_pdf=False):
    exam = EXAMS[exam_key]
    try:
        doc = open_pdf_from_url(exam["questions_url"])
        abytes = get_pdf_bytes(exam["answers_url"])
        answers = pdf_parser.parse_answer_pdf(abytes)
        questions = pdf_parser.find_all_questions(doc)

        # ── DEBUG: write Q<->A alignment file ─────────────────────────────────
        if debug:
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

        qa_export_path = None
        if debug_qa_pdf:
            qa_export_path = export_questions_with_answers_pdf(doc, questions, answers, exam_key)
            print(f"[DEBUG] Wrote {qa_export_path}")

    except Exception as e:
        st.error(f"Failed to load exam: {e}")
        st.stop()

    return doc, answers, questions, qa_export_path
