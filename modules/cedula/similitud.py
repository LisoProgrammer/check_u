"""
Comparacion de nombres.

Regla acordada con el equipo: el nombre leido de la cedula y el nombre
que devuelve el RUI deben parecerse al menos un 85 % para dar la
validacion por buena.

No se compara texto crudo, porque dos escrituras del MISMO nombre casi
nunca son identicas caracter por caracter:

- El orden cambia: el MRZ entrega "apellidos, nombres" y el RUI entrega
  "nombres apellidos".
- Las tildes y la Ñ se pierden o se leen mal segun la fuente.
- El OCR agrega o come letras sueltas.
- El MRZ recorta los nombres a 30 caracteres por linea, asi que un
  nombre largo llega incompleto ("MANU" por "MANUEL").

Por eso se normaliza primero (mayusculas, sin tildes, sin signos) y se
usa `token_sort_ratio`, que ordena las palabras antes de comparar: asi
"CABARCAS CUADRADO HECTOR MANUEL" y "HECTOR MANUEL CABARCAS CUADRADO"
dan 100 %, que es lo correcto -- son la misma persona.

Deliberadamente NO se usa `token_set_ratio`, que daria 100 % cuando un
nombre es subconjunto del otro: "HECTOR" contra "HECTOR MANUEL CABARCAS
CUADRADO" pasaria como coincidencia perfecta, y eso es justo el tipo de
error que esta validacion tiene que atrapar.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

UMBRAL_SIMILITUD = 85.0


@dataclass
class Comparacion:
    valor_a: str | None
    valor_b: str | None
    similitud: float          # 0..100
    coincide: bool | None     # None = no se pudo comparar (falta un lado)
    umbral: float = UMBRAL_SIMILITUD


def normalizar(nombre: str | None) -> str:
    """Mayusculas, sin tildes, sin signos, con un solo espacio entre palabras."""
    if not nombre:
        return ""

    # NFD separa la letra de su tilde; se descartan los acentos sueltos.
    descompuesto = unicodedata.normalize("NFD", nombre)
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")

    # La Ñ se pierde en el paso anterior (queda "N"), lo cual es justo lo
    # que se quiere: el RUI y el OCR no siempre coinciden en la eñe.
    limpio = "".join(c if c.isalnum() or c.isspace() else " " for c in sin_tildes)

    return " ".join(limpio.upper().split())


def _ratio(a: str, b: str) -> float:
    try:
        from rapidfuzz.fuzz import token_sort_ratio

        return float(token_sort_ratio(a, b))
    except ImportError:
        # Respaldo sin dependencias: compara las palabras ya ordenadas.
        from difflib import SequenceMatcher

        a_ord = " ".join(sorted(a.split()))
        b_ord = " ".join(sorted(b.split()))
        return SequenceMatcher(None, a_ord, b_ord).ratio() * 100.0


def comparar_nombres(
    nombre_a: str | None,
    nombre_b: str | None,
    umbral: float = UMBRAL_SIMILITUD,
) -> Comparacion:
    """Similitud entre dos nombres, ya normalizados internamente."""
    a = normalizar(nombre_a)
    b = normalizar(nombre_b)

    if not a or not b:
        return Comparacion(nombre_a, nombre_b, 0.0, None, umbral)

    similitud = round(_ratio(a, b), 1)

    return Comparacion(nombre_a, nombre_b, similitud, similitud >= umbral, umbral)


def comparar_numeros(numero_a: str | None, numero_b: str | None) -> Comparacion:
    """
    Los numeros de documento se comparan exacto (sin puntos ni ceros a la
    izquierda): aca un 95 % de parecido no significa "casi correcto",
    significa que es el documento de otra persona.
    """
    a = "".join(c for c in (numero_a or "") if c.isdigit()).lstrip("0")
    b = "".join(c for c in (numero_b or "") if c.isdigit()).lstrip("0")

    if not a or not b:
        return Comparacion(numero_a, numero_b, 0.0, None, 100.0)

    igual = a == b
    return Comparacion(numero_a, numero_b, 100.0 if igual else 0.0, igual, 100.0)
