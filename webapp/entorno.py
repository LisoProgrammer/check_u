"""
Check_U - Verificador de entorno
--------------------------------
Revisa, ANTES de arrancar el servidor, que las dependencias externas
(las que no se instalan solo con pip, como Tesseract OCR) esten
disponibles. La idea es fallar aqui, con un mensaje claro y una
solucion concreta, en vez de que el usuario descubra a mitad de un
procesamiento (con una alerta del navegador) que falta algo.

Se puede correr por separado para diagnosticar sin levantar el
servidor:

    python webapp\\entorno.py
"""

import shutil
import sys


def verificar_entorno():
    """
    Devuelve una lista de problemas encontrados (vacia si todo esta
    bien). Cada problema es un dict con: componente, detalle, solucion.
    """
    problemas = []

    # ------------------------------------------------------------
    # Tesseract OCR: el motor que lee el texto de la imagen. Sin
    # esto no se puede procesar ningun documento.
    # ------------------------------------------------------------
    tesseract_path = shutil.which("tesseract")

    if not tesseract_path:
        problemas.append({
            "componente": "Tesseract OCR",
            "detalle": "No se encontro el ejecutable 'tesseract' en el PATH.",
            "solucion": (
                "Instala Tesseract OCR para Windows desde "
                "https://github.com/UB-Mannheim/tesseract/wiki y, durante la "
                "instalacion, marca la casilla 'Add to PATH'. Si ya lo "
                "instalaste, agrega manualmente su carpeta (normalmente "
                "C:\\Program Files\\Tesseract-OCR) a la variable de entorno "
                "PATH y abre una terminal nueva."
            ),
        })
    else:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
        except Exception as e:
            problemas.append({
                "componente": "Tesseract OCR",
                "detalle": f"Se encontro '{tesseract_path}' pero no se pudo ejecutar: {e}",
                "solucion": "Reinstala Tesseract OCR o revisa los permisos del archivo.",
            })
        else:
            try:
                idiomas = pytesseract.get_languages(config="")
            except Exception:
                idiomas = []

            if "spa" not in idiomas:
                problemas.append({
                    "componente": "Tesseract - paquete de idioma español",
                    "detalle": "Tesseract esta instalado pero falta el paquete de idioma 'spa'.",
                    "solucion": (
                        "Vuelve a correr el instalador de Tesseract y marca "
                        "'Spanish' en 'Additional language data', o descarga "
                        "spa.traineddata desde "
                        "https://github.com/tesseract-ocr/tessdata y colocalo "
                        "en la carpeta tessdata de tu instalacion (normalmente "
                        "C:\\Program Files\\Tesseract-OCR\\tessdata)."
                    ),
                })

    # ------------------------------------------------------------
    # Lectura de PDF: se necesita PyMuPDF (preferido, sin binarios
    # externos) o poppler (pdftoppm/pdfinfo) como respaldo.
    # ------------------------------------------------------------
    tiene_pymupdf = False
    try:
        import pymupdf  # noqa: F401
        tiene_pymupdf = True
    except ImportError:
        pass

    tiene_poppler = bool(shutil.which("pdftoppm") and shutil.which("pdfinfo"))

    if not tiene_pymupdf and not tiene_poppler:
        problemas.append({
            "componente": "Lectura de PDF",
            "detalle": "No se encontro PyMuPDF ni poppler (pdftoppm/pdfinfo) para leer archivos PDF.",
            "solucion": (
                "Con el venv activado, corre: pip install pymupdf "
                "(no necesita instalar nada mas en Windows, es la opcion "
                "recomendada)."
            ),
        })

    # ------------------------------------------------------------
    # Paquetes de Python. Si alguno falta, 'import' ya habria roto
    # app.py antes de llegar aqui, pero los listamos igual para dar
    # un mensaje mas claro que un traceback de Python.
    # ------------------------------------------------------------
    paquetes = ["cv2", "PIL", "flask", "requests", "pytesseract"]
    for paquete in paquetes:
        try:
            __import__(paquete)
        except ImportError:
            nombre_pip = {"cv2": "opencv-python", "PIL": "pillow"}.get(paquete, paquete)
            problemas.append({
                "componente": f"Paquete de Python: {paquete}",
                "detalle": f"No se pudo importar '{paquete}'.",
                "solucion": f"Con el venv activado, corre: pip install {nombre_pip}",
            })

    return problemas


def imprimir_reporte(problemas):
    ancho = 70
    print("=" * ancho)
    if not problemas:
        print("Check_U: verificacion de entorno OK, todo listo.")
        print("=" * ancho)
        return

    print("Check_U: se encontraron problemas con el entorno antes de arrancar")
    print("=" * ancho)
    for p in problemas:
        print(f"\n[FALTA] {p['componente']}")
        print(f"  Detalle:  {p['detalle']}")
        print(f"  Solucion: {p['solucion']}")
    print("\n" + "=" * ancho)
    print("Corrige lo anterior y vuelve a correr 'python webapp\\app.py'.")
    print("=" * ancho)


if __name__ == "__main__":
    problemas = verificar_entorno()
    imprimir_reporte(problemas)
    sys.exit(1 if problemas else 0)
