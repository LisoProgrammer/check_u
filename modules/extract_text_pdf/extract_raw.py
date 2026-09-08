"""
Script simple para ver el texto crudo que se extrae de un PDF,
usando dos librerías distintas para comparar.

Uso:
    python extract_raw.py ruta/al/archivo.pdf
"""

import sys


def extract_with_pypdf(path: str) -> str:
    import pypdf

    reader = pypdf.PdfReader(path)
    text = ""

    for i, page in enumerate(reader.pages):
        text += f"\n--- Página {i+1} (pypdf) ---\n"
        text += page.extract_text() or ""

    return text


def extract_with_pdfplumber(path: str) -> str:
    import pdfplumber

    text = ""

    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text += f"\n--- Página {i+1} (pdfplumber) ---\n"
            text += page.extract_text() or ""

    return text


def main():
    if len(sys.argv) < 2:
        print("Uso: python extract_raw.py ruta/al/archivo.pdf")
        sys.exit(1)

    path = sys.argv[1]

    print("=" * 60)
    print("TEXTO CON pypdf")
    print("=" * 60)
    try:
        print(extract_with_pypdf(path))
    except Exception as e:
        print(f"Error con pypdf: {e}")

    print("\n" + "=" * 60)
    print("TEXTO CON pdfplumber")
    print("=" * 60)
    try:
        print(extract_with_pdfplumber(path))
    except Exception as e:
        print(f"Error con pdfplumber: {e}")


if __name__ == "__main__":
    main()