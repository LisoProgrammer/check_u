# preprocess/image_cleaner.py

import cv2
import numpy as np
from PIL import Image
from typing import Tuple
import os
from datetime import datetime


def create_image_stage_pdf(stages, filename):
    os.makedirs("test_image_cleaner", exist_ok=True)

    pages = []

    for name, img in stages:

        if not isinstance(img, Image.Image):
            img = Image.fromarray(img)

        img = img.convert("RGB")

        pages.append(img)


    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output = (
        f"test_image_cleaner/"
        f"{filename}_{timestamp}.pdf"
    )


    pages[0].save(
        output,
        save_all=True,
        append_images=pages[1:]
    )


    print(
        f"PDF del image cleaner generado: {output}"
    )



class ImageCleaner:
    """
    Limpia y normaliza imágenes para mejorar OCR
    """


    def __init__(
        self,
        resize_width: int = 1200,
        blur_kernel: Tuple[int,int] = (3,3)
    ):

        self.resize_width = resize_width
        self.blur_kernel = blur_kernel



    def clean_image(self, image) -> np.ndarray:


        image_stages = []


        # PIL -> numpy
        if isinstance(image, Image.Image):

            img = np.array(image)

        else:

            img = image.copy()



        # RGB -> escala de grises
        if len(img.shape) == 3:

            img = cv2.cvtColor(
                img,
                cv2.COLOR_RGB2GRAY
            )


        image_stages.append(
            ("Escala gris", img)
        )



        # Redimensionar
        img = self._resize_image(img)


        image_stages.append(
            ("Resize", img)
        )



        # Reducir ruido
        img = cv2.fastNlMeansDenoising(
            img,
            None,
            h=15,
            templateWindowSize=7,
            searchWindowSize=21
        )


        image_stages.append(
            ("Reduccion ruido", img)
        )



        # Suavizado ligero
        img = cv2.GaussianBlur(
            img,
            self.blur_kernel,
            0
        )


        image_stages.append(
            ("Gaussian Blur", img)
        )



        # Mejorar contraste local
        clahe = cv2.createCLAHE(
            clipLimit=1.0,
            tileGridSize=(8,8)
        )


        img = clahe.apply(img)


        image_stages.append(
            ("Contraste CLAHE", img)
        )



        # Binarización adaptativa
        img = cv2.adaptiveThreshold(
            img,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            17,
            13
        )


        image_stages.append(
            ("Threshold", img)
        )



        # Crear PDF de pruebas
        create_image_stage_pdf(
            image_stages,
            "img_cleaner_test"
        )



        return img




    def _resize_image(
        self,
        image: np.ndarray
    ) -> np.ndarray:


        height, width = image.shape[:2]


        if width > self.resize_width:

            scale = (
                self.resize_width /
                width
            )

            new_height = int(
                height * scale
            )


            image = cv2.resize(
                image,
                (
                    self.resize_width,
                    new_height
                )
            )


        return image




    def enhance_contrast(
        self,
        image: np.ndarray,
        alpha: float = 1.5,
        beta: float = 0
    ) -> np.ndarray:


        return cv2.convertScaleAbs(
            image,
            alpha=alpha,
            beta=beta
        )




    def remove_shadows(
        self,
        image: np.ndarray
    ) -> np.ndarray:


        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (8,8)
        )


        closing = cv2.morphologyEx(
            image,
            cv2.MORPH_CLOSE,
            kernel
        )


        opening = cv2.morphologyEx(
            closing,
            cv2.MORPH_OPEN,
            kernel
        )


        return opening




def clean_image(
    image,
    resize_width: int = 1200
) -> np.ndarray:


    cleaner = ImageCleaner(
        resize_width=resize_width
    )


    return cleaner.clean_image(image)