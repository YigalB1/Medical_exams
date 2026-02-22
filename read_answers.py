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
    return lines

# Usage:
#lines = extract_text_lines_with_pages("C:/Users/Tru1/Downloads/questions.pdf")
#for item in lines:
#    print(f"Page {item['page']}: {item['text']}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFViewer(root)
    root.mainloop()
