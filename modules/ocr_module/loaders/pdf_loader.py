# loaders/pdf_loader.py
from pdf2image import convert_from_bytes

def load_pdf(pdf_bytes: bytes):
    return convert_from_bytes(pdf_bytes)