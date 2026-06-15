# preprocess/check_inclination.py
import cv2
import numpy as np
from typing import Tuple

class SkewDetector:
    """Detecta y corrige la inclinación (skew) en documentos escaneados"""
    
    def __init__(self, max_angle: float = 15):
        self.max_angle = max_angle
    
    def detect_skew(self, image: np.ndarray) -> float:
        """
        Detecta el ángulo de inclinación usando Hough Transform
        
        Args:
            image: Imagen en escala de grises o binarizada
        
        Returns:
            Ángulo de inclinación en grados (negativo = anti-horario)
        """
        # Asegurar que es binarizada
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Aplicar umbral
        _, binary = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
        
        # Encontrar líneas usando Hough
        lines = cv2.HoughLines(binary, 1, np.pi/180, 100)
        
        if lines is None or len(lines) == 0:
            return 0.0
        
        # Calcular ángulos
        angles = []
        for line in lines:
            rho, theta = line[0]
            angle = np.degrees(theta) - 90
            
            # Normalizar ángulo entre -90 y 90
            if angle > 45:
                angle -= 90
            if angle < -45:
                angle += 90
            
            angles.append(angle)
        
        # Usar la mediana de los ángulos
        if angles:
            skew_angle = np.median(angles)
            return float(skew_angle)
        
        return 0.0
    
    def correct_skew(self, image: np.ndarray, angle: float = None) -> Tuple[np.ndarray, float]:
        """
        Corrige la inclinación de la imagen
        
        Args:
            image: Imagen de entrada
            angle: Ángulo de corrección. Si es None, se detecta automáticamente
        
        Returns:
            Tupla (imagen_corregida, ángulo_detectado)
        """
        if angle is None:
            angle = self.detect_skew(image)
        
        # Limitar el ángulo máximo
        if abs(angle) > self.max_angle:
            angle = np.sign(angle) * self.max_angle
        
        if abs(angle) < 0.5:  # Muy pequeño, no corregir
            return image, angle
        
        # Obtener altura y ancho
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        
        # Calcular matriz de rotación
        rotation_matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)
        
        # Aplicar rotación
        corrected = cv2.warpAffine(
            image, rotation_matrix, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        
        return corrected, angle
    
    def auto_correct(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Detecta y corrige automáticamente la inclinación
        
        Args:
            image: Imagen de entrada
        
        Returns:
            Tupla (imagen_corregida, ángulo_detectado)
        """
        angle = self.detect_skew(image)
        corrected, final_angle = self.correct_skew(image, angle)
        return corrected, final_angle

def detect_and_correct_skew(image: np.ndarray, max_angle: float = 15) -> Tuple[np.ndarray, float]:
    """Función de conveniencia para detectar y corregir inclinación"""
    detector = SkewDetector(max_angle=max_angle)
    return detector.auto_correct(image)