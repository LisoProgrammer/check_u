"""
Lectura del codigo de barras PDF417 del reverso de la cedula amarilla
con hologramas.

Es la fuente MAS confiable para este formato: mientras el texto impreso
hay que adivinarlo con OCR (y se equivoca con fotos borrosas, sellos
encima o poca luz), el PDF417 trae los datos codificados digitalmente y
con correccion de errores, asi que o se lee bien o no se lee -- nunca
devuelve un numero "casi correcto".

Estructura (531 bytes, posiciones fijas). La cedula digital de
policarbonato NO usa este codigo (usa MRZ + QR), por eso este modulo
solo aplica al formato amarillo.

Limitacion conocida: el PDF417 necesita resolucion. En fotos de menos de
~1000 px de ancho las barras se funden entre si y el decodificador no
puede reconstruirlo; en esos casos esta funcion devuelve None y la
lectura cae al OCR, que es justamente para lo que existe el respaldo.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Posiciones de cada campo dentro de los 531 bytes del codigo.
# Los campos de texto vienen rellenados a la derecha con bytes nulos.
_CAMPOS = {
    "codigo_afis": (2, 10),
    "tarjeta_huella": (40, 48),
    "numero_documento": (48, 58),
    "primer_apellido": (58, 81),
    "segundo_apellido": (81, 104),
    "primer_nombre": (104, 127),
    "segundo_nombre": (127, 150),
    "sexo": (151, 152),
    "anio_nacimiento": (152, 156),
    "mes_nacimiento": (156, 158),
    "dia_nacimiento": (158, 160),
    "codigo_municipio": (160, 162),
    "codigo_departamento": (162, 165),
    "rh": (166, 168),
}

LARGO_MINIMO = 170  # hasta donde llegan los campos que nos interesan


@dataclass
class DatosPDF417:
    numero_documento: str
    nombre_completo: str
    primer_apellido: str
    segundo_apellido: str
    primer_nombre: str
    segundo_nombre: str
    sexo: str
    fecha_nacimiento: str | None
    rh: str
    caja: dict | None      # donde estaba el codigo dentro de la imagen
    pagina: int = 0        # en que pagina del documento estaba


def _texto(crudo: bytes, desde: int, hasta: int) -> str:
    trozo = crudo[desde:hasta]
    # Relleno con nulos y, en algunas impresiones, con espacios.
    return trozo.replace(b"\x00", b" ").decode("latin-1", errors="ignore").strip()


def _parsear(crudo: bytes, caja: dict | None) -> DatosPDF417 | None:
    if len(crudo) < LARGO_MINIMO:
        return None

    numero = _texto(crudo, *_CAMPOS["numero_documento"])
    numero = "".join(c for c in numero if c.isdigit()).lstrip("0")

    if not numero or len(numero) < 6:
        return None

    primer_apellido = _texto(crudo, *_CAMPOS["primer_apellido"])
    segundo_apellido = _texto(crudo, *_CAMPOS["segundo_apellido"])
    primer_nombre = _texto(crudo, *_CAMPOS["primer_nombre"])
    segundo_nombre = _texto(crudo, *_CAMPOS["segundo_nombre"])

    # Un PDF417 bien leido siempre trae al menos un apellido y un nombre
    # en letras. Si no, lo mas probable es que sea otro codigo de barras
    # o una variante de formato que este parseo no cubre: mejor devolver
    # None y dejar que el OCR haga el trabajo, que entregar basura.
    if not primer_apellido.replace(" ", "").isalpha():
        return None
    if not primer_nombre.replace(" ", "").isalpha():
        return None

    sexo = _texto(crudo, *_CAMPOS["sexo"]).upper()
    sexo = sexo if sexo in ("M", "F") else ""

    fecha = None
    anio = _texto(crudo, *_CAMPOS["anio_nacimiento"])
    mes = _texto(crudo, *_CAMPOS["mes_nacimiento"])
    dia = _texto(crudo, *_CAMPOS["dia_nacimiento"])
    if anio.isdigit() and mes.isdigit() and dia.isdigit():
        if 1900 <= int(anio) <= 2100 and 1 <= int(mes) <= 12 and 1 <= int(dia) <= 31:
            fecha = f"{int(dia):02d}/{int(mes):02d}/{int(anio)}"

    nombres = " ".join(x for x in (primer_nombre, segundo_nombre) if x)
    apellidos = " ".join(x for x in (primer_apellido, segundo_apellido) if x)

    return DatosPDF417(
        numero_documento=numero,
        nombre_completo=f"{nombres} {apellidos}".strip(),
        primer_apellido=primer_apellido,
        segundo_apellido=segundo_apellido,
        primer_nombre=primer_nombre,
        segundo_nombre=segundo_nombre,
        sexo=sexo,
        fecha_nacimiento=fecha,
        rh=_texto(crudo, *_CAMPOS["rh"]),
        caja=caja,
    )


def _caja_de_posicion(posicion) -> dict | None:
    try:
        puntos = [
            posicion.top_left,
            posicion.top_right,
            posicion.bottom_right,
            posicion.bottom_left,
        ]
        xs = [p.x for p in puntos]
        ys = [p.y for p in puntos]
        return {
            "x": int(min(xs)),
            "y": int(min(ys)),
            "ancho": int(max(xs) - min(xs)),
            "alto": int(max(ys) - min(ys)),
        }
    except Exception:
        return None


def leer(imagen_gris: np.ndarray) -> DatosPDF417 | None:
    """
    Intenta decodificar un PDF417 en la imagen. Devuelve None si no hay
    ninguno legible (caso muy comun con fotos de baja resolucion).

    Se prueban varias versiones de la imagen porque el decodificador es
    sensible al contraste y al tamaño de las barras: la original, una
    ampliada al doble, y una con el contraste forzado.
    """
    try:
        import zxingcpp
    except ImportError:
        return None

    intentos = [imagen_gris]

    alto, ancho = imagen_gris.shape[:2]
    if ancho < 2400:
        intentos.append(
            cv2.resize(imagen_gris, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        )

    intentos.append(
        cv2.threshold(imagen_gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    )

    for indice, intento in enumerate(intentos):
        try:
            resultados = zxingcpp.read_barcodes(
                intento, formats=zxingcpp.BarcodeFormat.PDF417
            )
        except Exception:
            continue

        for resultado in resultados:
            crudo = bytes(resultado.bytes or b"")
            caja = _caja_de_posicion(resultado.position)

            # Las coordenadas del intento ampliado hay que devolverlas a
            # la escala de la imagen original, que es la que usa la
            # interfaz para dibujar.
            if caja and indice == 1 and ancho < 2400:
                caja = {k: v // 2 for k, v in caja.items()}

            datos = _parsear(crudo, caja)
            if datos:
                return datos

    return None
