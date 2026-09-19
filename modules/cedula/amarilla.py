"""
Lectura de la cedula amarilla con hologramas (formato 2000-2020).

Este formato NO tiene MRZ, asi que todo el parseo por posiciones fijas
que usa modules/mrz no aplica. Lo que si tiene:

FRENTE
    REPUBLICA DE COLOMBIA
    IDENTIFICACION PERSONAL
    CEDULA DE CIUDADANIA
    NUMERO        40.048.750          [foto]
    RIAÑO HIGUERA           <- valor
    APELLIDOS               <- etiqueta, DEBAJO del valor
    VICKY LILIANA           <- valor
    NOMBRES                 <- etiqueta, DEBAJO del valor
    <firma manuscrita>
    FIRMA

REVERSO
    [huella]  FECHA DE NACIMIENTO  08-NOV-1980
              TUNJA (BOYACA)
              LUGAR DE NACIMIENTO
              1.60      A+      F
              ESTATURA  G.S. RH  SEXO
              24-FEB-1999 TUNJA
              FECHA Y LUGAR DE EXPEDICION
    [codigo de barras PDF417]
    A-0704900-00150296-F-0040048750-20090211  00099 61521A 1  4980017488

Dos detalles que definen como hay que leerla:

1. **La etiqueta va DEBAJO del valor** (al reves que la cedula digital,
   donde "Apellidos"/"Nombres" van arriba). Por eso aca se busca la
   etiqueta y se lee la linea ANTERIOR, no la siguiente.

2. **La linea de produccion del reverso repite el numero de documento**
   rellenado a 10 digitos ("0040048750" -> 40048750) junto con el sexo.
   Es una segunda fuente independiente del OCR del frente, util cuando
   la foto esta borrosa justo sobre el numero grande.

Orden de confianza al resolver el numero: PDF417 (digital, con
correccion de errores) > linea de produccion (patron muy rigido, facil
de validar) > numero grande del frente (OCR suelto).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .ocr_cajas import Linea, Palabra, caja_de, compactar, palabras_en_mayuscula

# Etiquetas impresas que hay que reconocer (ya compactadas: solo letras).
# Se incluyen variantes que produce el OCR con frecuencia en estas fotos.
_ETIQUETA_APELLIDOS = {"APELLIDOS", "APELLIDO", "APELLIOOS", "APELUDOS", "APEWDOS"}
_ETIQUETA_NOMBRES = {"NOMBRES", "NOMBRE", "NOMBBES", "NOMERES"}
_ETIQUETA_NUMERO = {"NUMERO", "NUMERD", "NIJMERO", "NUMFRO"}

# Etiquetas que nunca son parte de un nombre, por si quedan pegadas.
_NO_ES_NOMBRE = {
    "REPUBLICA", "COLOMBIA", "IDENTIFICACION", "PERSONAL", "CEDULA",
    "CIUDADANIA", "NUMERO", "APELLIDOS", "NOMBRES", "FIRMA", "ESTATURA",
    "SEXO", "INDICE", "DERECHO", "REGISTRADOR", "NACIONAL", "FECHA",
    "NACIMIENTO", "LUGAR", "EXPEDICION", "DE", "Y",
}

# Linea de produccion: letra - 7 digitos - 8 digitos - sexo - 10 digitos - fecha.
# Se aceptan espacios alrededor de los guiones porque el OCR los mete.
_PATRON_PRODUCCION = re.compile(
    r"([A-Z])\s*-\s*(\d{6,8})\s*-\s*(\d{7,9})\s*-\s*([FMH])\s*-\s*(\d{9,11})\s*-\s*(\d{7,9})"
)


@dataclass
class CampoLeido:
    valor: str | None = None
    caja: dict | None = None
    fuente: str | None = None       # "pdf417" | "produccion" | "etiqueta" | "mrz"
    confianza: float | None = None
    pagina: int = 0                 # en que pagina del documento esta la caja


@dataclass
class LecturaAmarilla:
    numero_documento: CampoLeido = field(default_factory=CampoLeido)
    nombre_completo: CampoLeido = field(default_factory=CampoLeido)
    apellidos: CampoLeido = field(default_factory=CampoLeido)
    nombres: CampoLeido = field(default_factory=CampoLeido)
    fecha_nacimiento: CampoLeido = field(default_factory=CampoLeido)
    sexo: CampoLeido = field(default_factory=CampoLeido)
    avisos: list[str] = field(default_factory=list)


def _ordenar(lineas: list[Linea]) -> list[Linea]:
    """De arriba hacia abajo. Tesseract numera por bloques y un bloque
    puede quedar antes que otro que esta mas arriba en la pagina."""
    def clave(linea: Linea):
        caja = linea.caja
        return (caja["y"] if caja else 0, caja["x"] if caja else 0)

    return sorted([l for l in lineas if l.palabras], key=clave)


def _corregir_digitos(texto: str) -> str:
    """Letras que Tesseract confunde con digitos, en campos numericos."""
    tabla = {
        "O": "0", "Q": "0", "D": "0",
        "I": "1", "L": "1", "|": "1",
        "Z": "2", "S": "5", "G": "6", "T": "7", "B": "8",
    }
    return "".join(tabla.get(c, c) for c in texto.upper())


def _solo_digitos(texto: str) -> str:
    return "".join(c for c in _corregir_digitos(texto) if c.isdigit())


def _numero_valido(numero: str) -> bool:
    """Las cedulas colombianas van de 6 a 10 digitos."""
    return numero.isdigit() and 6 <= len(numero) <= 10


# ---------------------------------------------------------------------------
# Numero de documento
# ---------------------------------------------------------------------------

def _numero_por_linea_produccion(lineas: list[Linea]) -> CampoLeido | None:
    for linea in lineas:
        texto = _corregir_digitos(linea.texto).replace(" ", "")
        # Se vuelven a meter los guiones que el OCR pudo leer como otra cosa.
        texto = texto.replace("—", "-").replace("–", "-").replace("_", "-")

        coincidencia = _PATRON_PRODUCCION.search(texto)
        if not coincidencia:
            continue

        numero = coincidencia.group(5).lstrip("0")
        if not _numero_valido(numero):
            continue

        return CampoLeido(
            valor=numero,
            caja=linea.caja,
            fuente="produccion",
            confianza=min((p.confianza for p in linea.palabras), default=0.0),
            pagina=linea.pagina,
        )

    return None


def _numero_por_etiqueta(lineas: list[Linea]) -> CampoLeido | None:
    """
    Busca la etiqueta "NUMERO" y toma las cifras que vienen despues en la
    misma linea. Si la etiqueta quedo sola, mira la linea siguiente.
    """
    for indice, linea in enumerate(lineas):
        palabras = linea.palabras
        posicion_etiqueta = None

        for i, palabra in enumerate(palabras):
            if compactar(palabra.texto) in _ETIQUETA_NUMERO:
                posicion_etiqueta = i
                break

        if posicion_etiqueta is None:
            continue

        # 1) Cifras en la misma linea, a la derecha de la etiqueta.
        candidatas = palabras[posicion_etiqueta + 1:]
        # 2) Si no hay nada util, la linea de abajo.
        if not candidatas and indice + 1 < len(lineas):
            candidatas = lineas[indice + 1].palabras

        usadas = [p for p in candidatas if any(c.isdigit() for c in _corregir_digitos(p.texto))]
        numero = _solo_digitos(" ".join(p.texto for p in usadas))

        if _numero_valido(numero):
            return CampoLeido(
                valor=numero,
                caja=caja_de(usadas),
                fuente="etiqueta",
                confianza=min((p.confianza for p in usadas), default=0.0),
                pagina=usadas[0].pagina,
            )

    return None


def _numero_por_formato_miles(lineas: list[Linea]) -> CampoLeido | None:
    """
    Ultimo recurso: el numero va impreso grande y con puntos de miles
    ("40.048.750"). Se busca ese patron en cualquier parte del frente,
    sin depender de que la etiqueta se haya leido.
    """
    mejor = None

    for linea in lineas:
        for palabra in linea.palabras:
            texto = _corregir_digitos(palabra.texto)
            # El punto/coma final lo agrega el OCR, no esta impreso.
            texto = texto.rstrip(".,")
            if not re.fullmatch(r"\d{1,3}(?:[.,]\d{3}){1,3}", texto):
                continue

            numero = _solo_digitos(texto)
            if not _numero_valido(numero):
                continue

            candidato = CampoLeido(
                valor=numero,
                caja=caja_de([palabra]),
                fuente="etiqueta",
                confianza=palabra.confianza,
                pagina=palabra.pagina,
            )
            # El numero de la cedula es el texto mas grande del frente:
            # ante varios candidatos, gana el de letra mas alta.
            if mejor is None or palabra.alto > mejor[1]:
                mejor = (candidato, palabra.alto)

    return mejor[0] if mejor else None


# ---------------------------------------------------------------------------
# Nombres
# ---------------------------------------------------------------------------
#
# En este formato las etiquetas ("APELLIDOS", "NOMBRES") van impresas en
# letra MUY chica debajo de cada valor. En fotos y escaneos de calidad
# normal el OCR no las recupera: en las muestras reales salen como
# "ADOS", "NOLAAES", "Sue", con confianza casi nula. Buscarlas para
# ubicar el valor no funciona.
#
# Lo que si es estable es la ESTRUCTURA, que en esta cedula nunca cambia:
#
#     NUMERO   <numero grande>
#     <APELLIDOS>          <- primer renglon de texto grande debajo
#     apellidos            (etiqueta chica, ilegible)
#     <NOMBRES>            <- segundo renglon de texto grande
#     nombres              (etiqueta chica, ilegible)
#
# Asi que se buscan los dos primeros renglones de "texto de campo" que
# aparecen debajo del numero. Un renglon cuenta como texto de campo si
# sus palabras estan en MAYUSCULA, tienen 3+ letras y el OCR las leyo
# con confianza razonable: ese trio separa limpiamente los valores
# reales del ruido de las etiquetas chicas y de la firma manuscrita.

# Confianza minima para considerar que una palabra es texto real.
#
# Deliberadamente BAJA. El resto del proyecto usa 40, pero en cedulas
# amarillas fotografiadas o escaneadas con poca resolucion Tesseract
# reporta confianzas muy bajas incluso cuando acierta: en las muestras
# reales "LOPEZ" y "ALONSO" salieron correctos con confianza 14, y un
# umbral de 40 los borraba junto con el ruido. Aca se filtra por FORMA
# (mayuscula, 3+ letras, que no se parezca a una etiqueta impresa) en
# vez de por confianza, y la confianza solo sirve para descartar lo
# manifiestamente ilegible.
_CONFIANZA_MINIMA = 10.0

# Etiquetas impresas contra las que se compara cada palabra candidata.
# Cuando el OCR las lee mal quedan como "APELITOS", "ADOS", "NOLAAES":
# parecen nombres para cualquier filtro de forma, pero se parecen mucho
# mas a la etiqueta original que a un apellido real.
_ETIQUETAS_IMPRESAS = (
    "APELLIDOS", "NOMBRES", "FIRMA", "NUMERO", "ESTATURA", "SEXO",
    "CEDULA", "CIUDADANIA", "REPUBLICA", "COLOMBIA", "IDENTIFICACION",
)

# Parecido a partir del cual se considera que la palabra ES una etiqueta
# mal leida. 82 deja pasar nombres cortos reales ("ROY" da 80 contra
# "NUMERO") y descarta las etiquetas rotas ("APELITOS" da 82,
# "ADOS" da 86).
_PARECIDO_ETIQUETA = 82


def _parece_etiqueta(texto: str) -> bool:
    limpio = compactar(texto)
    if not limpio:
        return True
    if limpio in _NO_ES_NOMBRE:
        return True

    try:
        from rapidfuzz.fuzz import partial_ratio, ratio
    except ImportError:
        return False

    for etiqueta in _ETIQUETAS_IMPRESAS:
        if max(ratio(limpio, etiqueta), partial_ratio(limpio, etiqueta)) >= _PARECIDO_ETIQUETA:
            return True

    return False


def _solo_letras(texto: str) -> str:
    """Quita signos pegados por el OCR ("¡ALONSO" -> "ALONSO")."""
    return re.sub(r"[^A-ZÁÉÍÓÚÑ]", "", texto.upper())

# Que tan abajo del numero pueden estar los nombres, como fraccion del
# alto de la pagina. Sirve para no confundirlos con el texto del reverso
# (ciudad de nacimiento, de expedicion), que tambien va en mayuscula.
_DISTANCIA_MAXIMA = 0.18


def _palabras_de_campo(linea: Linea) -> list[Palabra]:
    """Palabras de la linea que parecen el valor impreso de un campo."""
    resultado = []
    for palabra in palabras_en_mayuscula(linea):
        if palabra.confianza < _CONFIANZA_MINIMA:
            continue
        if _parece_etiqueta(palabra.texto):
            continue
        resultado.append(palabra)
    return resultado


def _renglones_de_campo(
    lineas: list[Linea], desde_y: int, hasta_y: int, alto_minimo: int = 0
) -> list[list[Palabra]]:
    """
    Agrupa en renglones las palabras de campo que caen en la franja
    vertical dada. Se agrupa por cercania en Y y no por la linea que
    reporto Tesseract, porque el OCR parte seguido un mismo renglon en
    dos cuando las palabras estan separadas por mucho espacio (justo el
    caso de "RIAÑO      HIGUERA").
    """
    palabras = [
        palabra
        for linea in lineas
        for palabra in _palabras_de_campo(linea)
        if desde_y <= palabra.y <= hasta_y and palabra.alto >= alto_minimo
    ]
    if not palabras:
        return []

    palabras.sort(key=lambda p: (p.y, p.x))

    renglones: list[list[Palabra]] = [[palabras[0]]]
    for palabra in palabras[1:]:
        anterior = renglones[-1]
        referencia = anterior[0]
        # Mismo renglon si se solapan verticalmente en buena medida.
        tolerancia = max(referencia.alto, palabra.alto) * 0.6
        if abs(palabra.y - referencia.y) <= tolerancia:
            anterior.append(palabra)
        else:
            renglones.append([palabra])

    for renglon in renglones:
        renglon.sort(key=lambda p: p.x)

    return renglones


def _nombres_por_estructura(
    lineas: list[Linea], campo_numero: CampoLeido | None, alto_pagina: int
) -> tuple[CampoLeido | None, CampoLeido | None]:
    """
    Devuelve (apellidos, nombres) leyendo los dos primeros renglones de
    texto de campo que siguen al numero de documento.
    """
    if campo_numero and campo_numero.caja:
        inicio = campo_numero.caja["y"] + campo_numero.caja["alto"]
        pagina = campo_numero.pagina
    else:
        # Sin numero ubicado: se busca en la parte alta del documento,
        # despues del encabezado.
        inicio = int(alto_pagina * 0.10)
        pagina = 0

    limite = inicio + int(alto_pagina * _DISTANCIA_MAXIMA)

    # El nombre va impreso a un tamaño parecido al del numero; las
    # etiquetas y el ruido son bastante mas chicos. Se exige al menos la
    # mitad de la altura del numero para descartarlos ("LAS", "AUICOS").
    alto_minimo = 0
    if campo_numero and campo_numero.caja:
        alto_minimo = int(campo_numero.caja["alto"] * 0.5)

    en_pagina = [linea for linea in lineas if linea.pagina == pagina]
    renglones = _renglones_de_campo(en_pagina, inicio, limite, alto_minimo)

    if not renglones:
        return None, None

    def a_campo(renglon: list[Palabra]) -> CampoLeido:
        return CampoLeido(
            valor=" ".join(
                limpio for limpio in (_solo_letras(p.texto) for p in renglon) if limpio
            ),
            caja=caja_de(renglon),
            fuente="estructura",
            confianza=min(p.confianza for p in renglon),
            pagina=pagina,
        )

    apellidos = a_campo(renglones[0])
    nombres = a_campo(renglones[1]) if len(renglones) > 1 else None

    return apellidos, nombres


def _valor_sobre_etiqueta(
    lineas: list[Linea], etiquetas: set[str]
) -> CampoLeido | None:
    """
    Encuentra la linea que contiene la etiqueta y devuelve el texto de la
    linea INMEDIATAMENTE ANTERIOR, que en este formato es donde va el
    valor.

    Si la etiqueta viene pegada al valor en la misma linea (pasa cuando
    el OCR junta dos renglones), se usan las palabras de esa misma linea
    descartando la etiqueta.
    """
    for indice, linea in enumerate(lineas):
        tiene_etiqueta = any(
            compactar(p.texto) in etiquetas for p in linea.palabras
        )
        if not tiene_etiqueta:
            continue

        # Caso A: valor pegado en la misma linea que la etiqueta.
        propias = [
            p for p in palabras_en_mayuscula(linea)
            if compactar(p.texto) not in etiquetas
            and compactar(p.texto) not in _NO_ES_NOMBRE
        ]
        if propias:
            return CampoLeido(
                valor=" ".join(p.texto.upper() for p in propias),
                caja=caja_de(propias),
                fuente="etiqueta",
                confianza=min(p.confianza for p in propias),
                pagina=linea.pagina,
            )

        # Caso B (el normal): el valor esta en la linea de arriba.
        for anterior in range(indice - 1, -1, -1):
            candidatas = [
                p for p in palabras_en_mayuscula(lineas[anterior])
                if compactar(p.texto) not in _NO_ES_NOMBRE
                and compactar(p.texto) not in etiquetas
            ]
            if candidatas:
                return CampoLeido(
                    valor=" ".join(p.texto.upper() for p in candidatas),
                    caja=caja_de(candidatas),
                    fuente="etiqueta",
                    confianza=min(p.confianza for p in candidatas),
                    pagina=lineas[anterior].pagina,
                )
            # Solo se retrocede sobre lineas vacias o de puro ruido.
            if lineas[anterior].palabras and any(
                len(compactar(p.texto)) >= 3 for p in lineas[anterior].palabras
            ):
                break

    return None


# ---------------------------------------------------------------------------
# Fecha de nacimiento y sexo (reverso)
# ---------------------------------------------------------------------------

_MESES = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "SET": 9, "OCT": 10, "NOV": 11, "DIC": 12,
}

_PATRON_FECHA = re.compile(r"(\d{1,2})\s*[-/]\s*([A-Z]{3})\s*[-/]\s*(\d{4})")


def _fecha_nacimiento(lineas: list[Linea]) -> CampoLeido | None:
    """
    La primera fecha del reverso es la de nacimiento; la segunda es la de
    expedicion. Se toma la primera que aparezca de arriba hacia abajo.
    """
    for linea in lineas:
        texto = linea.texto.upper().replace(".", "")
        coincidencia = _PATRON_FECHA.search(texto)
        if not coincidencia:
            continue

        dia, mes_texto, anio = coincidencia.groups()
        mes = _MESES.get(mes_texto[:3])
        if not mes:
            continue

        try:
            dia_int = int(dia)
            anio_int = int(anio)
        except ValueError:
            continue

        if not (1 <= dia_int <= 31 and 1900 <= anio_int <= 2100):
            continue

        return CampoLeido(
            valor=f"{dia_int:02d}/{mes:02d}/{anio_int}",
            caja=linea.caja,
            fuente="etiqueta",
            pagina=linea.pagina,
        )

    return None


def _sexo(lineas: list[Linea]) -> CampoLeido | None:
    """
    En el reverso, "SEXO" es la etiqueta y el valor (M o F) va ARRIBA,
    igual que los nombres del frente. Tambien aparece en la linea de
    produccion, que es mas confiable.
    """
    for linea in lineas:
        texto = _corregir_digitos(linea.texto).replace(" ", "")
        coincidencia = _PATRON_PRODUCCION.search(texto)
        if coincidencia:
            valor = coincidencia.group(4)
            return CampoLeido(
                valor="M" if valor == "H" else valor,
                caja=linea.caja,
                fuente="produccion",
                pagina=linea.pagina,
            )

    campo = _valor_sobre_etiqueta(lineas, {"SEXO"})
    if campo and campo.valor:
        letras = [c for c in campo.valor if c in ("M", "F")]
        if len(letras) == 1:
            campo.valor = letras[0]
            return campo

    return None


# ---------------------------------------------------------------------------
# Entrada principal
# ---------------------------------------------------------------------------

def leer(
    lineas: list[Linea], datos_pdf417=None, alto_pagina: int = 2000
) -> LecturaAmarilla:
    """
    Arma la lectura completa de una cedula amarilla a partir de las
    lineas OCR (de todas sus caras/paginas juntas) y, si se pudo
    decodificar, los datos del PDF417.
    """
    lineas = _ordenar(lineas)
    lectura = LecturaAmarilla()

    # --- Numero de documento: de la fuente mas confiable a la menos ---
    if datos_pdf417:
        lectura.numero_documento = CampoLeido(
            valor=datos_pdf417.numero_documento,
            caja=datos_pdf417.caja,
            fuente="pdf417",
            confianza=100.0,
            pagina=datos_pdf417.pagina,
        )
    else:
        for buscar in (
            _numero_por_linea_produccion,
            _numero_por_etiqueta,
            _numero_por_formato_miles,
        ):
            campo = buscar(lineas)
            if campo:
                lectura.numero_documento = campo
                break

    # --- Nombres ---
    if datos_pdf417:
        lectura.nombre_completo = CampoLeido(
            valor=datos_pdf417.nombre_completo,
            caja=datos_pdf417.caja,
            fuente="pdf417",
            confianza=100.0,
            pagina=datos_pdf417.pagina,
        )
        lectura.apellidos = CampoLeido(
            valor=" ".join(
                x for x in (datos_pdf417.primer_apellido, datos_pdf417.segundo_apellido) if x
            ),
            caja=datos_pdf417.caja,
            fuente="pdf417",
            pagina=datos_pdf417.pagina,
        )
        lectura.nombres = CampoLeido(
            valor=" ".join(
                x for x in (datos_pdf417.primer_nombre, datos_pdf417.segundo_nombre) if x
            ),
            caja=datos_pdf417.caja,
            fuente="pdf417",
            pagina=datos_pdf417.pagina,
        )
    else:
        # Primero por estructura (los dos renglones grandes debajo del
        # numero), que es lo unico que aguanta fotos de calidad normal.
        apellidos, nombres = _nombres_por_estructura(
            lineas, lectura.numero_documento, alto_pagina
        )

        # Si por lo que sea no se pudo, se intenta por etiqueta: sirve
        # en escaneos buenos donde "APELLIDOS"/"NOMBRES" si se leen.
        if apellidos is None:
            apellidos = _valor_sobre_etiqueta(lineas, _ETIQUETA_APELLIDOS)
        if nombres is None:
            nombres = _valor_sobre_etiqueta(lineas, _ETIQUETA_NOMBRES)

        if apellidos:
            lectura.apellidos = apellidos
        if nombres:
            lectura.nombres = nombres

        partes = [c.valor for c in (nombres, apellidos) if c and c.valor]
        if partes:
            cajas = [c.caja for c in (nombres, apellidos) if c and c.caja]
            lectura.nombre_completo = CampoLeido(
                valor=" ".join(partes),
                caja=_unir_cajas(cajas),
                fuente="etiqueta",
                pagina=next(
                    (c.pagina for c in (nombres, apellidos) if c and c.caja), 0
                ),
            )

    # --- Fecha de nacimiento y sexo ---
    if datos_pdf417 and datos_pdf417.fecha_nacimiento:
        lectura.fecha_nacimiento = CampoLeido(
            valor=datos_pdf417.fecha_nacimiento,
            caja=datos_pdf417.caja,
            fuente="pdf417",
            pagina=datos_pdf417.pagina,
        )
    else:
        campo = _fecha_nacimiento(lineas)
        if campo:
            lectura.fecha_nacimiento = campo

    if datos_pdf417 and datos_pdf417.sexo:
        lectura.sexo = CampoLeido(
            valor=datos_pdf417.sexo,
            caja=datos_pdf417.caja,
            fuente="pdf417",
            pagina=datos_pdf417.pagina,
        )
    else:
        campo = _sexo(lineas)
        if campo:
            lectura.sexo = campo

    # --- Avisos para el usuario ---
    if datos_pdf417:
        lectura.avisos.append(
            "Datos tomados del codigo de barras PDF417 del reverso "
            "(lectura digital, no depende del OCR)."
        )
    else:
        lectura.avisos.append(
            "No se pudo leer el codigo de barras PDF417 del reverso "
            "(suele pasar con fotos de baja resolucion). Los datos se "
            "obtuvieron por OCR del texto impreso."
        )

    if not lectura.numero_documento.valor:
        lectura.avisos.append(
            "No se pudo determinar el numero de documento. Conviene "
            "cargar una foto mas nitida o con mas resolucion."
        )

    return lectura


def _unir_cajas(cajas: list[dict]) -> dict | None:
    cajas = [c for c in cajas if c]
    if not cajas:
        return None

    x = min(c["x"] for c in cajas)
    y = min(c["y"] for c in cajas)
    x2 = max(c["x"] + c["ancho"] for c in cajas)
    y2 = max(c["y"] + c["alto"] for c in cajas)

    return {"x": x, "y": y, "ancho": x2 - x, "alto": y2 - y}
