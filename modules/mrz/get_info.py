# modules/ocr_module/mrz/get_info.py

from __future__ import annotations

from dataclasses import dataclass

from .normalize import normalize_mrz, normalize_numeric_field


# ================================================================
# INFORMACIÓN EXTRAÍDA
# ================================================================

@dataclass
class MRZInfo:

    document_type: str
    issuing_country: str

    document_number: str
    document_number_check: str

    municipality: str
    department: str

    birth_date: str
    birth_day: int
    birth_month: int
    birth_year: int

    birth_date_check: str

    sex: str

    expiry_date: str
    expiry_date_check: str

    nationality: str

    optional_data: str
    final_check: str

    surname: str
    given_names: str

    raw_lines: list[str]


# ================================================================
# NOMBRES
# ================================================================

def parse_names(
    line: str,
) -> tuple[str, str]:
    """
    Extrae apellidos y nombres de la tercera línea.

    Ejemplo:

        ZAPATA<PATERNINA<<LISANDRO<ENR

    """

    parts = line.split("<<", 1)

    if len(parts) != 2:
        return line, ""

    surname = parts[0]
    given_names = parts[1]

    surname = surname.replace("<", " ")
    given_names = given_names.replace("<", " ")

    surname = " ".join(
        surname.split()
    )

    given_names = " ".join(
        given_names.split()
    )

    return surname, given_names


# ================================================================
# EXTRACCIÓN
# ================================================================

def get_info(
    mrz: str,
) -> MRZInfo:
    """
    Extrae información del MRZ.

    Actualmente trabaja con el formato de tres líneas
    utilizado por el documento que estamos procesando.

    La función NO determina si el MRZ es válido.
    Esa responsabilidad pertenece a validate.py.
    """

    lines = normalize_mrz(mrz)

    if len(lines) != 3:
        raise ValueError(
            "El MRZ debe contener exactamente 3 líneas."
        )

    line1, line2, line3 = lines

    if len(line1) != 30:
        raise ValueError(
            "La primera línea del MRZ debe tener 30 caracteres."
        )

    if len(line2) != 30:
        raise ValueError(
            "La segunda línea del MRZ debe tener 30 caracteres."
        )

    if len(line3) != 30:
        raise ValueError(
            "La tercera línea del MRZ debe tener 30 caracteres."
        )

    # ------------------------------------------------------------
    # LÍNEA 1
    # ------------------------------------------------------------
    document_type = line1[0:2]
    issuing_country = line1[2:5]

    document_number_check = line1[14]

    optional_data_1 = line1[15:30]
    # department/municipality son códigos DANE, siempre numéricos:
    # se corrigen errores de OCR típicos (L->1, O->0, etc.) igual que
    # ya se hacía solo para los dígitos de chequeo.
    department = normalize_numeric_field(optional_data_1[0:2])
    municipality = normalize_numeric_field(optional_data_1[2:5])

    # ------------------------------------------------------------
    # LÍNEA 2
    # ------------------------------------------------------------

    # El número de documento y las fechas son campos puramente
    # numéricos, así que se les aplica la misma corrección OCR
    # (L->1, O->0, I->1, etc.) que normalize.py ya define y que antes
    # SOLO se usaba para validar dígitos de chequeo en validate.py, no
    # para el valor del campo en sí. Sin esto, un '1' leído como 'L'
    # (confusión común de Tesseract) quedaba tal cual en el número de
    # documento, y nunca iba a coincidir con nada real al consultarlo.
    document_number = normalize_numeric_field(line2[18:28])

    birth_date_raw = normalize_numeric_field(line2[0:6])
    birth_date = birth_date_raw
    birth_day = birth_date_raw[4:6]
    birth_month = birth_date_raw[2:4]
    birth_year = "20" + birth_date_raw[0:2]
    birth_date_check = line2[6]

    sex = line2[7]

    expiry_date = normalize_numeric_field(line2[8:14])
    expiry_date_check = line2[14]

    nationality = line2[15:18]
    optional_data = line2[18:29]
    final_check = line2[29]

    # ------------------------------------------------------------
    # LÍNEA 3
    # ------------------------------------------------------------

    surname, given_names = parse_names(
        line3
    )

    return MRZInfo(
        document_type=document_type,
        issuing_country=issuing_country,

        document_number=document_number,
        document_number_check=document_number_check,

        municipality=municipality,
        department=department,

        birth_date=birth_date,
        birth_day=birth_day,
        birth_month=birth_month,
        birth_year=birth_year,
        birth_date_check=birth_date_check,

        sex=sex,

        expiry_date=expiry_date,
        expiry_date_check=expiry_date_check,

        nationality=nationality,

        optional_data=optional_data,
        final_check=final_check,

        surname=surname,
        given_names=given_names,

        raw_lines=lines,
    )


# ================================================================
# COMO DICCIONARIO
# ================================================================

def get_info_dict(
    mrz: str,
) -> dict:
    """
    Devuelve la información en formato dict.

    Útil para convertir posteriormente a JSON.
    """

    info = get_info(mrz)

    return {
        "document_type": info.document_type,
        "issuing_country": info.issuing_country,
        "document_number": info.document_number,
        "birth_date": info.birth_date,
        "birth_day": info.birth_day,
        "birth_month": info.birth_month,
        "birth_year": info.birth_year,
        "sex": info.sex,
        "expiry_date": info.expiry_date,
        "surname": info.surname,
        "given_names": info.given_names,
        "raw_lines": info.raw_lines,
    }
