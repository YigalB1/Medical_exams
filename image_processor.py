import fitz
from PIL import Image


def crop_page_to_image(page, y_start, y_end, dpi=150):
    padding = 10
    clip = fitz.Rect(
        page.rect.x0,
        max(0, y_start - padding),
        page.rect.x1,
        min(page.rect.height, y_end + padding),
    )
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def get_question_image(doc, q_info) -> Image.Image:
    page = doc.load_page(q_info["page_idx"])
    return crop_page_to_image(page, q_info["y_start"], q_info["y_end"])
