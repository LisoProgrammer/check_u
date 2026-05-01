# ocr/tesseract_engine.py
import pytesseract
from .engine import OCREngine

class TesseractEngine(OCREngine):
    def extract_text(self, image) -> str:
        return pytesseract.image_to_string(image, lang='spa')