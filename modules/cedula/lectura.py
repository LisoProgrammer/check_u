"""
Orquestador de la lectura de una cedula.

Es el unico punto de entrada que necesita la webapp:

    resultado = leer_cedula(paginas, progreso=callback)

Se encarga de:

1. Preparar cada pagina (escalado, limpieza, correccion de inclinacion),
   dejando una version a color para mostrar y una binarizada para OCR,
   ambas con la MISMA geometria.
2. Pasar el OCR guardando las coordenadas de cada palabra.
3. **Detectar el formato**: si aparece un MRZ de 3 lineas es una cedula
   digital; si no aparece, es una cedula amarilla con hologramas. El
   cambio se avisa por el callback de progreso para que la interfaz lo
   muestre mientras dura el proceso.
4. Delegar la extraccion al modulo del formato correspondiente.
5. Devolver los campos con su caja normalizada (0..1) y la pagina donde
   esta, listos para dibujar sobre el documento.

Este modulo no escribe nada en disco ni sabe de Flask: devuelve las
imagenes en memoria y la webapp decide que hacer con ellas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import amarilla as _amarilla
from . import digital as _digital
from . import imagen as _imagen
from . import pdf417 as _pdf417
from .ocr_cajas import Linea, caja_normalizada, leer_palabras, texto_de

FORMATO_DIGITAL = "digital"
FORMATO_AMARILLA = "amarilla_hologramas"
FORMATO_DESCONOCIDO = "desconocido"

NOMBRES_FORMATO = {
    FORMATO_DIGITAL: "Cédula digital",
    FORMATO_AMARILLA: "Cédula amarilla con hologramas",
    FORMATO_DESCONOCIDO: "Formato no reconocido",
}

# Caracteres validos en una franja MRZ. Restringir el alfabeto evita que
# Tesseract intente "corregir" hacia palabras del diccionario y reduce
# las confusiones L/1, O/0 en esa franja.
_ALFABETO_MRZ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"

# Porcion inferior de la pagina donde deberia estar el MRZ.
_FRANJA_MRZ = 0.74


@dataclass
class PaginaLeida:
    indice: int
    ancho: int
    alto: int
    display: np.ndarray = field(repr=False)


@dataclass
class ResultadoCedula:
    formato: str
    formato_nombre: str
    campos: dict
    paginas: list[PaginaLeida]
    avisos: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    texto_ocr: str = ""
    mrz: dict | None = None
    edad: int | None = None


def _avisar(progreso, **datos):
    if progreso:
        progreso(datos)


def _campo_a_dict(campo, paginas: list[PaginaLeida]) -> dict:
    """Pasa un CampoLeido a algo que se pueda mandar por JSON, con la
    caja convertida a fracciones del tamaño de su pagina."""
    if campo is None:
        return {"valor": None, "caja": None, "pagina": 0, "fuente": None}

    pagina = None
    for p in paginas:
        if p.indice == campo.pagina:
            pagina = p
            break

    caja = None
    if campo.caja and pagina:
        caja = caja_normalizada(campo.caja, pagina.ancho, pagina.alto)

    return {
        "valor": campo.valor,
        "caja": caja,
        "pagina": campo.pagina,
        "fuente": campo.fuente,
        "confianza": campo.confianza,
    }


def leer_cedula(paginas_entrada, progreso=None) -> ResultadoCedula:
    """
    `paginas_entrada`: lista de imagenes PIL (o numpy) con las paginas del
    documento. `progreso`: callable opcional que recibe diccionarios con
    el avance, para que la interfaz los muestre en vivo.
    """
    paginas: list[PaginaLeida] = []
    lineas_pagina: list[Linea] = []
    lineas_mrz_recorte: list[Linea] = []
    datos_pdf417 = None

    total = len(paginas_entrada)

    for indice, entrada in enumerate(paginas_entrada):
        _avisar(progreso, etapa="preparando", pagina=indice, total=total)
        preparada = _imagen.preparar(entrada)

        paginas.append(
            PaginaLeida(
                indice=indice,
                ancho=preparada.ancho,
                alto=preparada.alto,
                display=preparada.display,
            )
        )

        # --- OCR de la pagina completa ---
        _avisar(progreso, etapa="ocr", pagina=indice, total=total)
        lineas_pagina.extend(
            leer_palabras(preparada.ocr, lang="spa", psm=3, pagina=indice)
        )

        # --- OCR dedicado a la franja del MRZ ---
        # Se corre siempre porque, cuando el documento SI es digital,
        # esta pasada lee la franja bastante mejor que la general: usa
        # alfabeto restringido y psm 6 (bloque uniforme) en vez de la
        # segmentacion automatica con diccionario en español.
        corte = int(preparada.alto * _FRANJA_MRZ)
        recorte = preparada.ocr[corte:, :]
        if recorte.size:
            lineas_mrz_recorte.extend(
                leer_palabras(
                    recorte,
                    lang="eng",
                    psm=6,
                    whitelist=_ALFABETO_MRZ,
                    desplazamiento_y=corte,
                    pagina=indice,
                )
            )

        # --- Codigo de barras PDF417 (solo lo trae la amarilla) ---
        if datos_pdf417 is None:
            encontrado = _pdf417.leer(preparada.gris)
            if encontrado:
                encontrado.pagina = indice
                datos_pdf417 = encontrado

    # ------------------------------------------------------------------
    # Deteccion de formato
    # ------------------------------------------------------------------
    _avisar(progreso, etapa="detectando_formato")

    mrz = _digital.detectar_mrz(lineas_mrz_recorte)
    if mrz is None:
        mrz = _digital.detectar_mrz(lineas_pagina)

    if mrz is not None:
        formato = FORMATO_DIGITAL
        _avisar(
            progreso,
            etapa="formato",
            formato=formato,
            formato_nombre=NOMBRES_FORMATO[formato],
            cambio=False,
        )
    else:
        formato = FORMATO_AMARILLA
        # Aviso explicito del cambio de formato: es lo que la interfaz
        # muestra mientras dura el proceso y esconde al terminar.
        _avisar(
            progreso,
            etapa="formato",
            formato=formato,
            formato_nombre=NOMBRES_FORMATO[formato],
            cambio=True,
            mensaje=(
                "No se detecta MRZ: cambiando a "
                f"{NOMBRES_FORMATO[formato].lower()}"
            ),
        )

    # ------------------------------------------------------------------
    # Extraccion segun el formato
    # ------------------------------------------------------------------
    _avisar(progreso, etapa="extrayendo", formato=formato)

    texto = texto_de(lineas_pagina)
    avisos: list[str] = []
    errores: list[str] = []
    edad = None
    datos_mrz = None

    if formato == FORMATO_DIGITAL:
        lineas_mrz, caja_mrz, pagina_mrz = mrz
        alto_pagina = paginas[0].alto if paginas else 2000
        lectura = _digital.leer(
            lineas_pagina, lineas_mrz, caja_mrz, pagina_mrz, alto_pagina
        )

        campos = {
            "numero_documento": lectura.numero_documento,
            "nombre_completo": lectura.nombre_completo,
            "fecha_nacimiento": lectura.fecha_nacimiento,
            "sexo": lectura.sexo,
        }
        avisos = lectura.avisos
        errores = lectura.errores
        edad = lectura.edad
        datos_mrz = {
            "lineas": lectura.lineas_mrz,
            "valido": lectura.mrz_valido,
            "nacionalidad": lectura.nacionalidad,
        }
    else:
        alto_pagina = paginas[0].alto if paginas else 2000
        lectura = _amarilla.leer(lineas_pagina, datos_pdf417, alto_pagina)

        campos = {
            "numero_documento": lectura.numero_documento,
            "nombre_completo": lectura.nombre_completo,
            "fecha_nacimiento": lectura.fecha_nacimiento,
            "sexo": lectura.sexo,
        }
        avisos = lectura.avisos

        if not lectura.nombre_completo.valor and not lectura.numero_documento.valor:
            formato = FORMATO_DESCONOCIDO
            errores.append(
                "No se pudo leer ni el numero ni el nombre del documento. "
                "Puede que no sea una cedula, o que la imagen tenga muy "
                "poca resolucion."
            )

    resultado = ResultadoCedula(
        formato=formato,
        formato_nombre=NOMBRES_FORMATO[formato],
        campos={
            nombre: _campo_a_dict(campo, paginas) for nombre, campo in campos.items()
        },
        paginas=paginas,
        avisos=avisos,
        errores=errores,
        texto_ocr=texto,
        mrz=datos_mrz,
        edad=edad,
    )

    _avisar(progreso, etapa="listo", formato=formato)

    return resultado
