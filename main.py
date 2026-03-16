import os
import tkinter as tk
import sys
from tkinter import filedialog, messagebox
from pdf_mng import PDFViewer

sys.dont_write_bytecode = True  # prevent .pyc files

print("Starting!")
print("Files in folder:", os.listdir())


# Extract lines before launching the GUI
#lines = extract_text_lines("C:/Users/Tru1/Downloads/answers.pdf")

root = tk.Tk()
app = PDFViewer(root)
root.mainloop()

print("done2")
