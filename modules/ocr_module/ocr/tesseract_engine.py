# ocr/tesseract_engine.py
import pytesseract
from pytesseract import Output
from .engine import OCREngine

# Caracteres validos en una franja MRZ (letras, digitos y "<" de
# relleno). Se usa como whitelist en extract_mrz_text para que
# Tesseract no intente "corregir" hacia palabras del diccionario ni
# confunda tan seguido letras con digitos parecidos (L/1, O/0, etc.).
MRZ_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"


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

    def extract_mrz_text(self, image, psm: int = 6) -> str:
        """
        Pasada de OCR dedicada a una franja tipo MRZ (o cualquier
        recorte donde se espere solo letras/digitos/'<'), pensada para
        usarse sobre un recorte de la franja inferior de la cedula,
        no sobre la pagina completa.

        Diferencias frente a extract_text_with_confidence:
        - lang='eng' en vez de 'spa': evita que el diccionario en
          español intente "corregir" caracteres sueltos hacia palabras
          reales, algo que no tiene sentido en una franja de codigo.
        - whitelist restringido a MRZ_CHARSET: fuerza a Tesseract a
          elegir entre esos caracteres, reduciendo confusiones como
          'L' por '1' que son mas frecuentes con la configuracion
          general (sin whitelist) usada en el resto del documento.
        - psm 6 (bloque uniforme de texto) en vez de la segmentacion
          automatica de pagina completa (psm 3, la que usan los otros
          metodos), mas apropiado para una franja angosta de pocas
          lineas.
        """
        config = (
            f"--oem 3 --psm {psm} "
            f"-c tessedit_char_whitelist={MRZ_CHARSET}"
        )
        return pytesseract.image_to_string(image, lang="eng", config=config)