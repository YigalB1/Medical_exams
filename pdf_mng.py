import fitz
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog


class PDFViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Viewer")
        self.root.geometry("900x1100")
        self.root.resizable(False, False)  # lock window size
        self.doc = None
        self.current_page = 0
        self._resize_job = None

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Load PDF", command=self.load_pdf).pack(side="left", padx=5)
        tk.Button(btn_frame, text="◀ Prev", command=self.prev_page).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Next ▶", command=self.next_page).pack(side="left", padx=5)

        self.page_label = tk.Label(btn_frame, text="No PDF loaded")
        self.page_label.pack(side="left", padx=10)

        # Use Canvas instead of Label - doesn't resize to fit content
        self.canvas = tk.Canvas(root, bg="gray")
        self.canvas.pack(fill="both", expand=True)

    def load_pdf(self):
        #file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        file_path="C:/Users/Tru1/Downloads/questions.pdf"

        if not file_path:
            return

        self.doc = fitz.open(file_path)
        self.current_page = 0
        self.update_page_label()
        self.show_page()

    def show_page(self):
        if not self.doc:
            return

        self.root.update_idletasks()
        page = self.doc.load_page(self.current_page)
        pix = page.get_pixmap(dpi=150)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Scale to fit canvas without exceeding it
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        scale = min(canvas_w / img.width, canvas_h / img.height)
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")  # clear previous image
        # Center the image in the canvas
        self.canvas.create_image(canvas_w // 2, canvas_h // 2, anchor="center", image=self.tk_img)

    def next_page(self):
        if self.doc and self.current_page < self.doc.page_count - 1:
            self.current_page += 1
            self.update_page_label()
            self.show_page()

    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.update_page_label()
            self.show_page()

    def update_page_label(self):
        if self.doc:
            self.page_label.config(
                text=f"Page {self.current_page + 1} / {self.doc.page_count}"
            )



if __name__ == "__main__":
    root = tk.Tk()
    app = PDFViewer(root)
    root.mainloop()
