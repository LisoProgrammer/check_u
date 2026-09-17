"""
Lectura de la cedula digital de policarbonato (formato desde 2020).

Es la que el proyecto ya sabia leer: trae en el reverso un MRZ propio de
3 lineas de 30 caracteres, que modules/mrz parsea por posiciones fijas.

Lo que agrega este modulo sobre lo que ya habia:

- Devuelve la CAJA de donde salio cada dato, para poder dibujarla sobre
  el documento en la interfaz.
- Mantiene el cruce con las etiquetas impresas del frente ("NUIP",
  "Apellidos", "Nombres"), que ya estaba resuelto y sigue siendo
  necesario: el MRZ corta los nombres a 30 caracteres por linea y se
  desalinea entero si el OCR pierde o agrega un solo caracter, mientras
  que las etiquetas no dependen de posiciones fijas.

Ojo con la diferencia de maquetacion entre formatos: en la cedula
digital la etiqueta va ARRIBA del valor ("Apellidos" y debajo el
apellido), mientras que en la amarilla va DEBAJO. Por eso cada formato
tiene su propio modulo de lectura en vez de compartir uno solo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .amarilla import CampoLeido, _nombres_por_estructura, _unir_cajas
from .ocr_cajas import Linea, caja_de, compactar, palabras_en_mayuscula

_ETIQUETAS_A_SALTAR = {
    "NOMBRES", "APELLIDOS", "APEFICOS", "APOLLIDOS", "NACIONALIDAD",
    "SEXO", "ESTATURA", "FIRMA", "NUIP", "NUMERO",
}

# Mapa inverso al de modules/mrz/normalize.py (que corrige letra->digito).
# Aca se usa para tolerar la confusion mas comun al leer "COL" (la
# nacionalidad, un campo de LETRAS): Tesseract lee "C0L" muy seguido,
# incluso en cedulas donde el resto del MRZ salio perfecto.
_DIGITO_A_LETRA = {
    "0": "O", "1": "I", "5": "S", "8": "B", "2": "Z", "6": "G", "7": "T",
}


@dataclass
class LecturaDigital:
    numero_documento: CampoLeido = field(default_factory=CampoLeido)
    nombre_completo: CampoLeido = field(default_factory=CampoLeido)
    fecha_nacimiento: CampoLeido = field(default_factory=CampoLeido)
    edad: int | None = None
    sexo: CampoLeido = field(default_factory=CampoLeido)
    nacionalidad: str | None = None
    mrz_valido: bool | None = None
    lineas_mrz: list[str] = field(default_factory=list)
    caja_mrz: dict | None = None
    avisos: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Deteccion del MRZ
# ---------------------------------------------------------------------------

def detectar_mrz(lineas: list[Linea]) -> tuple[list[str], dict | None, int] | None:
    """
    Busca las 3 lineas del MRZ dentro de las lineas OCR.

    Señal fuerte de MRZ real: el relleno con "<". No basta con que sea
    texto largo en mayusculas, porque el encabezado de la cedula
    ("REPUBLICA DE COLOMBIA") tambien lo es.

    Devuelve (lineas_ajustadas_a_30_caracteres, caja_que_las_envuelve,
    pagina) o None si no hay MRZ -- que es justamente como se decide que
    el documento es del formato amarillo.
    """
    from modules.mrz.normalize import normalize_line

    candidatas: list[tuple[str, Linea]] = []

    for linea in lineas:
        limpia = normalize_line(linea.texto)
        if len(limpia) < 20 or "<" not in limpia:
            continue
        candidatas.append((limpia, linea))

    if len(candidatas) < 3:
        return None

    # El MRZ va al final del documento.
    ultimas = candidatas[-3:]

    ajustadas = []
    for texto, _ in ultimas:
        if len(texto) > 30:
            texto = texto[:30]
        elif len(texto) < 30:
            texto = texto.ljust(30, "<")
        ajustadas.append(texto)

    caja = _unir_cajas([linea.caja for _, linea in ultimas])
    pagina = ultimas[-1][1].pagina

    return ajustadas, caja, pagina


def _calcular_edad(anio: int, mes: int, dia: int) -> int | None:
    try:
        nacimiento = date(anio, mes, dia)
    except ValueError:
        return None

    hoy = date.today()
    return hoy.year - nacimiento.year - (
        (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day)
    )


def _nacionalidad_parece(nacionalidad: str, esperada: str = "COL") -> bool:
    corregida = "".join(_DIGITO_A_LETRA.get(c, c) for c in nacionalidad)
    return corregida == esperada


# ---------------------------------------------------------------------------
# Etiquetas del frente (valor DEBAJO de la etiqueta en este formato)
# ---------------------------------------------------------------------------

def _valor_bajo_etiqueta(lineas: list[Linea], etiquetas: set[str]) -> CampoLeido | None:
    for indice, linea in enumerate(lineas):
        if not any(compactar(p.texto) in etiquetas for p in linea.palabras):
            continue

        for siguiente in range(indice + 1, len(lineas)):
            candidatas = [
                p for p in palabras_en_mayuscula(lineas[siguiente])
                if compactar(p.texto) not in _ETIQUETAS_A_SALTAR
            ]
            if candidatas:
                return CampoLeido(
                    valor=" ".join(p.texto.upper() for p in candidatas),
                    caja=caja_de(candidatas),
                    fuente="etiqueta",
                    confianza=min(p.confianza for p in candidatas),
                    pagina=lineas[siguiente].pagina,
                )
            # Solo se avanza sobre lineas vacias o de puras etiquetas.
            if lineas[siguiente].palabras and not all(
                compactar(p.texto) in _ETIQUETAS_A_SALTAR or len(compactar(p.texto)) < 3
                for p in lineas[siguiente].palabras
            ):
                break

    return None


def _numero_por_etiqueta(lineas: list[Linea]) -> CampoLeido | None:
    """Numero grande del frente, junto a la etiqueta NUIP o NUMERO."""
    from modules.mrz.normalize import normalize_numeric_field

    for linea in lineas:
        posicion = None
        for i, palabra in enumerate(linea.palabras):
            if re.fullmatch(r"N[UÚ][I1]P|N[UÚ]MERO", compactar(palabra.texto)):
                posicion = i
                break

        if posicion is None:
            continue

        usadas = [
            p for p in linea.palabras[posicion + 1:]
            if any(c.isdigit() for c in p.texto)
        ]
        if not usadas:
            continue

        numero = re.sub(r"[.,\s]", "", " ".join(p.texto for p in usadas))
        numero = normalize_numeric_field(numero)

        if numero.isdigit() and 6 <= len(numero) <= 10:
            return CampoLeido(
                valor=numero,
                caja=caja_de(usadas),
                fuente="etiqueta",
                confianza=min(p.confianza for p in usadas),
                pagina=usadas[0].pagina,
            )

    return None


# ---------------------------------------------------------------------------
# Entrada principal
# ---------------------------------------------------------------------------

def leer(
    lineas: list[Linea],
    lineas_mrz: list[str],
    caja_mrz: dict | None,
    pagina_mrz: int = 0,
    alto_pagina: int = 2000,
) -> LecturaDigital:
    from modules.mrz.get_info import get_info as mrz_get_info
    from modules.mrz.validate import validate_mrz

    lectura = LecturaDigital(lineas_mrz=lineas_mrz, caja_mrz=caja_mrz)
    texto_mrz = "\n".join(lineas_mrz)

    try:
        info = mrz_get_info(texto_mrz)
    except Exception as e:
        lectura.errores.append(f"No se pudo interpretar el MRZ: {e}")
        info = None

    if info is not None:
        validacion = validate_mrz(texto_mrz)
        lectura.mrz_valido = validacion.valid
        lectura.avisos.extend(validacion.warnings)
        lectura.errores.extend(validacion.errors)

        lectura.numero_documento = CampoLeido(
            valor=info.document_number.replace("<", "").strip(),
            caja=caja_mrz,
            fuente="mrz",
            pagina=pagina_mrz,
        )
        lectura.nombre_completo = CampoLeido(
            valor=f"{info.given_names} {info.surname}".strip(),
            caja=caja_mrz,
            fuente="mrz",
            pagina=pagina_mrz,
        )
        lectura.sexo = CampoLeido(
            valor=info.sex, caja=caja_mrz, fuente="mrz", pagina=pagina_mrz
        )
        lectura.nacionalidad = info.nationality

        try:
            anio, mes, dia = int(info.birth_year), int(info.birth_month), int(info.birth_day)
            edad = _calcular_edad(anio, mes, dia)

            # get_info.py siempre antepone "20" al año de 2 digitos.
            # Si eso da una fecha futura, la persona nacio en 19xx.
            if edad is not None and edad < 0:
                anio -= 100
                edad = _calcular_edad(anio, mes, dia)

            lectura.edad = edad
            lectura.fecha_nacimiento = CampoLeido(
                valor=f"{dia:02d}/{mes:02d}/{anio}",
                caja=caja_mrz,
                fuente="mrz",
                pagina=pagina_mrz,
            )
        except Exception:
            pass

        # La nacionalidad va justo antes del numero de documento en la
        # misma linea del MRZ. Si no se leyo "COL", puede ser el
        # documento de un extranjero, pero tambien es la señal mas
        # practica de que el OCR perdio o agrego un caracter antes -- lo
        # que correria todos los campos de posicion fija que siguen,
        # incluido el numero. Se informa como dato, sin decidir por el
        # usuario si el numero es confiable.
        if not _nacionalidad_parece(info.nationality or ""):
            lectura.avisos.append(
                f"Nacionalidad leida: '{info.nationality}' (distinta de 'COL'). "
                "Puede ser un documento de un extranjero, o el MRZ se leyo "
                "corrido/desalineado; en ese caso conviene revisar el numero "
                "de documento a mano."
            )

    # --- Cruce con las etiquetas impresas del frente ---
    numero_etiqueta = _numero_por_etiqueta(lineas)
    apellidos = _valor_bajo_etiqueta(lineas, {"APELLIDOS"})
    nombres = _valor_bajo_etiqueta(lineas, {"NOMBRES"})

    # Respaldo estructural: si las etiquetas "Apellidos"/"Nombres" no se
    # leyeron (letra chica, foto con reflejo), se usan los dos primeros
    # renglones de texto grande debajo del numero, que en esta cedula son
    # justamente apellidos y nombres -- igual que en la amarilla.
    if not (apellidos and apellidos.valor) or not (nombres and nombres.valor):
        por_estructura = _nombres_por_estructura(
            lineas, numero_etiqueta, alto_pagina
        )
        if not (apellidos and apellidos.valor):
            apellidos = por_estructura[0] or apellidos
        if not (nombres and nombres.valor):
            nombres = por_estructura[1] or nombres

    nombre_etiqueta = None
    if apellidos and apellidos.valor and nombres and nombres.valor:
        nombre_etiqueta = CampoLeido(
            valor=f"{nombres.valor} {apellidos.valor}",
            caja=_unir_cajas([nombres.caja, apellidos.caja]),
            fuente="etiqueta",
            pagina=nombres.pagina,
        )
    elif apellidos and apellidos.valor:
        nombre_etiqueta = apellidos

    if numero_etiqueta and numero_etiqueta.valor:
        actual = lectura.numero_documento.valor
        if actual and numero_etiqueta.valor != actual:
            lectura.avisos.append(
                f"El numero leido en el frente ('{numero_etiqueta.valor}') no "
                f"coincide con el del MRZ ('{actual}'). Se usa el del frente: "
                "el MRZ se desalinea entero si el OCR pierde un caracter."
            )
            lectura.numero_documento = numero_etiqueta
        elif not actual:
            lectura.numero_documento = numero_etiqueta

    # El MRZ corta a 30 caracteres por linea, la etiqueta no: si la
    # etiqueta entrega un nombre mas largo, es el completo.
    if nombre_etiqueta and nombre_etiqueta.valor:
        actual = lectura.nombre_completo.valor or ""
        if len(nombre_etiqueta.valor) > len(actual):
            lectura.nombre_completo = nombre_etiqueta

    # Preferir SIEMPRE la caja del texto impreso del frente cuando dice lo
    # mismo que el MRZ. El valor no cambia; lo que mejora es donde se le
    # muestra al usuario: el MRZ es una sola franja que contiene todos los
    # campos a la vez, asi que señalarla no dice nada ("el numero salio de
    # aca, y el nombre tambien, y la fecha tambien"). El numero grande y el
    # nombre del frente si son regiones distintas y legibles a simple vista,
    # que es lo que hace util el recuadro para quien revisa.
    _preferir_caja(lectura.numero_documento, numero_etiqueta)
    _preferir_caja(lectura.nombre_completo, nombre_etiqueta)

    return lectura


def _preferir_caja(campo: CampoLeido, alternativa: CampoLeido | None) -> None:
    """Usa la caja de `alternativa` si apunta al MISMO valor ya resuelto.

    La condicion de que el valor coincida es importante: si el texto del
    frente se leyo distinto que el MRZ, su caja estaria señalando un dato
    que no es el que se esta mostrando.
    """
    if not alternativa or not alternativa.caja or not campo.valor:
        return
    if (alternativa.valor or "").strip().upper() != campo.valor.strip().upper():
        return

    campo.caja = alternativa.caja
    campo.pagina = alternativa.pagina
