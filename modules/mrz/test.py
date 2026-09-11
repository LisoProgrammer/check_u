# modules/ocr_module/mrz/test.py

from __future__ import annotations

from .normalize import normalize_mrz
from .get_info import get_info_dict
from .validate import validate_mrz


# ================================================================
# MRZ DE PRUEBA
# ================================================================

MRZ = """
RELLENAR
"""


# ================================================================
# PRUEBA DE NORMALIZACIÓN
# ================================================================

def test_normalize():

    print()
    print("=" * 70)
    print("1. NORMALIZACIÓN")
    print("=" * 70)

    lines = normalize_mrz(MRZ)

    for index, line in enumerate(lines, start=1):

        print(
            f"Línea {index}: "
            f"{line}"
        )

        print(
            f"Longitud: {len(line)}"
        )


# ================================================================
# PRUEBA DE EXTRACCIÓN
# ================================================================

def test_get_info():

    print()
    print("=" * 70)
    print("2. INFORMACIÓN EXTRAÍDA")
    print("=" * 70)

    try:

        info = get_info_dict(
            MRZ
        )

        for key, value in info.items():

            print(
                f"{key}: {value}"
            )

    except Exception as error:

        print(
            "ERROR AL EXTRAER INFORMACIÓN:"
        )

        print(
            error
        )


# ================================================================
# PRUEBA DE VALIDACIÓN
# ================================================================

def test_validate():

    print()
    print("=" * 70)
    print("3. VALIDACIÓN")
    print("=" * 70)

    result = validate_mrz(
        MRZ
    )

    print(
        f"Válido:             {result.valid}"
    )

    print(
        f"Estructura válida:  "
        f"{result.structure_valid}"
    )

    print(
        f"Caracteres válidos: "
        f"{result.characters_valid}"
    )

    print(
        f"Check digits:       "
        f"{result.check_digits_valid}"
    )

    # ------------------------------------------------------------
    # ERRORES
    # ------------------------------------------------------------

    if result.errors:

        print()
        print("ERRORES:")

        for error in result.errors:

            print(
                f"  Error {error}"
            )

    else:

        print()
        print(
            "ERRORES: ninguno"
        )

    # ------------------------------------------------------------
    # ADVERTENCIAS
    # ------------------------------------------------------------

    if result.warnings:

        print()
        print("ADVERTENCIAS:")

        for warning in result.warnings:

            print(
                f"Warning {warning}"
            )

    else:

        print()
        print(
            "ADVERTENCIAS: ninguna"
        )


# ================================================================
# EJECUCIÓN
# ================================================================

def main():

    print()
    print("#" * 70)
    print("# TEST MRZ - CHECKU")
    print("#" * 70)

    test_normalize()

    test_get_info()

    test_validate()

    print()
    print("#" * 70)
    print("# FIN DEL TEST")
    print("#" * 70)
    print()


if __name__ == "__main__":
    main()
