import re
import fitz
import tkinter as tk
from pdf_mng import PDFViewer


def extract_text_lines(pdf_path):
    doc = fitz.open(pdf_path)
    lines = []
    for page_num, page in enumerate(doc):
        text = page.get_text()
        for line in text.splitlines():
            line = line.strip()
            if line:
                lines.append({"page": page_num + 1, "text": line})
    # Skip first 6 lines
    lines = lines[7:]

    for i, line in enumerate(lines):
        print(f"{i}: {line}")

    answers = {}
    for item in lines:
        text = item['text']
        print("t1",text)
        match = re.match(r"^(\d+)([אבגד])", text)
        if match:
            question_num = int(match.group(1))
            answer = match.group(2)
            answers[question_num] = answer
    print("answers")
    for i, ans in enumerate(answers):
        print(f"{i}: {ans}")

    
    return lines

# Usage:
#lines = extract_text_lines_with_pages("C:/Users/Tru1/Downloads/questions.pdf")
#for item in lines:
#    print(f"Page {item['page']}: {item['text']}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFViewer(root)
    root.mainloop()
