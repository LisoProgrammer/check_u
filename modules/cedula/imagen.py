"""
Preparacion de imagenes para lectura de cedulas.

Produce SIEMPRE dos imagenes con la MISMA geometria (mismo tamaño, misma
rotacion):

- `display`: a color, para mostrarla de fondo en la interfaz.
- `ocr`: en blanco y negro, binarizada, para pasarsela a Tesseract.

Que las dos compartan geometria es lo que permite dibujar sobre la
imagen de la interfaz los recuadros de donde el OCR saco cada dato: las
coordenadas que devuelve Tesseract sobre `ocr` valen tal cual sobre
`display`.

Por que no se usa directamente ImageCleaner de modules/ocr_module:

1. `ImageCleaner._resize_image` solo REDUCE (`if width > resize_width`).
   Las cedulas amarillas de prueba vienen de fotos/escaneos chicos
   (277-472 px de ancho para las dos caras juntas); dejarlas en su
   tamaño original es justamente lo que hace que el OCR falle. Aca se
   escala hacia ARRIBA tambien, que es lo que necesita ese material.
2. `ImageCleaner.clean_image` escribe un PDF de depuracion en disco en
   CADA llamada (`create_image_stage_pdf`). Para un flujo interactivo
   donde el usuario sube documentos y espera respuesta inmediata, eso
   es tiempo y basura en disco por cada pagina.
3. Se necesita aplicar la MISMA rotacion a la version a color, cosa que
   la clase original no expone.

No se modifica ImageCleaner (es codigo de otro integrante del equipo y
lo usa el resto del proyecto); se reimplementan aca los mismos pasos.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

# Ancho objetivo. Tesseract trabaja bien con texto de ~30 px de alto;
# con una cedula ocupando el ancho completo, 2000 px deja las letras
# chicas del reverso (estatura, RH, la linea de produccion) en un tamaño
# legible sin disparar el costo del OCR.
ANCHO_OBJETIVO = 2000

# Limite de ampliacion. Ampliar una imagen no agrega informacion que no
# estuviera ahi; pasado cierto punto solo agranda el ruido y hace todo
# mas lento. 6x es suficiente para llevar una foto de 350 px a ~2100.
MAX_ESCALA = 6.0


@dataclass
class ImagenPreparada:
    """Par de imagenes alineadas + metadatos de como se llego a ellas."""

    display: np.ndarray       # BGR, para mostrar
    ocr: np.ndarray           # binarizada, para Tesseract
    gris: np.ndarray          # gris ecualizada (sin binarizar), para PDF417
    ancho: int
    alto: int
    escala: float             # factor aplicado respecto al original
    angulo: float             # grados de inclinacion corregidos


def _a_bgr(imagen) -> np.ndarray:
    """PIL (RGB) o numpy -> numpy BGR de 3 canales."""
    if isinstance(imagen, Image.Image):
        arr = np.array(imagen.convert("RGB"))
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    arr = np.asarray(imagen)
    if arr.ndim == 2:
        return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    if arr.ndim == 3 and arr.shape[2] == 4:
        return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
    return arr.copy()


def _escalar(img_bgr: np.ndarray) -> tuple[np.ndarray, float]:
    """
    Lleva la imagen al ancho objetivo, ampliando o reduciendo segun haga
    falta. Devuelve (imagen, factor aplicado).
    """
    alto, ancho = img_bgr.shape[:2]
    if ancho == 0:
        return img_bgr, 1.0

    escala = ANCHO_OBJETIVO / float(ancho)
    escala = min(escala, MAX_ESCALA)

    if abs(escala - 1.0) < 0.02:
        return img_bgr, 1.0

    # INTER_CUBIC al ampliar (interpola suave, conserva bordes de letras);
    # INTER_AREA al reducir (promedia, evita aliasing).
    interpolacion = cv2.INTER_CUBIC if escala > 1 else cv2.INTER_AREA
    nuevo = cv2.resize(
        img_bgr,
        (int(round(ancho * escala)), int(round(alto * escala))),
        interpolation=interpolacion,
    )
    return nuevo, escala


def _binarizar(gris: np.ndarray) -> np.ndarray:
    """
    Mismos pasos que ImageCleaner (denoise -> blur -> CLAHE -> umbral
    adaptativo), que ya estaban ajustados por el equipo para estas
    cedulas.
    """
    sin_ruido = cv2.fastNlMeansDenoising(
        gris, None, h=15, templateWindowSize=7, searchWindowSize=21
    )
    suave = cv2.GaussianBlur(sin_ruido, (3, 3), 0)

    clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(8, 8))
    contraste = clahe.apply(suave)

    return cv2.adaptiveThreshold(
        contraste,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        19,
        3,
    )


def _detectar_angulo(binaria: np.ndarray) -> float:
    """
    Inclinacion del documento, en grados. Se usa el SkewDetector que ya
    existe en el repo; si falla por cualquier motivo se devuelve 0 (no
    corregir es preferible a romper el procesamiento por la inclinacion).
    """
    try:
        from modules.ocr_module.preprocess.check_inclination import SkewDetector

        return float(SkewDetector().detect_skew(binaria))
    except Exception:
        return 0.0


def _rotar(img: np.ndarray, angulo: float, borde) -> np.ndarray:
    alto, ancho = img.shape[:2]
    matriz = cv2.getRotationMatrix2D((ancho / 2.0, alto / 2.0), angulo, 1.0)
    return cv2.warpAffine(
        img,
        matriz,
        (ancho, alto),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=borde,
    )


def preparar(imagen, corregir_inclinacion: bool = True) -> ImagenPreparada:
    """
    Punto de entrada: recibe una pagina (PIL o numpy) y devuelve el par
    de imagenes alineadas listo para OCR y para mostrar.
    """
    bgr = _a_bgr(imagen)
    bgr, escala = _escalar(bgr)

    gris = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gris_eq = clahe.apply(gris)

    binaria = _binarizar(gris)

    angulo = _detectar_angulo(binaria) if corregir_inclinacion else 0.0

    # Solo rotar si la inclinacion es real y razonable: rotar por medio
    # grado no mejora el OCR y sí degrada la imagen por la interpolacion.
    if 0.5 < abs(angulo) <= 15.0:
        bgr = _rotar(bgr, angulo, (255, 255, 255))
        binaria = _rotar(binaria, angulo, 255)
        gris_eq = _rotar(gris_eq, angulo, 255)
    else:
        angulo = 0.0

    alto, ancho = binaria.shape[:2]

    return ImagenPreparada(
        display=bgr,
        ocr=binaria,
        gris=gris_eq,
        ancho=ancho,
        alto=alto,
        escala=escala,
        angulo=angulo,
    )
