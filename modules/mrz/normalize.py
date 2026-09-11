# modules/ocr_module/mrz/normalize.py

from __future__ import annotations


# ================================================================
# CARACTERES PERMITIDOS EN MRZ
# ================================================================

MRZ_ALLOWED = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "<"
)


# ================================================================
# NORMALIZACIÓN GENERAL
# ================================================================

def normalize_text(text: str) -> str:
    """
    Normaliza el texto obtenido por OCR.

    IMPORTANTE:
    No realiza sustituciones agresivas como:

        O -> 0
        I -> 1

    porque esos caracteres pueden ser correctos dependiendo
    del campo MRZ.
    """

    if not isinstance(text, str):
        raise TypeError(
            "El MRZ debe recibirse como str."
        )

    text = text.upper()

    # Normalizar saltos de línea.
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    lines = []

    for line in text.split("\n"):

        # El OCR puede insertar espacios entre caracteres.
        line = line.replace(" ", "")
        line = line.replace("\t", "")

        if line:
            lines.append(line)

    return "\n".join(lines)


# ================================================================
# OBTENER LÍNEAS
# ================================================================

def get_lines(text: str) -> list[str]:
    """
    Devuelve las líneas MRZ sin modificar caracteres.
    """

    normalized = normalize_text(text)

    return [
        line
        for line in normalized.split("\n")
        if line
    ]


# ================================================================
# CORRECCIONES OCR SEGÚN CONTEXTO
# ================================================================

OCR_DIGIT_CORRECTIONS = {
    "O": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "S": "5",
    "G": "6",
    "T": "7",
    "B": "8",
}


def normalize_digit(
    char: str,
) -> str:
    """
    Convierte un carácter que probablemente sea un error OCR
    a dígito.

    SOLO debe utilizarse cuando sabemos que esa posición
    debe contener un número.

    Ejemplo:

        O -> 0
        I -> 1
        L -> 1
    """

    char = char.upper()

    if char.isdigit():
        return char

    return OCR_DIGIT_CORRECTIONS.get(
        char,
        char,
    )


def normalize_numeric_field(
    value: str,
) -> str:
    """
    Normaliza un campo que debe ser exclusivamente numérico.

    No modifica letras si no existe una equivalencia OCR
    razonable.
    """

    result = []

    for char in value:

        normalized = normalize_digit(char)

        result.append(normalized)

    return "".join(result)


# ================================================================
# CARÁCTER MRZ
# ================================================================

def is_valid_mrz_character(
    char: str,
) -> bool:
    """
    Comprueba si un carácter pertenece al alfabeto MRZ.
    """

    return char in MRZ_ALLOWED


# ================================================================
# LIMPIAR UNA LÍNEA
# ================================================================

def normalize_line(
    line: str,
) -> str:
    """
    Normaliza una línea individual.
    """

    line = line.upper()

    line = line.replace(" ", "")
    line = line.replace("\t", "")

    return "".join(
        char
        for char in line
        if char in MRZ_ALLOWED
    )


# ================================================================
# NORMALIZAR MRZ COMPLETO
# ================================================================

def normalize_mrz(
    text: str,
) -> list[str]:
    """
    Devuelve las líneas MRZ normalizadas.

    No corrige O/0, I/1, etc. de forma global.
    """

    lines = get_lines(text)

    return [
        normalize_line(line)
        for line in lines
    ]
