"""
Check_U - Panel de validacion documental
=========================================

Backend Flask del panel. Conecta los modulos del repo
(modules/cedula, modules/ocr_module, modules/mrz, modules/check_id) en
un flujo de trabajo pensado para ir rapido:

    se suelta un documento -> se abre su pestaña -> se procesa solo ->
    se consulta el RUI -> se valida -> se compara con los documentos que
    ya estaban en el caso.

Conceptos
---------

**Caso**: una solicitud, es decir una persona con los documentos que
presento. Vive en disco (webapp/data/casos/<id>/), asi que se puede
cerrar el navegador y retomarlo despues desde el historial, agregando o
reemplazando documentos.

**Documento**: un archivo dentro de un caso. Hoy solo cedula; el formato
de inscripcion del proyecto contempla ademas evaluacion de grado,
estampilla Pro-Cultura, Saber Pro y Paz y Salvo, por eso el documento ya
guarda un "tipo" y las comparaciones estan escritas para N documentos,
no para dos fijos.

**Validacion**: el nombre que se leyo del documento contra el nombre que
devuelve el RUI del DNP, con un minimo de 85 % de similitud. De ahi sale
el estado de la solicitud (valida / inconsistente / por revisar), que es
lo que permite no mandar a revision manual lo que ya se sabe que esta
mal o incompleto.

Ejecutar:
    python webapp/app.py        (o .\\iniciar.ps1 desde la raiz)
Luego abrir http://localhost:5000
"""

import io
import json
import queue
import shutil
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_file,
    stream_with_context,
)

# --------------------------------------------------------------------------
# Hacer visible el paquete "modules" del repo (raiz del proyecto)
# --------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# El verificador de entorno se importa primero y aparte: si falta un
# paquete de Python (opencv, por ejemplo), las importaciones de abajo
# reventarian con un traceback crudo antes de poder explicar que pasa.
from entorno import verificar_entorno, imprimir_reporte  # noqa: E402

try:
    import cv2
    from PIL import Image

    from modules.cedula import leer_cedula
    from modules.cedula.similitud import (
        UMBRAL_SIMILITUD,
        comparar_nombres,
        comparar_numeros,
    )
    from modules.check_id.rui.consultar import consultar as consultar_rui
except ImportError as e:
    print("=" * 70)
    print("Check_U: falta un paquete de Python para poder arrancar.")
    print("=" * 70)
    print(f"\nDetalle: {e}")
    print(
        "\nSolucion: corre '.\\iniciar.ps1' de nuevo (reinstala lo que "
        "falte en el venv), o instala el paquete que falta a mano con "
        "pip dentro del venv."
    )
    print("=" * 70)
    sys.exit(1)

# Image.frombytes() (que usa la carga con PyMuPDF) no registra los
# plugins de Pillow, a diferencia de Image.open(). Sin este init
# explicito, guardar un JPEG despues falla con KeyError: 'JPEG'.
Image.init()

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
CASOS_DIR = DATA_DIR / "casos"
CASOS_DIR.mkdir(parents=True, exist_ok=True)

DISCO = threading.Lock()

app = Flask(__name__)

TRABAJOS = {}
TRABAJOS_LOCK = threading.Lock()

EXTENSIONES = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


# ============================================================================
# ALMACENAMIENTO DE CASOS
# ----------------------------------------------------------------------------
# Todo en archivos JSON dentro de webapp/data/. Es deliberado: el panel
# corre en local, en la maquina de quien revisa, y meter una base de
# datos solo para esto agregaria una dependencia mas que instalar y
# mantener. Cada caso es una carpeta autocontenida, asi que se puede
# copiar, respaldar o borrar a mano sin romper nada.
# ============================================================================

def _ruta_caso(caso_id: str) -> Path:
    return CASOS_DIR / caso_id


def _ruta_meta(caso_id: str) -> Path:
    return _ruta_caso(caso_id) / "caso.json"


def leer_caso(caso_id: str) -> dict | None:
    ruta = _ruta_meta(caso_id)
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return None


def guardar_caso(caso: dict) -> None:
    with DISCO:
        ruta = _ruta_caso(caso["id"])
        ruta.mkdir(parents=True, exist_ok=True)
        caso["actualizado"] = datetime.now().isoformat(timespec="seconds")
        _ruta_meta(caso["id"]).write_text(
            json.dumps(caso, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def crear_caso() -> dict:
    caso = {
        "id": uuid.uuid4().hex[:12],
        "titulo": None,
        "creado": datetime.now().isoformat(timespec="seconds"),
        "documentos": [],
        "comparaciones": [],
    }
    guardar_caso(caso)
    return caso


def listar_casos() -> list[dict]:
    casos = []
    for carpeta in CASOS_DIR.iterdir():
        if not carpeta.is_dir():
            continue
        caso = leer_caso(carpeta.name)
        if not caso:
            continue

        # Un caso sin documentos no le sirve de nada a nadie en el
        # historial (queda como "(sin identificar), 0 documentos").
        if not caso.get("documentos"):
            continue

        casos.append(
            {
                "id": caso["id"],
                "titulo": caso.get("titulo") or "(sin identificar)",
                "creado": caso.get("creado"),
                "actualizado": caso.get("actualizado"),
                "documentos": len(caso.get("documentos", [])),
                "estado": estado_del_caso(caso),
            }
        )

    casos.sort(key=lambda c: c.get("actualizado") or "", reverse=True)
    return casos


def estado_del_caso(caso: dict) -> str:
    """
    Estado global de la solicitud, con la misma nomenclatura del formato
    de inscripcion del proyecto. Manda el peor estado de sus documentos:
    basta un documento inconsistente para que la solicitud no pueda
    avanzar.
    """
    documentos = caso.get("documentos", [])
    if not documentos:
        return "vacia"

    estados = [
        (d.get("validacion") or {}).get("estado", "por_revisar") for d in documentos
    ]

    # Una discrepancia entre documentos tambien vuelve inconsistente el caso.
    for comparacion in caso.get("comparaciones", []):
        for campo in comparacion.get("campos", []):
            if campo.get("coincide") is False:
                return "inconsistente"

    if "inconsistente" in estados:
        return "inconsistente"
    if "por_revisar" in estados:
        return "por_revisar"
    return "valida"


# ============================================================================
# CARGA DE ARCHIVOS (PDF o IMAGEN)
# ----------------------------------------------------------------------------
# PyMuPDF primero (no depende de ningun binario externo) y poppler solo
# como respaldo. Asi el panel funciona aunque poppler no este instalado,
# que era un problema recurrente en Windows.
# ============================================================================

def cargar_paginas(datos: bytes, nombre_archivo: str) -> list:
    extension = Path(nombre_archivo).suffix.lower()

    if extension == ".pdf":
        error_pymupdf = None
        try:
            return _paginas_con_pymupdf(datos)
        except Exception as e:
            error_pymupdf = e

        try:
            from modules.ocr_module.loaders.pdf_loader import load_pdf

            return load_pdf(datos)
        except Exception as error_poppler:
            raise RuntimeError(
                f"No se pudo leer el PDF. Con PyMuPDF: {error_pymupdf}. "
                f"Con poppler: {error_poppler}."
            )

    return [Image.open(io.BytesIO(datos)).convert("RGB")]


def _paginas_con_pymupdf(datos: bytes, dpi: int = 200) -> list:
    import pymupdf

    doc = pymupdf.open(stream=datos, filetype="pdf")
    zoom = dpi / 72.0
    matriz = pymupdf.Matrix(zoom, zoom)

    paginas = []
    for pagina in doc:
        pix = pagina.get_pixmap(matrix=matriz, colorspace=pymupdf.csRGB, alpha=False)
        paginas.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    doc.close()

    if not paginas:
        raise RuntimeError("El PDF no tiene paginas legibles.")

    return paginas


# ============================================================================
# VALIDACION CONTRA EL RUI
# ============================================================================

def validar_contra_rui(campos: dict) -> tuple[dict, dict]:
    """
    Consulta el RUI con el numero extraido y compara el nombre.

    Devuelve (rui, validacion). Los tres estados posibles son los del
    formato de inscripcion del proyecto:

    - **valida**: el RUI encontro a la persona y el nombre coincide al
      menos en el umbral acordado (85 %).
    - **inconsistente**: el RUI la encontro pero el nombre NO coincide.
      Es el caso que hay que devolverle al estudiante antes de que llegue
      a revision manual.
    - **por_revisar**: no se pudo decidir automaticamente (no se leyo el
      numero, el RUI no respondio, o no hay registro). Requiere ojo
      humano, pero se sabe de antemano y no consume tiempo de revision a
      ciegas.
    """
    numero = (campos.get("numero_documento") or {}).get("valor")
    nombre = (campos.get("nombre_completo") or {}).get("valor")

    rui = {
        "consultado": False,
        "exito": False,
        "numero": numero,
        "nombre": None,
        "mensaje": None,
    }

    if not numero:
        return rui, {
            "estado": "por_revisar",
            "similitud": None,
            "umbral": UMBRAL_SIMILITUD,
            "detalle": (
                "No se pudo leer el numero de documento, asi que no se "
                "puede verificar contra el RUI."
            ),
        }

    rui["consultado"] = True
    try:
        respuesta = consultar_rui({"id": numero})
        rui["exito"] = bool(respuesta.get("success"))
        rui["mensaje"] = respuesta.get("message")
        rui["nombre"] = (respuesta.get("data") or {}).get("nombre_completo") or None
    except Exception as e:
        rui["mensaje"] = f"No se pudo consultar el RUI: {e}"
        return rui, {
            "estado": "por_revisar",
            "similitud": None,
            "umbral": UMBRAL_SIMILITUD,
            "detalle": rui["mensaje"],
        }

    if not rui["exito"] or not rui["nombre"]:
        return rui, {
            "estado": "por_revisar",
            "similitud": None,
            "umbral": UMBRAL_SIMILITUD,
            "detalle": (
                rui.get("mensaje")
                or "El RUI no devolvio informacion para ese numero de documento."
            ),
        }

    comparacion = comparar_nombres(nombre, rui["nombre"])

    if comparacion.coincide is None:
        return rui, {
            "estado": "por_revisar",
            "similitud": None,
            "umbral": UMBRAL_SIMILITUD,
            "detalle": "No se pudo leer el nombre del documento para compararlo.",
            "nombre_rui": rui["nombre"],
        }

    if comparacion.coincide:
        detalle = (
            f"El nombre del documento coincide con el del RUI "
            f"({comparacion.similitud:.0f} % de similitud)."
        )
        estado = "valida"
    else:
        detalle = (
            f"El nombre del documento ('{nombre}') no coincide con el del "
            f"RUI ('{rui['nombre']}'): {comparacion.similitud:.0f} % de "
            f"similitud, por debajo del minimo de {UMBRAL_SIMILITUD:.0f} %."
        )
        estado = "inconsistente"

    return rui, {
        "estado": estado,
        "similitud": comparacion.similitud,
        "umbral": UMBRAL_SIMILITUD,
        "detalle": detalle,
        "nombre_rui": rui["nombre"],
    }


# ============================================================================
# COMPARACION ENTRE DOCUMENTOS
# ============================================================================

CAMPOS_COMPARABLES = [
    ("numero_documento", "N° documento", comparar_numeros),
    ("nombre_completo", "Nombre completo", comparar_nombres),
]


def comparar_documentos(caso: dict) -> list[dict]:
    """
    Compara cada par de documentos del caso campo por campo.

    Se guarda la caja de cada lado para que la interfaz pueda dibujar la
    linea que une el dato de un documento con el del otro. Esta escrito
    para N documentos justamente porque ya vienen en camino los otros
    documentos de la solicitud de grado.
    """
    documentos = [d for d in caso.get("documentos", []) if d.get("campos")]
    comparaciones = []

    for i in range(len(documentos)):
        for j in range(i + 1, len(documentos)):
            a, b = documentos[i], documentos[j]
            campos = []

            for clave, etiqueta, comparador in CAMPOS_COMPARABLES:
                campo_a = a["campos"].get(clave) or {}
                campo_b = b["campos"].get(clave) or {}

                resultado = comparador(campo_a.get("valor"), campo_b.get("valor"))

                campos.append(
                    {
                        "campo": clave,
                        "etiqueta": etiqueta,
                        "valor_a": campo_a.get("valor"),
                        "valor_b": campo_b.get("valor"),
                        "caja_a": campo_a.get("caja"),
                        "caja_b": campo_b.get("caja"),
                        "pagina_a": campo_a.get("pagina", 0),
                        "pagina_b": campo_b.get("pagina", 0),
                        "similitud": resultado.similitud,
                        "coincide": resultado.coincide,
                        "umbral": resultado.umbral,
                    }
                )

            comparaciones.append(
                {
                    "documento_a": a["id"],
                    "documento_b": b["id"],
                    "nombre_a": a.get("nombre_archivo"),
                    "nombre_b": b.get("nombre_archivo"),
                    "campos": campos,
                }
            )

    return comparaciones


# ============================================================================
# PROCESAMIENTO DE UN DOCUMENTO
# ============================================================================

def emitir(cola, **datos):
    cola.put(datos)


def procesar_documento(cola, caso_id: str, documento_id: str, datos: bytes, nombre: str):
    carpeta = _ruta_caso(caso_id) / "documentos" / documento_id
    carpeta.mkdir(parents=True, exist_ok=True)

    try:
        emitir(cola, tipo="etapa", etapa="cargando", documento=documento_id)
        paginas = cargar_paginas(datos, nombre)

        def progreso(evento):
            evento = dict(evento)
            evento["tipo"] = "progreso"
            evento["documento"] = documento_id
            cola.put(evento)

        resultado = leer_cedula(paginas, progreso=progreso)

        # --- Guardar las imagenes que la interfaz muestra de fondo ---
        paginas_json = []
        for pagina in resultado.paginas:
            archivo = carpeta / f"pagina_{pagina.indice}.jpg"
            cv2.imwrite(str(archivo), pagina.display, [cv2.IMWRITE_JPEG_QUALITY, 82])
            paginas_json.append(
                {
                    "indice": pagina.indice,
                    "ancho": pagina.ancho,
                    "alto": pagina.alto,
                    "url": f"/api/casos/{caso_id}/documentos/{documento_id}/paginas/{pagina.indice}",
                }
            )

        emitir(cola, tipo="paginas", documento=documento_id, paginas=paginas_json)

        # --- Consulta al RUI y validacion ---
        emitir(cola, tipo="etapa", etapa="rui", documento=documento_id)
        rui, validacion = validar_contra_rui(resultado.campos)

        documento = {
            "id": documento_id,
            "nombre_archivo": nombre,
            "tipo": "cedula",
            "formato": resultado.formato,
            "formato_nombre": resultado.formato_nombre,
            "paginas": paginas_json,
            "campos": resultado.campos,
            "edad": resultado.edad,
            "mrz": resultado.mrz,
            "avisos": resultado.avisos,
            "errores": resultado.errores,
            "rui": rui,
            "validacion": validacion,
            "creado": datetime.now().isoformat(timespec="seconds"),
        }

        (carpeta / "resultado.json").write_text(
            json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # --- Guardar en el caso y recomparar ---
        caso = leer_caso(caso_id) or crear_caso()
        caso["documentos"] = [
            d for d in caso.get("documentos", []) if d["id"] != documento_id
        ]
        caso["documentos"].append(documento)

        # El caso se titula con el nombre de la persona apenas se sepa.
        nombre_persona = (resultado.campos.get("nombre_completo") or {}).get("valor")
        if nombre_persona and not caso.get("titulo"):
            caso["titulo"] = nombre_persona

        caso["comparaciones"] = comparar_documentos(caso)
        guardar_caso(caso)

        emitir(cola, tipo="documento", documento=documento_id, datos=documento)
        emitir(
            cola,
            tipo="comparaciones",
            comparaciones=caso["comparaciones"],
            estado=estado_del_caso(caso),
            titulo=caso.get("titulo"),
        )

    except Exception as e:
        emitir(cola, tipo="error", documento=documento_id, mensaje=str(e))

    finally:
        emitir(cola, tipo="fin", documento=documento_id)
        cola.put(None)


# ============================================================================
# RUTAS
# ============================================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/casos", methods=["GET"])
def api_listar_casos():
    return jsonify(listar_casos())


@app.route("/api/casos", methods=["POST"])
def api_crear_caso():
    return jsonify(crear_caso())


@app.route("/api/casos/<caso_id>", methods=["GET"])
def api_caso(caso_id):
    caso = leer_caso(caso_id)
    if not caso:
        return jsonify({"error": "caso no encontrado"}), 404

    caso["estado"] = estado_del_caso(caso)
    return jsonify(caso)


@app.route("/api/casos/<caso_id>", methods=["DELETE"])
def api_borrar_caso(caso_id):
    carpeta = _ruta_caso(caso_id)
    if carpeta.exists():
        shutil.rmtree(carpeta, ignore_errors=True)
    return jsonify({"ok": True})


@app.route("/api/casos/<caso_id>/documentos", methods=["POST"])
def api_subir_documento(caso_id):
    caso = leer_caso(caso_id)
    if not caso:
        return jsonify({"error": "caso no encontrado"}), 404

    if "archivo" not in request.files:
        return jsonify({"error": "falta el archivo"}), 400

    archivo = request.files["archivo"]
    nombre = archivo.filename or "documento"

    if Path(nombre).suffix.lower() not in EXTENSIONES:
        return jsonify(
            {
                "error": (
                    "Formato no admitido. Se aceptan PDF e imagenes "
                    "(png, jpg, webp, bmp, tif)."
                )
            }
        ), 400

    datos = archivo.read()
    if not datos:
        return jsonify({"error": "el archivo llego vacio"}), 400

    documento_id = uuid.uuid4().hex[:12]
    trabajo_id = uuid.uuid4().hex[:12]
    cola = queue.Queue()

    with TRABAJOS_LOCK:
        TRABAJOS[trabajo_id] = {"cola": cola}

    threading.Thread(
        target=procesar_documento,
        args=(cola, caso_id, documento_id, datos, nombre),
        daemon=True,
    ).start()

    return jsonify(
        {"documento_id": documento_id, "trabajo_id": trabajo_id, "nombre_archivo": nombre}
    )


@app.route("/api/casos/<caso_id>/documentos/<documento_id>", methods=["DELETE"])
def api_borrar_documento(caso_id, documento_id):
    caso = leer_caso(caso_id)
    if not caso:
        return jsonify({"error": "caso no encontrado"}), 404

    caso["documentos"] = [d for d in caso.get("documentos", []) if d["id"] != documento_id]
    caso["comparaciones"] = comparar_documentos(caso)
    guardar_caso(caso)

    shutil.rmtree(
        _ruta_caso(caso_id) / "documentos" / documento_id, ignore_errors=True
    )

    return jsonify(
        {
            "ok": True,
            "comparaciones": caso["comparaciones"],
            "estado": estado_del_caso(caso),
        }
    )


@app.route("/api/casos/<caso_id>/documentos/<documento_id>/paginas/<int:indice>")
def api_pagina(caso_id, documento_id, indice):
    archivo = (
        _ruta_caso(caso_id) / "documentos" / documento_id / f"pagina_{indice}.jpg"
    )
    if not archivo.exists():
        return jsonify({"error": "pagina no encontrada"}), 404
    return send_file(archivo, mimetype="image/jpeg")


@app.route("/api/trabajos/<trabajo_id>/stream")
def api_stream(trabajo_id):
    with TRABAJOS_LOCK:
        trabajo = TRABAJOS.get(trabajo_id)

    if not trabajo:
        return jsonify({"error": "trabajo no encontrado"}), 404

    cola = trabajo["cola"]

    def generar():
        while True:
            evento = cola.get()
            if evento is None:
                break
            yield f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"

        with TRABAJOS_LOCK:
            TRABAJOS.pop(trabajo_id, None)

    return Response(stream_with_context(generar()), mimetype="text/event-stream")


@app.route("/api/salud")
def api_salud():
    """
    Verifica el entorno (Tesseract, PyMuPDF/poppler, paquetes de Python)
    en caliente, para que el panel avise en pantalla si algo quedo mal
    configurado en vez de que el usuario se entere a mitad de un
    procesamiento.
    """
    problemas = verificar_entorno()
    return jsonify({"ok": not problemas, "problemas": problemas})


if __name__ == "__main__":
    # Verificacion ANTES de arrancar el servidor: si falta Tesseract, el
    # idioma español o una forma de leer PDF, se avisa aca con una
    # solucion concreta y no se arranca. Asi el problema aparece una sola
    # vez y claro, no a mitad de un procesamiento real.
    problemas_entorno = verificar_entorno()
    imprimir_reporte(problemas_entorno)
    if problemas_entorno:
        sys.exit(1)

    print("Check_U: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
