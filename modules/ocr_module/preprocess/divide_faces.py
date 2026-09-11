# modules/ocr_module/preprocess/divide_faces.py

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from modules.ocr_module.preprocess.check_inclination import (
    MultiFaceSkewDetector,
    ensure_cv_image,
)


BASE_DIR = Path(__file__).resolve().parent

PDF_PATH = BASE_DIR / "test_data" / "cc10.pdf"
DEBUG_DIR = BASE_DIR / "debug_faces"

MAX_FACES = 2
PADDING = 10

MAX_ANGLE = 15.0
CORRECTION_THRESHOLD = 1.0


def load_pdf_pages(pdf_path: Path):

    from pdf2image import convert_from_path

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"No se encontró el PDF:\n{pdf_path}"
        )

    return convert_from_path(
        str(pdf_path),
        dpi=200,
    )


def save_image(path: Path, image):

    image = ensure_cv_image(image)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not cv2.imwrite(str(path), image):
        raise RuntimeError(
            f"No se pudo guardar:\n{path}"
        )


def order_points(points):
    """
    Ordena cuatro puntos como:

        0 = arriba-izquierda
        1 = arriba-derecha
        2 = abajo-derecha
        3 = abajo-izquierda
    """

    points = np.array(points, dtype=np.float32)

    ordered = np.zeros((4, 2), dtype=np.float32)

    suma = points.sum(axis=1)
    diferencia = np.diff(points, axis=1).reshape(-1)

    ordered[0] = points[np.argmin(suma)]
    ordered[2] = points[np.argmax(suma)]

    ordered[1] = points[np.argmin(diferencia)]
    ordered[3] = points[np.argmax(diferencia)]

    return ordered


def detect_outer_rectangle(image):
    """
    Busca cuadriláteros grandes dentro del crop.

    Esta función es solamente de DIAGNÓSTICO.
    No modifica la segmentación.
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

        points = approx.reshape(4, 2)

        rect = cv2.minAreaRect(
            approx
        )

        (_, _), (rw, rh), raw_angle = rect

        if rw <= 0 or rh <= 0:
            continue

        ratio = max(rw, rh) / min(rw, rh)

        if not 1.25 <= ratio <= 2.0:
            continue

        candidates.append(
            {
                "area": area,
                "points": points,
                "ratio": ratio,
                "raw_angle": raw_angle,
                "rect": rect,
            }
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: x["area"],
        reverse=True,
    )

    return candidates[0]


def calculate_edge_angle(points):
    """
    Calcula el ángulo del borde superior directamente
    utilizando los cuatro vértices.
    """

    points = order_points(points)

    top_left = points[0]
    top_right = points[1]

    dx = float(top_right[0] - top_left[0])
    dy = float(top_right[1] - top_left[1])

    angle = np.degrees(
        np.arctan2(dy, dx)
    )

    return float(angle), points


def process_pdf():

    print("=" * 75)
    print("DIAGNÓSTICO DE INCLINACIÓN")
    print("=" * 75)

    print(f"\nPDF:")
    print(PDF_PATH)

    pages = load_pdf_pages(
        PDF_PATH
    )

    print(
        f"\nPDF cargado correctamente. "
        f"Imágenes/páginas: {len(pages)}"
    )

    DEBUG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    detector = MultiFaceSkewDetector(
        max_angle=MAX_ANGLE,
        correction_threshold=CORRECTION_THRESHOLD,
        max_faces=MAX_FACES,
        padding=PADDING,
    )

    for page_number, page in enumerate(
        pages,
        start=1,
    ):

        print("\n" + "=" * 75)
        print(f"PÁGINA {page_number}")
        print("=" * 75)

        page_cv = ensure_cv_image(page)

        height, width = page_cv.shape[:2]

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
            f"\nCaras detectadas: "
            f"{len(regions)}"
        )

        for face_number, region in enumerate(
            regions,
            start=1,
        ):

            print("\n" + "-" * 75)
            print(f"CARA {face_number}")
            print("-" * 75)

            crop = region.crop

            h, w = crop.shape[:2]

            print(
                f"Tamaño recorte: "
                f"{w} x {h}"
            )

            print(
                f"BBox: "
                f"{region.bbox}"
            )

            # ====================================================
            # ÁNGULO QUE ACTUALMENTE USA EL DETECTOR
            # ====================================================

            print(
                f"\nÁngulo rectángulo actual: "
                f"{region.rect_angle:.4f}°"
            )

            # ====================================================
            # BUSCAR CUADRILÁTERO EXTERIOR
            # ====================================================

            candidate = detect_outer_rectangle(
                crop
            )

            if candidate is None:

                print(
                    "\n❌ No se encontró "
                    "un cuadrilátero exterior."
                )

                corrected = crop.copy()

            else:

                points = candidate["points"]

                raw_angle = candidate[
                    "raw_angle"
                ]

                ratio = candidate[
                    "ratio"
                ]

                area = candidate[
                    "area"
                ]

                edge_angle, ordered = (
                    calculate_edge_angle(
                        points
                    )
                )

                print(
                    "\nCUADRILÁTERO DETECTADO"
                )

                print(
                    f"Área: "
                    f"{area:.2f}"
                )

                print(
                    f"Ratio: "
                    f"{ratio:.4f}"
                )

                print(
                    f"Ángulo raw minAreaRect: "
                    f"{raw_angle:.4f}°"
                )

                print(
                    "\nPUNTOS DETECTADOS:"
                )

                labels = [
                    "arriba-izquierda",
                    "arriba-derecha",
                    "abajo-derecha",
                    "abajo-izquierda",
                ]

                for label, point in zip(
                    labels,
                    ordered,
                ):

                    print(
                        f"  {label}: "
                        f"({point[0]:.2f}, "
                        f"{point[1]:.2f})"
                    )

                print(
                    f"\nÁngulo BORDE SUPERIOR: "
                    f"{edge_angle:.4f}°"
                )

                # =================================================
                # DIBUJAR EL RECTÁNGULO DETECTADO
                # =================================================

                debug = crop.copy()

                polygon = (
                    ordered
                    .astype(np.int32)
                    .reshape((-1, 1, 2))
                )

                cv2.polylines(
                    debug,
                    [polygon],
                    True,
                    (0, 0, 255),
                    3,
                )

                for i, point in enumerate(
                    ordered
                ):

                    x = int(point[0])
                    y = int(point[1])

                    cv2.circle(
                        debug,
                        (x, y),
                        8,
                        (255, 0, 0),
                        -1,
                    )

                    cv2.putText(
                        debug,
                        str(i),
                        (x + 10, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 0),
                        2,
                    )

                debug_path = (
                    DEBUG_DIR
                    / (
                        f"page_{page_number}"
                        f"_face_{face_number}"
                        f"_geometry.png"
                    )
                )

                save_image(
                    debug_path,
                    debug,
                )

                print(
                    "\nGeometría marcada guardada en:"
                )

                print(
                    debug_path
                )

                # =================================================
                # PROBAR CORRECCIÓN
                # =================================================

                corrected = detector.correct_skew(
                    crop,
                    edge_angle,
                )

                print(
                    f"\nÁngulo utilizado para "
                    f"corrección: "
                    f"{edge_angle:.4f}°"
                )

            # ====================================================
            # GUARDAR ORIGINAL
            # ====================================================

            original_path = (
                DEBUG_DIR
                / (
                    f"page_{page_number}"
                    f"_face_{face_number}"
                    f"_original.png"
                )
            )

            save_image(
                original_path,
                crop,
            )

            # ====================================================
            # GUARDAR CORREGIDA
            # ====================================================

            corrected_path = (
                DEBUG_DIR
                / (
                    f"page_{page_number}"
                    f"_face_{face_number}"
                    f"_corrected.png"
                )
            )

            save_image(
                corrected_path,
                corrected,
            )

            print(
                "\nOriginal:"
            )
            print(
                original_path
            )

            print(
                "\nCorregida:"
            )
            print(
                corrected_path
            )

    print("\n" + "=" * 75)
    print("DIAGNÓSTICO TERMINADO")
    print("=" * 75)


if __name__ == "__main__":
    process_pdf()