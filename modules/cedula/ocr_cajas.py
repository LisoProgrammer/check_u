"""
OCR con coordenadas.

El resto del proyecto usa Tesseract solo para obtener TEXTO. Aca se usa
`image_to_data`, que ademas del texto devuelve la caja (x, y, ancho,
alto) de cada palabra. Esas cajas son las que despues se dibujan sobre
el documento en la interfaz para mostrarle al usuario de donde salio
cada dato.

Todo se agrupa en lineas respetando el orden de lectura que reporta
Tesseract (bloque, parrafo, linea), para poder buscar por etiquetas
("NUMERO", "APELLIDOS") mirando tambien la linea de arriba o la de
abajo, que es como esta organizada la cedula amarilla.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pytesseract
from pytesseract import Output


@dataclass
class Palabra:
    texto: str
    x: int
    y: int
    ancho: int
    alto: int
    confianza: float
    # Indice de la pagina del documento de donde salio. Una cedula puede
    # venir como un PDF de 2 paginas (frente y reverso), y el recuadro
    # hay que dibujarlo sobre la pagina correcta.
    pagina: int = 0

    @property
    def x2(self) -> int:
        return self.x + self.ancho

    @property
    def y2(self) -> int:
        return self.y + self.alto


@dataclass
class Linea:
    palabras: list[Palabra] = field(default_factory=list)
    pagina: int = 0

    @property
    def texto(self) -> str:
        return " ".join(p.texto for p in self.palabras)

    @property
    def caja(self) -> dict | None:
        return caja_de(self.palabras)


def caja_de(palabras: list[Palabra]) -> dict | None:
    """Rectangulo que envuelve a todas las palabras dadas."""
    palabras = [p for p in palabras if p]
    if not palabras:
        return None

    x = min(p.x for p in palabras)
    y = min(p.y for p in palabras)
    x2 = max(p.x2 for p in palabras)
    y2 = max(p.y2 for p in palabras)

    return {"x": x, "y": y, "ancho": x2 - x, "alto": y2 - y}


def caja_normalizada(caja: dict | None, ancho: int, alto: int) -> dict | None:
    """
    Convierte una caja en pixeles a fracciones 0..1 del tamaño de la
    imagen. La interfaz dibuja con esas fracciones, asi no importa a que
    tamaño se este mostrando el documento en pantalla.
    """
    if not caja or not ancho or not alto:
        return None

    return {
        "x": round(caja["x"] / ancho, 5),
        "y": round(caja["y"] / alto, 5),
        "ancho": round(caja["ancho"] / ancho, 5),
        "alto": round(caja["alto"] / alto, 5),
    }


def leer_palabras(
    imagen,
    lang: str = "spa",
    psm: int = 3,
    whitelist: str | None = None,
    min_confianza: float = 0.0,
    desplazamiento_y: int = 0,
    pagina: int = 0,
) -> list[Linea]:
    """
    Corre Tesseract sobre `imagen` y devuelve sus lineas con las cajas
    de cada palabra.

    `desplazamiento_y` se suma a la coordenada Y de todas las cajas: sirve
    cuando se le pasa a esta funcion un RECORTE de la imagen (por ejemplo
    la franja del MRZ), para que las coordenadas devueltas sigan siendo
    validas sobre la imagen completa.
    """
    config = f"--oem 3 --psm {psm}"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"

    datos = pytesseract.image_to_data(
        imagen, lang=lang, config=config, output_type=Output.DICT
    )

    lineas: dict[tuple, Linea] = {}

    for i, texto in enumerate(datos["text"]):
        texto = (texto or "").strip()
        if not texto:
            continue

        try:
            confianza = float(datos["conf"][i])
        except (TypeError, ValueError):
            confianza = -1.0

        if confianza < min_confianza:
            continue

        palabra = Palabra(
            texto=texto,
            x=int(datos["left"][i]),
            y=int(datos["top"][i]) + desplazamiento_y,
            ancho=int(datos["width"][i]),
            alto=int(datos["height"][i]),
            confianza=confianza,
            pagina=pagina,
        )

        clave = (
            datos["block_num"][i],
            datos["par_num"][i],
            datos["line_num"][i],
        )
        lineas.setdefault(clave, Linea(pagina=pagina)).palabras.append(palabra)

    return list(lineas.values())


def texto_de(lineas: list[Linea]) -> str:
    return "\n".join(linea.texto for linea in lineas)


# ---------------------------------------------------------------------------
# Utilidades de busqueda dentro de las lineas
# ---------------------------------------------------------------------------

def compactar(texto: str) -> str:
    """Solo letras en mayuscula, sin tildes ni espacios ni signos.

    Sirve para comparar una linea contra una etiqueta impresa sin que un
    punto, un acento mal leido o un espacio de mas la hagan fallar.
    """
    reemplazos = {"Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ü": "U"}
    texto = texto.upper()
    for viejo, nuevo in reemplazos.items():
        texto = texto.replace(viejo, nuevo)
    return re.sub(r"[^A-ZÑ]", "", texto)


def palabras_en_mayuscula(linea: Linea, minimo: int = 3) -> list[Palabra]:
    """
    Palabras de la linea que parecen texto real de un campo impreso en
    MAYUSCULA (nombres, apellidos, ciudades).

    El ruido que rodea a esos campos (marcas de agua, restos de la foto,
    la firma manuscrita) casi siempre sale en minuscula o mezclado, asi
    que este filtro lo descarta sin tener que saber de antemano donde
    empieza y termina el campo dentro de la linea.

    Minimo 3 letras: un fragmento de 2 letras en mayuscula (por ejemplo
    "TA", sobrante de "ESTATURA") alcanzaba a colarse y se pegaba al
    nombre real.
    """
    resultado = []
    for palabra in linea.palabras:
        solo_letras = re.sub(r"[^A-Za-zÁÉÍÓÚÑáéíóúñ]", "", palabra.texto)
        if len(solo_letras) < minimo:
            continue
        # Ya venia en mayuscula en el documento (no la estamos forzando).
        if solo_letras != solo_letras.upper():
            continue
        resultado.append(palabra)
    return resultado
