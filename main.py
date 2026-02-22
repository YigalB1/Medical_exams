import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pdf_mng import PDFViewer
from read_answers import extract_text_lines


print("Starting!")
print("Files in folder:", os.listdir())


# Extract lines before launching the GUI
lines = extract_text_lines("C:/Users/Tru1/Downloads/answers.pdf")
for i, line in enumerate(lines):
    print(f"{i}: {line}")



root = tk.Tk()
app = PDFViewer(root)
root.mainloop()

print("done2")
