"""
Check_U - Panel de pruebas locales
-----------------------------------
Backend Flask que conecta los modulos ya existentes del repo
(modules/ocr_module, modules/mrz, modules/check_id) en un solo
flujo: subir un Documento (PDF tipo acta/ICFES) + una Cedula,
procesarlos con OCR paso a paso, comparar los campos entre ambos,
y consultar el RUI con el numero de documento obtenido.

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

from modules.ocr_module.loaders.pdf_loader import load_pdf
from modules.ocr_module.preprocess.image_cleaner import ImageCleaner
from modules.ocr_module.preprocess.check_inclination import SkewDetector, ensure_cv_image
from modules.ocr_module.ocr.tesseract_engine import TesseractEngine
from modules.ocr_module.postprocess.cleaner import TextCleaner
from modules.ocr_module.postprocess.structure import TextStructurer

from modules.mrz.normalize import normalize_line, MRZ_ALLOWED
from modules.mrz.get_info import get_info as mrz_get_info
from modules.mrz.validate import validate_mrz

from modules.check_id.rui.consultar import consultar as consultar_rui

from PIL import Image

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
structurer = TextStructurer()


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
# ============================================================================

def cargar_paginas(file_bytes: bytes, filename: str):
    """Devuelve una lista de imagenes PIL a partir de un PDF o una imagen suelta."""
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()

    if ext == "pdf":
        try:
            # Camino "estandar" del proyecto (usa poppler, igual que
            # modules/ocr_module/loaders/pdf_loader.py).
            return load_pdf(file_bytes)
        except Exception as e:
            # En Windows es comun que poppler no este instalado / en PATH.
            # En vez de tumbar el flujo, usamos PyMuPDF como respaldo:
            # no depende de ningun binario externo.
            if "poppler" not in str(e).lower() and "page count" not in str(e).lower():
                raise
            return _cargar_pdf_con_pymupdf(file_bytes)

    # Imagen suelta (png, jpg, jpeg, etc.)
    img = Image.open(io.BytesIO(file_bytes))
    img = img.convert("RGB")
    return [img]


def _cargar_pdf_con_pymupdf(file_bytes: bytes, dpi: int = 200):
    """Respaldo sin poppler: renderiza el PDF a imagenes con PyMuPDF."""
    import pymupdf

    paginas = []
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    zoom = dpi / 72.0
    matriz = pymupdf.Matrix(zoom, zoom)

    for pagina in doc:
        pix = pagina.get_pixmap(matrix=matriz)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        paginas.append(img)

    doc.close()
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
# NORMALIZACION PARA COMPARAR CAMPOS
# ============================================================================

def normalizar_texto(valor):
    if not valor:
        return ""
    valor = str(valor).upper().strip()
    valor = unicodedata.normalize("NFKD", valor)
    valor = "".join(c for c in valor if not unicodedata.combining(c))
    valor = re.sub(r"\s+", " ", valor)
    return valor


def normalizar_numero(valor):
    if not valor:
        return ""
    return re.sub(r"\D", "", str(valor)).lstrip("0")


def comparar_nombres(a, b):
    a_norm, b_norm = normalizar_texto(a), normalizar_texto(b)
    if not a_norm or not b_norm:
        return None
    if a_norm == b_norm:
        return True
    tokens_a = set(a_norm.split())
    tokens_b = set(b_norm.split())
    if not tokens_a or not tokens_b:
        return False
    interseccion = tokens_a & tokens_b
    menor = min(len(tokens_a), len(tokens_b))
    return len(interseccion) >= max(1, menor - 1)


def comparar_numeros(a, b):
    a_norm, b_norm = normalizar_numero(a), normalizar_numero(b)
    if not a_norm or not b_norm:
        return None
    return a_norm == b_norm


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


def procesar_documento(q, target, file_bytes, filename, tipo_documento):
    """
    target: "documento" | "cedula"
    tipo_documento: "acta_grado" | "icfes" | "cedula"
    """

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

        for idx, pagina in enumerate(paginas, start=1):

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
            emitir(q, type="stage", target=target, stage="limpiando", status="done")

        texto_limpio = text_cleaner.clean(raw_text_total)

        # ---------------- Extraccion de campos ----------------
        resultado = {
            "raw_text": raw_text_total,
            "text": texto_limpio,
        }

        if tipo_documento == "cedula":
            mrz_info = procesar_mrz(raw_text_total)
            resultado["mrz"] = mrz_info
            resultado["fields"] = {
                "nombre_completo": mrz_info.get("nombre_completo") if mrz_info.get("encontrado") else None,
                "numero_documento": mrz_info.get("numero_documento") if mrz_info.get("encontrado") else None,
                "fecha_nacimiento": mrz_info.get("fecha_nacimiento") if mrz_info.get("encontrado") else None,
                "edad": mrz_info.get("edad") if mrz_info.get("encontrado") else None,
                "sexo": mrz_info.get("sexo") if mrz_info.get("encontrado") else None,
            }
        else:
            extraido = structurer.extract_key_fields(texto_limpio, tipo_documento)
            resultado["fields"] = extraido.get("fields", {})
            resultado["document_type"] = extraido.get("document_type")

        emitir(q, type="result", target=target, result=resultado)
        return resultado

    except Exception as e:
        emitir(q, type="error", target=target, message=str(e))
        return None


def hilo_trabajo(job_id, doc_bytes, doc_name, doc_tipo, ced_bytes, ced_name):
    q = JOBS[job_id]["queue"]

    resultado_doc = procesar_documento(q, "documento", doc_bytes, doc_name, doc_tipo)
    resultado_ced = procesar_documento(q, "cedula", ced_bytes, ced_name, "cedula")

    # ---------------- Comparacion ----------------
    filas = []

    if resultado_doc is not None and resultado_ced is not None:
        f_doc = resultado_doc.get("fields", {}) or {}
        f_ced = resultado_ced.get("fields", {}) or {}

        nombre_doc = f_doc.get("nombre_completo")
        nombre_ced = f_ced.get("nombre_completo")
        filas.append({
            "campo": "Nombre completo",
            "documento": nombre_doc or "—",
            "cedula": nombre_ced or "—",
            "coincide": comparar_nombres(nombre_doc, nombre_ced),
        })

        num_doc = f_doc.get("numero_documento")
        num_ced = f_ced.get("numero_documento")
        filas.append({
            "campo": "Numero de documento",
            "documento": num_doc or "—",
            "cedula": num_ced or "—",
            "coincide": comparar_numeros(num_doc, num_ced),
        })

        filas.append({
            "campo": "Fecha de nacimiento",
            "documento": "—",
            "cedula": f_ced.get("fecha_nacimiento") or "—",
            "coincide": None,
        })

        filas.append({
            "campo": "Edad",
            "documento": "—",
            "cedula": (str(f_ced.get("edad")) if f_ced.get("edad") is not None else "—"),
            "coincide": None,
        })

        if f_doc.get("institucion_educativa"):
            filas.append({
                "campo": "Institucion educativa",
                "documento": f_doc.get("institucion_educativa") or "—",
                "cedula": "—",
                "coincide": None,
            })

    emitir(q, type="comparison", rows=filas)

    # ---------------- Consulta RUI ----------------
    numero_para_rui = None
    if resultado_ced is not None:
        numero_para_rui = (resultado_ced.get("fields") or {}).get("numero_documento")
    if not numero_para_rui and resultado_doc is not None:
        numero_para_rui = (resultado_doc.get("fields") or {}).get("numero_documento")

    rui_resultado = None

    if numero_para_rui:
        emitir(q, type="rui", status="start", numero=numero_para_rui)
        try:
            rui_resultado = consultar_rui({"id": numero_para_rui})
            emitir(q, type="rui", status="done", success=True, data=rui_resultado)
        except Exception as e:
            emitir(q, type="rui", status="done", success=False, error=str(e))
    else:
        emitir(q, type="rui", status="skipped", message="No se obtuvo un numero de documento para consultar.")

    # ---------------- Historial ----------------
    nombre_final = None
    if resultado_ced is not None:
        nombre_final = (resultado_ced.get("fields") or {}).get("nombre_completo")
    if not nombre_final and resultado_doc is not None:
        nombre_final = (resultado_doc.get("fields") or {}).get("nombre_completo")

    registro = {
        "id": job_id,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nombre": nombre_final or "(sin determinar)",
        "numero_documento": numero_para_rui or "(sin determinar)",
        "tipo_documento": doc_tipo,
        "documento_archivo": doc_name,
        "cedula_archivo": ced_name,
        "rui": rui_resultado,
        "coincidencias": filas,
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
    if "documento" not in request.files or "cedula" not in request.files:
        return jsonify({"error": "Se requieren los dos archivos: documento y cedula."}), 400

    doc_file = request.files["documento"]
    ced_file = request.files["cedula"]
    doc_tipo = request.form.get("documento_tipo", "acta_grado")

    doc_bytes = doc_file.read()
    ced_bytes = ced_file.read()

    job_id = uuid.uuid4().hex[:12]
    q = queue.Queue()

    with JOBS_LOCK:
        JOBS[job_id] = {"queue": q}

    hilo = threading.Thread(
        target=hilo_trabajo,
        args=(job_id, doc_bytes, doc_file.filename, doc_tipo, ced_bytes, ced_file.filename),
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
