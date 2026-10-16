import os

import pymupdf  
from pypdf import PdfReader

PDF_DIR = "data/pdfs"


def extract_pages(file):
    reader = PdfReader(file)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({"page": i, "text": text})
    return pages


def pdf_path(name):
    return os.path.join(PDF_DIR, os.path.basename(name))


def save_pdf(uploaded):

    os.makedirs(PDF_DIR, exist_ok=True)
    with open(pdf_path(uploaded.name), "wb") as f:
        f.write(uploaded.getvalue())


def delete_pdf(name):
    path = pdf_path(name)
    if os.path.exists(path):
        os.remove(path)


def render_page(name, page_number, zoom=1.5):
    path = pdf_path(name)
    if not os.path.exists(path):
        return None
    with pymupdf.open(path) as doc:
        if page_number < 1 or page_number > len(doc):
            return None
        pix = doc[page_number - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        return pix.tobytes("png")