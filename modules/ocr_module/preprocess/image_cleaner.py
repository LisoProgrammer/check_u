# preprocess/image_cleaner.py
import cv2
import numpy as np
from PIL import Image
from typing import Tuple

class ImageCleaner:
    """Limpia y normaliza imágenes para mejorar OCR"""
    
    def __init__(self, resize_width: int = 1200, blur_kernel: Tuple[int, int] = (5, 5)):
        self.resize_width = resize_width
        self.blur_kernel = blur_kernel
    
    def clean_image(self, image) -> np.ndarray:

        if isinstance(image, Image.Image):
            img = np.array(image)
        else:
            img = image.copy()

        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        img = self._resize_image(img)

        # eliminar ruido suave
        img = cv2.fastNlMeansDenoising(
            img,
            None,
            h=15,
            templateWindowSize=7,
            searchWindowSize=21
        )

        # aumentar contraste
        clahe = cv2.createCLAHE(
            clipLimit=1.5,
            tileGridSize=(8,8)
        )

        img = clahe.apply(img)

        # umbral adaptativo
        img = cv2.adaptiveThreshold(
            img,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            15,
            8
        )
        #apertura morfológica para eliminar píxeles aislados
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)
        #cierre morfológico para rellenar huecos dentro de letras
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel_close)
        return img
    
    def _resize_image(self, image: np.ndarray) -> np.ndarray:
        """Redimensiona la imagen preservando la relación de aspecto"""
        height, width = image.shape[:2]
        if width > self.resize_width:
            scale = self.resize_width / width
            new_height = int(height * scale)
            image = cv2.resize(image, (self.resize_width, new_height))
        return image
    
    def enhance_contrast(self, image: np.ndarray, alpha: float = 1.5, beta: float = 0) -> np.ndarray:
        """
        Mejora el contraste de la imagen
        
        Args:
            image: Imagen de entrada
            alpha: Factor de contraste (>1 aumenta contraste)
            beta: Brillo
        
        Returns:
            Imagen con contraste mejorado
        """
        return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    
    def remove_shadows(self, image: np.ndarray) -> np.ndarray:
        """Intenta eliminar sombras de la imagen"""
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (8, 8))
        closing = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
        opening = cv2.morphologyEx(closing, cv2.MORPH_OPEN, kernel)
        return opening

def clean_image(image, resize_width: int = 1200) -> np.ndarray:
    """Función de conveniencia para limpiar una imagen"""
    cleaner = ImageCleaner(resize_width=resize_width)
    return cleaner.clean_image(image)