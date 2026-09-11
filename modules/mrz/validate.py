# modules/ocr_module/mrz/validate.py

from __future__ import annotations

from dataclasses import dataclass

from .normalize import (
    normalize_mrz,
    normalize_numeric_field,
)


# ================================================================
# RESULTADO
# ================================================================

@dataclass
class ValidationResult:

    valid: bool

    structure_valid: bool
    characters_valid: bool
    check_digits_valid: bool

    errors: list[str]
    warnings: list[str]

    lines: list[str]


# ================================================================
# VALORES MRZ
# ================================================================

def char_value(
    char: str,
) -> int:
    """
    Convierte un carácter MRZ a su valor numérico.

    0-9 -> 0-9
    A-Z -> 10-35
    <   -> 0
    """

    if char == "<":
        return 0

    if "0" <= char <= "9":
        return ord(char) - ord("0")

    if "A" <= char <= "Z":
        return ord(char) - ord("A") + 10

    raise ValueError(
        f"Carácter MRZ inválido: {char}"
    )


# ================================================================
# CHECK DIGIT
# ================================================================

def calculate_check_digit(
    value: str,
) -> int:
    """
    Calcula el check digit MRZ.

    Pesos:

        7, 3, 1

    repetidos cíclicamente.
    """

    weights = (
        7,
        3,
        1,
    )

    total = 0

    for index, char in enumerate(value):

        total += (
            char_value(char)
            * weights[index % 3]
        )

    return total % 10


# ================================================================
# VALIDAR CHECK DIGIT
# ================================================================

def validate_check_digit(
    value: str,
    check_digit: str,
) -> bool:
    """
    Comprueba un check digit.
    """

    if len(check_digit) != 1:
        return False

    # El OCR puede confundir O/I/L/etc. con números.
    check_digit = normalize_numeric_field(
        check_digit
    )

    if not check_digit.isdigit():
        return False

    calculated = calculate_check_digit(
        value
    )

    return calculated == int(
        check_digit
    )


# ================================================================
# ESTRUCTURA
# ================================================================

def validate_structure(
    lines: list[str],
) -> list[str]:

    errors = []

    if len(lines) != 3:

        errors.append(
            f"Se esperaban 3 líneas y se recibieron "
            f"{len(lines)}."
        )

        return errors

    for index, line in enumerate(
        lines,
        start=1,
    ):

        if len(line) != 30:

            errors.append(
                f"Línea {index}: "
                f"se esperaban 30 caracteres y "
                f"se encontraron {len(line)}."
            )

    return errors


# ================================================================
# VALIDAR CARACTERES
# ================================================================

def validate_characters(
    lines: list[str],
) -> list[str]:

    errors = []

    allowed = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "<"
    )

    for line_number, line in enumerate(
        lines,
        start=1,
    ):

        for position, char in enumerate(
            line
        ):

            if char not in allowed:

                errors.append(
                    f"Línea {line_number}, "
                    f"posición {position}: "
                    f"carácter inválido '{char}'."
                )

    return errors


# ================================================================
# VALIDAR CHECK DIGITS
# ================================================================

def validate_check_digits(
    lines: list[str],
) -> tuple[list[str], list[str]]:

    errors = []
    warnings = []

    if len(lines) != 3:
        return errors, warnings

    line1, line2, line3 = lines

    if (
        len(line1) != 30
        or len(line2) != 30
        or len(line3) != 30
    ):
        return errors, warnings

    # ------------------------------------------------------------
    # Línea 2
    # ------------------------------------------------------------

    # Fecha de nacimiento
    birth_date = line2[0:6]
    birth_check = line2[6]

    if not validate_check_digit(
        birth_date,
        birth_check,
    ):

        errors.append(
            "El check digit de la fecha "
            "de nacimiento no es válido."
        )

    # ------------------------------------------------------------
    # Fecha de vencimiento
    # ------------------------------------------------------------

    expiry_date = line2[8:14]
    expiry_check = line2[14]

    if not validate_check_digit(
        expiry_date,
        expiry_check,
    ):

        errors.append(
            "El check digit de la fecha "
            "de vencimiento no es válido."
        )

    # ------------------------------------------------------------
    # Advertencia sobre posibles errores OCR
    # ------------------------------------------------------------

    numeric_positions = {
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
    }

    for position in numeric_positions:

        char = line2[position]

        if char in {
            "O",
            "I",
            "L",
            "Z",
            "S",
            "G",
            "T",
            "B",
        }:

            warnings.append(
                "Posible error OCR en línea 2, "
                f"posición {position}: '{char}'."
            )

    return errors, warnings


# ================================================================
# VALIDACIÓN COMPLETA
# ================================================================

def validate_mrz(
    mrz: str,
) -> ValidationResult:
    """
    Valida un MRZ completo.

    No modifica agresivamente el texto OCR.
    """

    lines = normalize_mrz(
        mrz
    )

    # ------------------------------------------------------------
    # Estructura
    # ------------------------------------------------------------

    structure_errors = validate_structure(
        lines
    )

    if structure_errors:

        return ValidationResult(
            valid=False,
            structure_valid=False,
            characters_valid=False,
            check_digits_valid=False,
            errors=structure_errors,
            warnings=[],
            lines=lines,
        )

    # ------------------------------------------------------------
    # Caracteres
    # ------------------------------------------------------------

    character_errors = validate_characters(
        lines
    )

    if character_errors:

        return ValidationResult(
            valid=False,
            structure_valid=True,
            characters_valid=False,
            check_digits_valid=False,
            errors=character_errors,
            warnings=[],
            lines=lines,
        )

    # ------------------------------------------------------------
    # Check digits
    # ------------------------------------------------------------

    check_errors, warnings = (
        validate_check_digits(
            lines
        )
    )

    check_digits_valid = (
        len(check_errors) == 0
    )

    # ------------------------------------------------------------
    # Resultado
    # ------------------------------------------------------------

    valid = (
        len(structure_errors) == 0
        and len(character_errors) == 0
        and check_digits_valid
    )

    return ValidationResult(
        valid=valid,
        structure_valid=True,
        characters_valid=True,
        check_digits_valid=check_digits_valid,
        errors=check_errors,
        warnings=warnings,
        lines=lines,
    )


# ================================================================
# DICT
# ================================================================

def validate_mrz_dict(
    mrz: str,
) -> dict:

    result = validate_mrz(
        mrz
    )

    return {
        "valid": result.valid,
        "structure_valid": result.structure_valid,
        "characters_valid": result.characters_valid,
        "check_digits_valid": result.check_digits_valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "lines": result.lines,
    }


# ================================================================
# PRUEBA DIRECTA
# ================================================================

if __name__ == "__main__":

    mrz = """
RELLENAR
    """

    result = validate_mrz(
        mrz
    )

    print("=" * 60)
    print("VALIDADOR MRZ")
    print("=" * 60)

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

    if result.errors:

        print("\nERRORES:")

        for error in result.errors:
            print(
                f"  - {error}"
            )

    if result.warnings:

        print("\nADVERTENCIAS OCR:")

        for warning in result.warnings:
            print(
                f"  - {warning}"
            )
