# ocr/tesseract_engine.py
import pytesseract
from pytesseract import Output
from .engine import OCREngine

class TesseractEngine(OCREngine):
    def extract_text(self, image) -> str:
        return pytesseract.image_to_string(image, lang='spa')

    def extract_text_with_confidence(self, image, min_confidence: int = 40) -> str:
        """
        Extrae texto descartando palabras con baja confianza del OCR.
        Esto ataca el ruido en el origen, no después.
        """
        data = pytesseract.image_to_data(
            image, lang='spa', output_type=Output.DICT
        )

        lines = {}
        for i, word in enumerate(data["text"]):
            word = word.strip()
            conf = int(data["conf"][i])

            if not word or conf < min_confidence:
                continue

            line_key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            lines.setdefault(line_key, []).append(word)

        return "\n".join(" ".join(words) for words in lines.values())