# modules/ocr_module/preprocess/check_inclination.py

from __future__ import annotations

from typing import NamedTuple

import cv2
import numpy as np


# ================================================================
# ESTRUCTURA DE UNA CARA
# ================================================================

class FaceRegion(NamedTuple):
    crop: np.ndarray
    bbox: tuple[int, int, int, int]
    rect_angle: float


# ================================================================
# UTILIDADES
# ================================================================

def ensure_cv_image(image) -> np.ndarray:
    """
    Convierte una imagen PIL o NumPy a formato OpenCV BGR.
    """

    if isinstance(image, np.ndarray):

        if image.ndim == 2:
            return cv2.cvtColor(
                image,
                cv2.COLOR_GRAY2BGR,
            )

        if image.ndim == 3:

            if image.shape[2] == 4:
                return cv2.cvtColor(
                    image,
                    cv2.COLOR_BGRA2BGR,
                )

            return image.copy()

        raise ValueError(
            f"Formato de imagen no soportado: {image.shape}"
        )

    try:
        from PIL import Image

        if isinstance(image, Image.Image):

            image = np.array(image)

            if image.ndim == 2:
                return cv2.cvtColor(
                    image,
                    cv2.COLOR_GRAY2BGR,
                )

            if image.shape[2] == 4:
                return cv2.cvtColor(
                    image,
                    cv2.COLOR_RGBA2BGR,
                )

            return cv2.cvtColor(
                image,
                cv2.COLOR_RGB2BGR,
            )

    except ImportError:
        pass

    raise TypeError(
        "La imagen debe ser numpy.ndarray o PIL.Image.Image"
    )


# ================================================================
# DETECTOR BASE
# ================================================================

class SkewDetector:
    """
    Detector y corrector de inclinación.

    La inclinación se calcula a partir de la geometría exterior
    del documento, no a partir de las líneas internas del texto.
    """

    def __init__(
        self,
        max_angle: float = 15.0,
        correction_threshold: float = 1.0,
    ):
        self.max_angle = max_angle
        self.correction_threshold = correction_threshold

    # ------------------------------------------------------------
    # NORMALIZAR ANGULO DE minAreaRect
    # ------------------------------------------------------------

    def _normalize_rect_angle(self, rect) -> float:
        """
        Convierte el ángulo de cv2.minAreaRect() en el ángulo
        del lado largo del documento.

        minAreaRect puede devolver valores cercanos a 90° aunque
        el documento esté prácticamente horizontal.

        Ejemplos:

            89.47  -> -0.53
            -86.49 ->  3.51
        """

        (_, _), (width, height), angle = rect

        # Si width representa el lado corto, el lado largo
        # está desplazado 90 grados.
        if width < height:
            angle += 90.0

        # Normalizar a [-45, 45].
        while angle > 45.0:
            angle -= 90.0

        while angle < -45.0:
            angle += 90.0

        return float(angle)

    # ------------------------------------------------------------
    # DETECTAR INCLINACION
    # ------------------------------------------------------------

    def detect_skew(self, image: np.ndarray) -> float:
        """
        Detecta la inclinación de una única cara.

        Busca un contorno grande y calcula su minAreaRect().
        """

        image = ensure_cv_image(image)

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        blurred = cv2.GaussianBlur(
            gray,
            (5, 5),
            0,
        )

        edges = cv2.Canny(
            blurred,
            50,
            150,
        )

        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_LIST,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        if not contours:
            return 0.0

        h, w = gray.shape[:2]
        image_area = float(w * h)

        candidates = []

        for contour in contours:

            area = cv2.contourArea(contour)

            if area < image_area * 0.15:
                continue

            perimeter = cv2.arcLength(
                contour,
                True,
            )

            if perimeter <= 0:
                continue

            approx = cv2.approxPolyDP(
                contour,
                0.02 * perimeter,
                True,
            )

            if len(approx) != 4:
                continue

            if not cv2.isContourConvex(approx):
                continue

            rect = cv2.minAreaRect(
                approx
            )

            (_, _), (rw, rh), _ = rect

            if rw <= 0 or rh <= 0:
                continue

            ratio = max(rw, rh) / min(rw, rh)

            # Relación aproximada de una cédula.
            if not 1.25 <= ratio <= 2.0:
                continue

            angle = self._normalize_rect_angle(
                rect
            )

            candidates.append(
                (
                    area,
                    angle,
                )
            )

        if not candidates:
            return 0.0

        # El contorno más grande tiene prioridad.
        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return float(
            candidates[0][1]
        )

    # ------------------------------------------------------------
    # CORREGIR INCLINACION
    # ------------------------------------------------------------

    def correct_skew(
        self,
        image: np.ndarray,
        angle: float,
    ) -> np.ndarray:
        """
        Rota TODO el crop conservando sus dimensiones.

        No vuelve a recortar después de rotar.
        """

        image = ensure_cv_image(image)

        # No corregir inclinaciones insignificantes.
        if abs(angle) < self.correction_threshold:
            return image.copy()

        # Seguridad.
        if abs(angle) > self.max_angle:
            return image.copy()

        h, w = image.shape[:2]

        center = (
            w / 2.0,
            h / 2.0,
        )

        # El ángulo utilizado aquí corresponde al ángulo
        # geométrico calculado sobre los puntos de la imagen.
        rotation_matrix = cv2.getRotationMatrix2D(
            center,
            angle,
            1.0,
        )

        corrected = cv2.warpAffine(
            image,
            rotation_matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )

        return corrected

    # ------------------------------------------------------------
    # DETECCION + CORRECCION
    # ------------------------------------------------------------

    def auto_correct(
        self,
        image: np.ndarray,
    ) -> tuple[np.ndarray, float]:

        image = ensure_cv_image(image)

        angle = self.detect_skew(
            image
        )

        corrected = self.correct_skew(
            image,
            angle,
        )

        return corrected, angle


# ================================================================
# DETECTOR MULTICARA
# ================================================================

class MultiFaceSkewDetector(SkewDetector):
    """
    Detector para páginas que contienen varias cédulas.
    """

    def __init__(
        self,
        max_angle: float = 15.0,
        correction_threshold: float = 1.0,
        max_faces: int = 2,
        padding: int = 10,
    ):

        super().__init__(
            max_angle=max_angle,
            correction_threshold=correction_threshold,
        )

        self.max_faces = max_faces
        self.padding = padding

    # ============================================================
    # SEGMENTAR CARAS
    # ============================================================

    def segment_faces(
        self,
        image: np.ndarray,
    ) -> list[FaceRegion]:
        """
        Segmenta las diferentes caras/cédulas de una página.

        IMPORTANTE:
        Este método pertenece a MultiFaceSkewDetector.

        El padding se conserva para permitir corregir posteriormente
        la inclinación sin cortar los bordes del documento.
        """

        image = ensure_cv_image(
            image
        )

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        h, w = gray.shape

        # --------------------------------------------------------
        # Umbral adaptativo basado en OTSU
        # --------------------------------------------------------

        blurred = cv2.GaussianBlur(
            gray,
            (5, 5),
            0,
        )

        _, threshold = cv2.threshold(
            blurred,
            0,
            255,
            cv2.THRESH_BINARY_INV
            + cv2.THRESH_OTSU,
        )

        # --------------------------------------------------------
        # Conectar elementos pertenecientes a una misma cédula.
        # --------------------------------------------------------

        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (15, 15),
        )

        threshold = cv2.morphologyEx(
            threshold,
            cv2.MORPH_CLOSE,
            kernel,
            iterations=2,
        )

        # --------------------------------------------------------
        # Dilatación moderada
        # --------------------------------------------------------

        kernel_dilate = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (11, 11),
        )

        threshold = cv2.dilate(
            threshold,
            kernel_dilate,
            iterations=1,
        )

        # --------------------------------------------------------
        # Contornos
        # --------------------------------------------------------

        contours, _ = cv2.findContours(
            threshold,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        page_area = float(
            w * h
        )

        candidates = []

        for contour in contours:

            area = cv2.contourArea(
                contour
            )

            # Ignorar ruido.
            if area < page_area * 0.003:
                continue

            x, y, bw, bh = cv2.boundingRect(
                contour
            )

            if bw <= 0 or bh <= 0:
                continue

            bbox_area = float(
                bw * bh
            )

            # Evitar seleccionar toda la hoja.
            if bbox_area > page_area * 0.80:
                continue

            ratio = bw / float(bh)

            # La cédula es horizontal.
            if not 1.15 <= ratio <= 2.5:
                continue

            candidates.append(
                (
                    area,
                    contour,
                    (x, y, bw, bh),
                )
            )

        # --------------------------------------------------------
        # Orden vertical.
        # --------------------------------------------------------

        candidates.sort(
            key=lambda item: item[2][1]
        )

        # Limitar número de caras.
        candidates = candidates[
            : self.max_faces
        ]

        regions = []

        # ========================================================
        # CREAR CROP DE CADA CARA
        # ========================================================

        for area, contour, bbox in candidates:

            x, y, bw, bh = bbox

            # ----------------------------------------------------
            # Orientación de la región.
            #
            # Esto NO usa Hough.
            # ----------------------------------------------------

            rect = cv2.minAreaRect(
                contour
            )

            rect_angle = self._normalize_rect_angle(
                rect
            )

            # ----------------------------------------------------
            # Padding
            # ----------------------------------------------------

            x1 = max(
                0,
                x - self.padding,
            )

            y1 = max(
                0,
                y - self.padding,
            )

            x2 = min(
                w,
                x + bw + self.padding,
            )

            y2 = min(
                h,
                y + bh + self.padding,
            )

            crop = image[
                y1:y2,
                x1:x2,
            ].copy()

            regions.append(
                FaceRegion(
                    crop=crop,
                    bbox=(
                        x1,
                        y1,
                        x2 - x1,
                        y2 - y1,
                    ),
                    rect_angle=rect_angle,
                )
            )

        return regions


# ================================================================
# FUNCION AUXILIAR
# ================================================================

def detect_and_correct_skew(
    image: np.ndarray,
    max_angle: float = 15.0,
    correction_threshold: float = 1.0,
) -> tuple[np.ndarray, float]:

    detector = SkewDetector(
        max_angle=max_angle,
        correction_threshold=correction_threshold,
    )

    return detector.auto_correct(
        image
    )