"""
Check_U - Panel de pruebas locales
-----------------------------------
Backend Flask que conecta los modulos ya existentes del repo
(modules/ocr_module, modules/mrz, modules/check_id) para procesar
una Cedula paso a paso (OCR + MRZ) y consultar el RUI con el
numero de documento obtenido.

Ejecutar:
    python webapp/app.py
Luego abrir http://localhost:5000
"""

import io
import json
import queue
import re
import sys
import threading
import time
import unicodedata
import uuid
from datetime import datetime, date
from pathlib import Path

from flask import Flask, request, jsonify, Response, render_template, stream_with_context

# --------------------------------------------------------------------------
# Hacer visible el paquete "modules" del repo (raiz del proyecto)
# --------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from modules.ocr_module.loaders.pdf_loader import load_pdf  # respaldo (poppler)
from modules.ocr_module.preprocess.image_cleaner import ImageCleaner
from modules.ocr_module.preprocess.check_inclination import SkewDetector
from modules.ocr_module.ocr.tesseract_engine import TesseractEngine
from modules.ocr_module.postprocess.cleaner import TextCleaner

from modules.mrz.normalize import normalize_line, MRZ_ALLOWED
from modules.mrz.get_info import get_info as mrz_get_info
from modules.mrz.validate import validate_mrz

from modules.check_id.rui.consultar import consultar as consultar_rui

from PIL import Image

# IMPORTANTE: Image.frombytes() (usado en la carga con PyMuPDF, mas abajo)
# no registra los plugins de Pillow (a diferencia de Image.open(), que si
# lo hace de forma perezosa). Sin este Image.init() explicito, el paso de
# "procesando" fallaba con KeyError: 'JPEG' al generar el PDF de depuracion
# en preprocess/image_cleaner.py (create_image_stage_pdf -> img.save(...)),
# porque el encoder JPEG de Pillow nunca quedaba registrado.
Image.init()

APP_DIR = Path(__file__).resolve().parent
HISTORIAL_PATH = APP_DIR / "historial.json"
HISTORIAL_LOCK = threading.Lock()

app = Flask(__name__)

JOBS = {}
JOBS_LOCK = threading.Lock()

# Motores reutilizables (sin estado relevante entre llamadas)
image_cleaner = ImageCleaner(resize_width=2000)
skew_detector = SkewDetector()
ocr_engine = TesseractEngine()
text_cleaner = TextCleaner()


# ============================================================================
# UTILIDADES DE HISTORIAL
# ============================================================================

def leer_historial():
    with HISTORIAL_LOCK:
        if not HISTORIAL_PATH.exists():
            return []
        try:
            return json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []


def guardar_en_historial(registro):
    with HISTORIAL_LOCK:
        data = []
        if HISTORIAL_PATH.exists():
            try:
                data = json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
            except Exception:
                data = []
        data.insert(0, registro)
        HISTORIAL_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )


# ============================================================================
# CARGA DE ARCHIVOS (PDF o IMAGEN)
# ----------------------------------------------------------------------------
# IMPORTANTE: se intenta PRIMERO con PyMuPDF (no depende de ningun binario
# externo instalado en el sistema) y solo si eso falla se intenta con
# poppler (pdf2image), que es lo que ya usaba el resto del proyecto.
# Asi el panel funciona aunque poppler no este instalado/en el PATH.
# ============================================================================

def cargar_paginas(file_bytes: bytes, filename: str):
    """Devuelve una lista de imagenes PIL a partir de un PDF o una imagen suelta."""
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()

    if ext == "pdf":
        error_pymupdf = None
        try:
            return _cargar_pdf_con_pymupdf(file_bytes)
        except Exception as e:
            error_pymupdf = e

        try:
            return load_pdf(file_bytes)
        except Exception as error_poppler:
            raise RuntimeError(
                "No se pudo leer el PDF. Con PyMuPDF: "
                f"{error_pymupdf}. Con poppler: {error_poppler}. "
                "Instala la libreria con 'pip install pymupdf' dentro del venv."
            )

    # Imagen suelta (png, jpg, jpeg, etc.)
    img = Image.open(io.BytesIO(file_bytes))
    img = img.convert("RGB")
    return [img]


def _cargar_pdf_con_pymupdf(file_bytes: bytes, dpi: int = 200):
    import pymupdf

    paginas = []
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    zoom = dpi / 72.0
    matriz = pymupdf.Matrix(zoom, zoom)

    for pagina in doc:
        pix = pagina.get_pixmap(matrix=matriz, colorspace=pymupdf.csRGB, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        paginas.append(img)

    doc.close()

    if not paginas:
        raise RuntimeError("El PDF no tiene paginas legibles.")

    return paginas


# ============================================================================
# MRZ: localizar y parsear dentro del texto OCR crudo
# ============================================================================

def buscar_lineas_mrz(raw_text: str):
    """
    Busca, dentro del texto OCR crudo, las 3 lineas que probablemente
    correspondan al MRZ (franja inferior de la cedula).

    Heuristica tolerante a errores de OCR: no exige exactamente 30
    caracteres, ajusta (rellena/recorta) para intentar el parseo.
    """
    candidatas = []

    for linea in raw_text.split("\n"):
        limpia = normalize_line(linea)
        if len(limpia) < 20:
            continue
        # Señal fuerte de MRZ real: relleno con "<" (no basta con ser
        # texto en mayúsculas sin acentos, que también sobrevive al filtro).
        if "<" not in limpia:
            continue
        candidatas.append(limpia)

    if len(candidatas) < 3:
        return None

    # Nos quedamos con las 3 ultimas candidatas (la MRZ suele ir al final)
    tres = candidatas[-3:]

    ajustadas = []
    for linea in tres:
        if len(linea) > 30:
            linea = linea[:30]
        elif len(linea) < 30:
            linea = linea.ljust(30, "<")
        ajustadas.append(linea)

    return ajustadas


def calcular_edad(anio: int, mes: int, dia: int):
    try:
        nacimiento = date(anio, mes, dia)
    except ValueError:
        return None
    hoy = date.today()
    edad = hoy.year - nacimiento.year - (
        (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day)
    )
    return edad


def procesar_mrz(raw_text: str):
    lineas = buscar_lineas_mrz(raw_text)
    if not lineas:
        return {"encontrado": False}

    mrz_texto = "\n".join(lineas)

    try:
        info = mrz_get_info(mrz_texto)
    except Exception as e:
        return {"encontrado": False, "error": str(e), "lineas": lineas}

    validacion = validate_mrz(mrz_texto)

    try:
        anio = int(info.birth_year)
        mes = int(info.birth_month)
        dia = int(info.birth_day)
        edad = calcular_edad(anio, mes, dia)

        # get_info.py siempre antepone "20" al año (asume nacidos en 2000+).
        # Si eso da una fecha futura, es alguien nacido en 1900+.
        if edad is not None and edad < 0:
            anio -= 100
            edad = calcular_edad(anio, mes, dia)

        fecha_nacimiento = f"{dia:02d}/{mes:02d}/{anio}"
    except Exception:
        edad = None
        fecha_nacimiento = None

    nombre_completo = f"{info.given_names} {info.surname}".strip()

    return {
        "encontrado": True,
        "valido": validacion.valid,
        "avisos": validacion.warnings,
        "errores": validacion.errors,
        "nombre_completo": nombre_completo,
        "numero_documento": info.document_number.replace("<", "").strip(),
        "fecha_nacimiento": fecha_nacimiento,
        "edad": edad,
        "sexo": info.sex,
        "lineas": lineas,
    }


# ============================================================================
# MOTOR DE PROCESAMIENTO (con eventos paso a paso)
# ============================================================================

ETAPAS = [
    ("leyendo", "Leyendo documento"),
    ("convirtiendo", "Convirtiendo"),
    ("procesando", "Procesando imagen"),
    ("inclinacion", "Corrigiendo inclinacion"),
    ("limpiando", "OCR y limpieza de texto"),
]


def emitir(q, **kwargs):
    q.put(kwargs)


def procesar_cedula(q, file_bytes, filename):
    target = "cedula"
    try:
        # ---------------- Leyendo ----------------
        emitir(q, type="stage", target=target, stage="leyendo", status="start")
        time.sleep(0.15)
        emitir(q, type="stage", target=target, stage="leyendo", status="done")

        # ---------------- Convirtiendo ----------------
        emitir(q, type="stage", target=target, stage="convirtiendo", status="start")
        paginas = cargar_paginas(file_bytes, filename)
        emitir(
            q, type="stage", target=target, stage="convirtiendo", status="done",
            detail=f"{len(paginas)} pagina(s)"
        )

        raw_text_total = ""
        raw_text_mrz_total = ""

        for pagina in paginas:

            # ---------------- Procesando (preprocesamiento de imagen) ----------------
            emitir(q, type="stage", target=target, stage="procesando", status="start")
            limpia = image_cleaner.clean_image(pagina)
            emitir(q, type="stage", target=target, stage="procesando", status="done")

            # ---------------- Corrigiendo inclinacion ----------------
            emitir(q, type="stage", target=target, stage="inclinacion", status="start")
            angulo = skew_detector.detect_skew(limpia)
            if abs(angulo) > 0.5:
                limpia, angulo = skew_detector.auto_correct(limpia)
            emitir(
                q, type="stage", target=target, stage="inclinacion", status="done",
                detail=f"{angulo:.2f} grados"
            )

            # ---------------- Limpiando (OCR + limpieza texto) ----------------
            emitir(q, type="stage", target=target, stage="limpiando", status="start")
            texto = ocr_engine.extract_text_with_confidence(limpia, min_confidence=40)
            raw_text_total += texto + "\n"

            # Segunda pasada de OCR sin filtro de confianza, solo para
            # buscar el MRZ: la franja del MRZ es una cadena rara de
            # letras/digitos/"<" que Tesseract suele calificar con baja
            # confianza por palabra (aunque lea bien los caracteres), asi
            # que el filtro min_confidence=40 puede borrar la linea entera
            # antes de que buscar_lineas_mrz() la vea.
            texto_mrz = ocr_engine.extract_text_with_confidence(limpia, min_confidence=0)
            raw_text_mrz_total += texto_mrz + "\n"
            emitir(q, type="stage", target=target, stage="limpiando", status="done")

        texto_limpio = text_cleaner.clean(raw_text_total)

        mrz_info = procesar_mrz(raw_text_total)
        if not mrz_info.get("encontrado"):
            mrz_info = procesar_mrz(raw_text_mrz_total)

        resultado = {
            "raw_text": raw_text_total,
            "text": texto_limpio,
            "mrz": mrz_info,
            "fields": {
                "nombre_completo": mrz_info.get("nombre_completo") if mrz_info.get("encontrado") else None,
                "numero_documento": mrz_info.get("numero_documento") if mrz_info.get("encontrado") else None,
                "fecha_nacimiento": mrz_info.get("fecha_nacimiento") if mrz_info.get("encontrado") else None,
                "edad": mrz_info.get("edad") if mrz_info.get("encontrado") else None,
                "sexo": mrz_info.get("sexo") if mrz_info.get("encontrado") else None,
            },
        }

        emitir(q, type="result", target=target, result=resultado)
        return resultado

    except Exception as e:
        emitir(q, type="error", target=target, message=str(e))
        return None


def hilo_trabajo(job_id, ced_bytes, ced_name):
    q = JOBS[job_id]["queue"]

    resultado_ced = procesar_cedula(q, ced_bytes, ced_name)

    # ---------------- Consulta RUI ----------------
    numero_para_rui = None
    if resultado_ced is not None:
        numero_para_rui = (resultado_ced.get("fields") or {}).get("numero_documento")

    rui_resultado = None

    if numero_para_rui:
        emitir(q, type="rui", status="start", numero=numero_para_rui)
        try:
            rui_resultado = consultar_rui({"id": numero_para_rui})
            emitir(q, type="rui", status="done", success=True, data=rui_resultado)
        except Exception as e:
            emitir(q, type="rui", status="done", success=False, error=str(e))
    else:
        emitir(q, type="rui", status="skipped", message="No se obtuvo un numero de documento (MRZ) para consultar.")

    # ---------------- Historial ----------------
    campos = (resultado_ced or {}).get("fields") or {}

    registro = {
        "id": job_id,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nombre": campos.get("nombre_completo") or "(sin determinar)",
        "numero_documento": campos.get("numero_documento") or "(sin determinar)",
        "fecha_nacimiento": campos.get("fecha_nacimiento"),
        "edad": campos.get("edad"),
        "sexo": campos.get("sexo"),
        "cedula_archivo": ced_name,
        "mrz_valido": (resultado_ced or {}).get("mrz", {}).get("valido"),
        "rui": rui_resultado,
    }
    guardar_en_historial(registro)
    emitir(q, type="historial_actualizado")

    emitir(q, type="done")
    q.put(None)  # sentinel para cerrar el stream


# ============================================================================
# RUTAS
# ============================================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/jobs", methods=["POST"])
def crear_job():
    if "cedula" not in request.files:
        return jsonify({"error": "Se requiere el archivo de la cedula."}), 400

    ced_file = request.files["cedula"]
    ced_bytes = ced_file.read()

    job_id = uuid.uuid4().hex[:12]
    q = queue.Queue()

    with JOBS_LOCK:
        JOBS[job_id] = {"queue": q}

    hilo = threading.Thread(
        target=hilo_trabajo,
        args=(job_id, ced_bytes, ced_file.filename),
        daemon=True,
    )
    hilo.start()

    return jsonify({"job_id": job_id})


@app.route("/api/jobs/<job_id>/stream")
def stream_job(job_id):
    if job_id not in JOBS:
        return jsonify({"error": "job no encontrado"}), 404

    q = JOBS[job_id]["queue"]

    def generar():
        while True:
            evento = q.get()
            if evento is None:
                break
            yield f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"
        with JOBS_LOCK:
            JOBS.pop(job_id, None)

    return Response(stream_with_context(generar()), mimetype="text/event-stream")


@app.route("/api/historial")
def api_historial():
    return jsonify(leer_historial())


if __name__ == "__main__":
    print("Check_U webapp: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
