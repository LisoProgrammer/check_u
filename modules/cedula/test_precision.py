"""
Medicion de precision de la lectura de cedulas.

Se apoya en que los archivos de prueba estan nombrados
"<numero>_<APELLIDOS>_<NOMBRES>.pdf", asi que el nombre del archivo
sirve como respuesta correcta y la precision se puede medir sola, sin
tener que revisar a mano cada resultado.

Uso:
    python -m modules.cedula.test_precision <carpeta> [<carpeta> ...]

Los archivos que no siguen esa convencion se procesan igual, pero solo
se reporta lo que se extrajo (no se puede puntuar).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from modules.cedula.lectura import leer_cedula  # noqa: E402
from modules.cedula.similitud import comparar_nombres, normalizar  # noqa: E402


def cargar_paginas(ruta: Path):
    from PIL import Image

    if ruta.suffix.lower() == ".pdf":
        import pymupdf

        doc = pymupdf.open(ruta)
        paginas = []
        for pagina in doc:
            pix = pagina.get_pixmap(
                matrix=pymupdf.Matrix(200 / 72, 200 / 72),
                colorspace=pymupdf.csRGB,
                alpha=False,
            )
            paginas.append(
                Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            )
        doc.close()
        return paginas

    return [Image.open(ruta).convert("RGB")]


def esperado_desde_nombre(ruta: Path):
    partes = ruta.stem.split("_")
    if len(partes) < 2 or not partes[0].isdigit():
        return None, None
    return partes[0], " ".join(partes[1:])


def main(carpetas: list[str]) -> int:
    archivos: list[Path] = []
    for carpeta in carpetas:
        base = Path(carpeta)
        if base.is_file():
            archivos.append(base)
        else:
            archivos.extend(sorted(base.glob("*.pdf")))
            archivos.extend(sorted(base.glob("*.png")))
            archivos.extend(sorted(base.glob("*.jpg")))

    if not archivos:
        print("No se encontraron archivos.")
        return 1

    total = puntuables = numeros_ok = nombres_ok = 0

    print(f"{'archivo':46} {'formato':22} {'numero':>12} {'num':>4} {'nombre %':>9}")
    print("-" * 100)

    for ruta in archivos:
        total += 1
        try:
            resultado = leer_cedula(cargar_paginas(ruta))
        except Exception as e:
            print(f"{ruta.name[:45]:46} ERROR: {e}")
            continue

        numero = (resultado.campos["numero_documento"] or {}).get("valor")
        nombre = (resultado.campos["nombre_completo"] or {}).get("valor")

        numero_esperado, nombre_esperado = esperado_desde_nombre(ruta)

        marca_numero = ""
        similitud = ""

        if numero_esperado:
            puntuables += 1
            acierto = (numero or "").lstrip("0") == numero_esperado.lstrip("0")
            numeros_ok += int(acierto)
            marca_numero = "OK" if acierto else "no"

            comparacion = comparar_nombres(nombre, nombre_esperado)
            similitud = f"{comparacion.similitud:.0f}"
            nombres_ok += int(bool(comparacion.coincide))

        print(
            f"{ruta.name[:45]:46} {resultado.formato_nombre[:21]:22} "
            f"{(numero or '-'):>12} {marca_numero:>4} {similitud:>9}"
        )
        if nombre:
            print(f"{'':46} nombre: {normalizar(nombre)}")
        if nombre_esperado:
            print(f"{'':46} real:   {normalizar(nombre_esperado)}")

    print("-" * 100)
    print(f"Documentos procesados: {total}")
    if puntuables:
        print(
            f"Numero correcto:  {numeros_ok}/{puntuables} "
            f"({numeros_ok / puntuables * 100:.0f} %)"
        )
        print(
            f"Nombre >= 85 %:   {nombres_ok}/{puntuables} "
            f"({nombres_ok / puntuables * 100:.0f} %)"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or ["test_samples"]))
