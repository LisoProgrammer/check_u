# core/orchestrator.py
from ..loaders.pdf_loader import load_pdf
from ..ocr.tesseract_engine import TesseractEngine

class OCRPipeline:

    def __init__(self):
        self.ocr_engine = TesseractEngine()

    def process(self, pdf_bytes: bytes):
        images = load_pdf(pdf_bytes)

        full_text = ""
        for img in images:
            text = self.ocr_engine.extract_text(img)
            full_text += text

        return {
            "text": full_text
        }