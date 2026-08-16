from ..loaders.pdf_loader import load_pdf
from ..ocr.tesseract_engine import TesseractEngine

from ..preprocess.image_cleaner import ImageCleaner
from ..preprocess.check_inclination import SkewDetector

from ..postprocess.cleaner import TextCleaner
from ..postprocess.structure import TextStructurer


class OCRPipeline:


    def __init__(self):

        self.ocr_engine = TesseractEngine()

        self.image_cleaner = ImageCleaner(
            resize_width=2000
        )

        self.skew_detector = SkewDetector()

        self.text_cleaner = TextCleaner()

        self.structurer = TextStructurer()



    def process(self, pdf_bytes: bytes):


        images = load_pdf(pdf_bytes)


        raw_text = ""

        processed_images = []



        for img in images:


            # -------------------------
            # PREPROCESAMIENTO IMAGEN
            # -------------------------

            cleaned_img = self.image_cleaner.clean_image(
                img
            )


            angle = self.skew_detector.detect_skew(
                cleaned_img
            )


            if abs(angle) > 0.5:

                cleaned_img, final_angle = self.skew_detector.auto_correct(
                    cleaned_img
                )


            processed_images.append(
                cleaned_img
            )



            # -------------------------
            # OCR
            # -------------------------

            text = self.ocr_engine.extract_text(
                cleaned_img
            )


            raw_text += text + "\n"




        # -------------------------
        # LIMPIEZA TEXTO
        # -------------------------

        cleaned_text = self.text_cleaner.clean(
            raw_text
        )



        # -------------------------
        # ESTRUCTURAR
        # -------------------------

        blocks = self.structurer.structure(
            cleaned_text
        )


        fields = self.structurer.extract_key_fields(
            cleaned_text, ""
        )



        return {


            # texto original OCR
            "raw_text": raw_text,


            # texto corregido
            "text": cleaned_text,


            # bloques detectados
            "blocks": blocks,


            # campos extraídos
            "fields": fields,


            # útil para debug
            "images": processed_images

        }