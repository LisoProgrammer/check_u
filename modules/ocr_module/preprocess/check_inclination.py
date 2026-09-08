# preprocess/check_inclination.py

import cv2
import numpy as np
from typing import Tuple


class SkewDetector:
    """Detecta y corrige la inclinación de documentos para OCR."""

    def __init__(
        self,
        max_angle: float = 15.0,
        correction_threshold: float = 1.0
    ):
        self.max_angle = max_angle
        self.correction_threshold = correction_threshold

    def detect_skew(self, image: np.ndarray) -> float:
        """
        Detecta la inclinación usando HoughLinesP.

        Se consideran únicamente líneas casi horizontales,
        ya que son las más útiles para determinar el skew
        del texto de un documento.

        Returns:
            Ángulo detectado en grados.
        """

        # --------------------------------------------------
        # 1. Escala de grises
        # --------------------------------------------------

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # --------------------------------------------------
        # 2. Binarización
        # --------------------------------------------------

        # Texto oscuro -> blanco
        _, binary = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        # --------------------------------------------------
        # 3. Reducir ruido pequeño
        # --------------------------------------------------

        kernel = np.ones((2, 2), np.uint8)

        binary = cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            kernel
        )

        # --------------------------------------------------
        # 4. Detectar segmentos de línea
        # --------------------------------------------------

        lines = cv2.HoughLinesP(
            binary,
            rho=1,
            theta=np.pi / 1800,
            threshold=50,
            minLineLength=50,
            maxLineGap=10
        )

        if lines is None:
            return 0.0

        # --------------------------------------------------
        # 5. Analizar solamente líneas horizontales
        # --------------------------------------------------

        candidates = []

        for line in lines:

            x1, y1, x2, y2 = line[0]

            dx = x2 - x1
            dy = y2 - y1

            # Ignorar líneas verticales
            if dx == 0:
                continue

            angle = np.degrees(
                np.arctan2(dy, dx)
            )

            length = np.sqrt(
                dx ** 2 + dy ** 2
            )

            # Solo líneas aproximadamente horizontales
            if -10.0 <= angle <= 10.0:

                candidates.append(
                    (float(angle), float(length))
                )

        if not candidates:
            return 0.0

        # --------------------------------------------------
        # 6. Eliminar líneas demasiado cortas
        # --------------------------------------------------

        candidates = [
            (angle, length)
            for angle, length in candidates
            if length >= 50
        ]

        if not candidates:
            return 0.0

        # --------------------------------------------------
        # 7. Ordenar por longitud
        # --------------------------------------------------

        candidates.sort(
            key=lambda x: x[1],
            reverse=True
        )

        # Tomamos las líneas más representativas
        selected = candidates[:20]

        # --------------------------------------------------
        # 8. Mediana ponderada por longitud
        # --------------------------------------------------

        angles = np.array(
            [angle for angle, _ in selected],
            dtype=np.float64
        )

        lengths = np.array(
            [length for _, length in selected],
            dtype=np.float64
        )

        # Repetimos los ángulos proporcionalmente
        # a su importancia relativa.
        weights = lengths / lengths.sum()

        # Media ponderada
        skew_angle = np.sum(
            angles * weights
        )

        # --------------------------------------------------
        # 9. Limitar resultados absurdos
        # --------------------------------------------------

        if abs(skew_angle) > self.max_angle:
            return 0.0

        return float(skew_angle)

    def correct_skew(
        self,
        image: np.ndarray,
        angle: float = None
    ) -> Tuple[np.ndarray, float]:
        """
        Detecta y corrige la inclinación.
        """

        if angle is None:
            angle = self.detect_skew(image)

        # --------------------------------------------------
        # No corregir inclinaciones pequeñas
        # --------------------------------------------------

        if abs(angle) < self.correction_threshold:
            return image, 0.0

        # --------------------------------------------------
        # Limitar ángulo
        # --------------------------------------------------

        angle = np.clip(
            angle,
            -self.max_angle,
            self.max_angle
        )

        # --------------------------------------------------
        # Dimensiones
        # --------------------------------------------------

        h, w = image.shape[:2]

        center = (
            w / 2.0,
            h / 2.0
        )

        # --------------------------------------------------
        # Matriz de rotación
        # --------------------------------------------------

        rotation_matrix = cv2.getRotationMatrix2D(
            center,
            -angle,
            1.0
        )

        # --------------------------------------------------
        # Rotación
        # --------------------------------------------------

        corrected = cv2.warpAffine(
            image,
            rotation_matrix,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE
        )

        return corrected, float(angle)

    def auto_correct(
        self,
        image: np.ndarray
    ) -> Tuple[np.ndarray, float]:
        """
        Detecta y corrige automáticamente la inclinación.
        """

        angle = self.detect_skew(image)

        corrected, final_angle = self.correct_skew(
            image,
            angle
        )

        return corrected, final_angle


def detect_and_correct_skew(
    image: np.ndarray,
    max_angle: float = 15.0
) -> Tuple[np.ndarray, float]:
    """
    Función de conveniencia.
    """

    detector = SkewDetector(
        max_angle=max_angle,
        correction_threshold=1.0
    )

    return detector.auto_correct(image)