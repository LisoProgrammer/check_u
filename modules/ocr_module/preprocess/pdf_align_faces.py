# modules/ocr_module/preprocess/export_aligned_pdf.py

"""
Exporta las caras de las cédulas de un PDF como un PDF multipágina,
aplicando corrección de inclinación a cada cara.

Estrategia actual:

    1. Se carga cada página del PDF.
    2. MultiFaceSkewDetector encuentra las caras.
    3. Cada cara conserva su margen.
    4. Se utiliza el ángulo detectado para esa cara.
    5. Se rota TODO el crop.
    6. NO se vuelve a recortar.
    7. Todas las caras corregidas se guardan como páginas de un PDF.

IMPORTANTE:
    En esta versión NO usamos warpPerspective.

Esto es deliberado: primero queremos comprobar que la rotación
simple funciona correctamente sin perder ningún borde ni contenido.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from modules.ocr_module.preprocess.check_inclination import (
    MultiFaceSkewDetector,
    ensure_cv_image,
)


# ================================================================
# RUTAS
# ================================================================

BASE_DIR = Path(__file__).resolve().parent

PDF_PATH = BASE_DIR / "test_data" / "cc_ejeml.pdf"

OUTPUT_DIR = BASE_DIR / "debug_faces"

OUTPUT_PDF_PATH = (
    OUTPUT_DIR / "cedulas_alineadas.pdf"
)


# ================================================================
# CONFIGURACIÓN
# ================================================================

MAX_FACES = 2

# Margen que se conserva alrededor de cada cara.
PADDING = 10

MAX_ANGLE = 15.0

CORRECTION_THRESHOLD = 1.0

# Resolución de lectura del PDF.
PDF_DPI = 200


# ================================================================
# CARGAR PDF
# ================================================================

def load_pdf_pages(
    pdf_path: Path,
):
    """
    Convierte las páginas del PDF en imágenes PIL.
    """

    from pdf2image import convert_from_path

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"No se encontró el PDF:\n{pdf_path}"
        )

    return convert_from_path(
        str(pdf_path),
        dpi=PDF_DPI,
    )


# ================================================================
# CONVERTIR A PIL
# ================================================================

def bgr_to_pil(
    image: np.ndarray,
) -> Image.Image:
    """
    Convierte una imagen OpenCV BGR a PIL RGB.
    """

    image = ensure_cv_image(
        image
    )

    rgb = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2RGB,
    )

    return Image.fromarray(
        rgb
    )


# ================================================================
# GUARDAR DEBUG
# ================================================================

def save_debug_image(
    path: Path,
    image: np.ndarray,
):
    """
    Guarda una imagen individual para inspección.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image = ensure_cv_image(
        image
    )

    success = cv2.imwrite(
        str(path),
        image,
    )

    if not success:
        raise RuntimeError(
            f"No se pudo guardar:\n{path}"
        )


# ================================================================
# ALINEAR UNA CARA
# ================================================================

def align_face(
    crop: np.ndarray,
    angle: float,
    detector: MultiFaceSkewDetector,
) -> np.ndarray:
    """
    Rota una cara completa.

    IMPORTANTE:

    - No detecta texto.
    - No usa Hough.
    - No hace perspectiva.
    - No recorta después de rotar.
    - Conserva el margen.
    """

    crop = ensure_cv_image(
        crop
    )

    return detector.correct_skew(
        crop,
        angle,
    )


# ================================================================
# EXPORTAR PDF
# ================================================================

def export_aligned_pdf(
    pdf_path: Path = PDF_PATH,
    output_pdf_path: Path = OUTPUT_PDF_PATH,
) -> Path:

    print("=" * 75)
    print("EXPORTACIÓN DE CÉDULAS ALINEADAS")
    print("=" * 75)

    print(
        f"\nPDF de entrada:\n{pdf_path}"
    )

    pages = load_pdf_pages(
        pdf_path
    )

    print(
        f"\nPáginas cargadas: "
        f"{len(pages)}"
    )

    # ------------------------------------------------------------
    # Detector
    # ------------------------------------------------------------

    detector = MultiFaceSkewDetector(
        max_angle=MAX_ANGLE,
        correction_threshold=CORRECTION_THRESHOLD,
        max_faces=MAX_FACES,
        padding=PADDING,
    )

    aligned_images: list[
        Image.Image
    ] = []

    # ------------------------------------------------------------
    # Procesar páginas
    # ------------------------------------------------------------

    for page_number, page in enumerate(
        pages,
        start=1,
    ):

        print("\n" + "=" * 75)
        print(
            f"PÁGINA {page_number}"
        )
        print("=" * 75)

        page_cv = ensure_cv_image(
            page
        )

        height, width = (
            page_cv.shape[:2]
        )

        print(
            f"Tamaño página: "
            f"{width} x {height}"
        )

        # --------------------------------------------------------
        # SEGMENTACIÓN
        # --------------------------------------------------------

        regions = detector.segment_faces(
            page_cv
        )

        print(
            f"Caras detectadas: "
            f"{len(regions)}"
        )

        if not regions:
            print(
                "⚠ No se detectaron caras."
            )
            continue

        # --------------------------------------------------------
        # CADA CARA
        # --------------------------------------------------------

        for face_number, region in enumerate(
            regions,
            start=1,
        ):

            crop = region.crop

            crop_height, crop_width = (
                crop.shape[:2]
            )

            print("\n" + "-" * 60)
            print(
                f"CARA {face_number}"
            )
            print("-" * 60)

            print(
                f"Crop: "
                f"{crop_width} x "
                f"{crop_height}"
            )

            print(
                f"BBox: "
                f"{region.bbox}"
            )

            print(
                f"Ángulo detectado: "
                f"{region.rect_angle:.4f}°"
            )

            # ----------------------------------------------------
            # ORIGINAL
            # ----------------------------------------------------

            original_path = (
                OUTPUT_DIR
                / (
                    f"page_{page_number}"
                    f"_face_{face_number}"
                    f"_original.png"
                )
            )

            save_debug_image(
                original_path,
                crop,
            )

            # ----------------------------------------------------
            # ALINEAR
            # ----------------------------------------------------

            aligned = align_face(
                crop,
                region.rect_angle,
                detector,
            )

            aligned_height, aligned_width = (
                aligned.shape[:2]
            )

            print(
                f"Resultado: "
                f"{aligned_width} x "
                f"{aligned_height}"
            )

            # ----------------------------------------------------
            # GUARDAR ALINEADA
            # ----------------------------------------------------

            aligned_path = (
                OUTPUT_DIR
                / (
                    f"page_{page_number}"
                    f"_face_{face_number}"
                    f"_aligned.png"
                )
            )

            save_debug_image(
                aligned_path,
                aligned,
            )

            print(
                f"Alineada guardada en:\n"
                f"{aligned_path}"
            )

            # ----------------------------------------------------
            # PIL
            # ----------------------------------------------------

            aligned_pil = bgr_to_pil(
                aligned
            )

            # Asegurar RGB.
            if aligned_pil.mode != "RGB":
                aligned_pil = (
                    aligned_pil.convert(
                        "RGB"
                    )
                )

            aligned_images.append(
                aligned_pil
            )

    # ============================================================
    # VALIDACIÓN
    # ============================================================

    if not aligned_images:
        raise RuntimeError(
            "No se detectó ninguna cara "
            "en el PDF."
        )

    # ============================================================
    # CREAR DIRECTORIO
    # ============================================================

    output_pdf_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ============================================================
    # CREAR PDF
    # ============================================================

    first = aligned_images[0]

    rest = aligned_images[1:]

    first.save(
        str(output_pdf_path),
        save_all=True,
        append_images=rest,
        resolution=float(PDF_DPI),
    )

    # ============================================================
    # RESULTADO
    # ============================================================

    print("\n" + "=" * 75)
    print("PROCESO TERMINADO")
    print("=" * 75)

    print(
        f"\nCaras exportadas: "
        f"{len(aligned_images)}"
    )

    print(
        f"\nPDF generado:\n"
        f"{output_pdf_path}"
    )

    return output_pdf_path


# ================================================================
# MAIN
# ================================================================

if __name__ == "__main__":

    export_aligned_pdf()