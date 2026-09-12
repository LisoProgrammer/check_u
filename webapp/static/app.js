// ============================================================
// Check_U - Panel de administrador (frontend)
// ============================================================

let archivoCedula = null;
let entornoOk = true; // se confirma con /api/salud apenas carga la pagina

function actualizarBotonProcesar() {
    document.getElementById("btn-procesar").disabled = !(archivoCedula && entornoOk);
}

// ------------------------------------------------------------
// VERIFICACION DE ENTORNO (Tesseract / PyMuPDF-poppler / paquetes)
// ------------------------------------------------------------
async function verificarEntorno() {
    const banner = document.getElementById("banner-entorno");
    const lista = document.getElementById("banner-entorno-lista");
    try {
        const resp = await fetch("/api/salud");
        const datos = await resp.json();
        entornoOk = datos.ok;

        if (datos.ok) {
            banner.hidden = true;
        } else {
            lista.innerHTML = datos.problemas.map((p) => `
                <li><strong>${p.componente}:</strong> ${p.detalle}
                    <div class="banner-entorno-solucion">${p.solucion}</div>
                </li>`).join("");
            banner.hidden = false;
        }
    } catch (e) {
        // Si ni siquiera responde /api/salud, no molestamos con el banner:
        // el problema ya se habria visto al arrancar el servidor. Se asume
        // que el entorno esta bien para no bloquear el boton sin motivo.
        entornoOk = true;
    }
    actualizarBotonProcesar();
}

verificarEntorno();

// ------------------------------------------------------------
// TABS
// ------------------------------------------------------------
document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("activo"));
        document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("activo"));
        btn.classList.add("activo");
        document.getElementById("tab-" + btn.dataset.tab).classList.add("activo");
        if (btn.dataset.tab === "historial") cargarHistorial();
    });
});

// ------------------------------------------------------------
// DROPZONE (cedula)
// ------------------------------------------------------------
function configurarDropzone() {
    const zona = document.querySelector('.dropzone[data-target="cedula"]');
    const input = document.getElementById("input-cedula");

    const asignarArchivo = (file) => {
        if (!file) return;
        archivoCedula = file;
        zona.classList.add("tiene-archivo");
        zona.querySelector(".nombre-archivo").textContent = file.name;
        actualizarBotonProcesar();
    };

    zona.addEventListener("click", () => input.click());
    input.addEventListener("change", (e) => asignarArchivo(e.target.files[0]));

    ["dragenter", "dragover"].forEach((ev) =>
        zona.addEventListener(ev, (e) => {
            e.preventDefault();
            zona.classList.add("dragover");
        })
    );
    ["dragleave", "drop"].forEach((ev) =>
        zona.addEventListener(ev, (e) => {
            e.preventDefault();
            zona.classList.remove("dragover");
        })
    );
    zona.addEventListener("drop", (e) => {
        const file = e.dataTransfer.files[0];
        if (file) asignarArchivo(file);
    });
}

configurarDropzone();

// ------------------------------------------------------------
// PASOS / PROGRESO
// ------------------------------------------------------------
const ETAPAS = ["leyendo", "convirtiendo", "procesando", "inclinacion", "limpiando"];

function marcarEtapa(stage, status) {
    const li = document.querySelector(`#pasos-cedula li[data-stage="${stage}"]`);
    if (!li) return;
    li.classList.remove("en-progreso", "completado");
    li.classList.add(status === "done" ? "completado" : "en-progreso");

    if (status === "done") {
        const idx = ETAPAS.indexOf(stage);
        const pct = Math.round(((idx + 1) / ETAPAS.length) * 100);
        document.getElementById("barra-cedula").style.width = pct + "%";
    }
}

function reiniciarPasos() {
    document.querySelectorAll("#pasos-cedula li").forEach((li) => {
        li.classList.remove("en-progreso", "completado");
    });
    document.getElementById("barra-cedula").style.width = "0%";

    const caja = document.getElementById("resultado-cedula");
    caja.innerHTML = `<p class="resultado-vacio">Procesando…</p>`;
}

// ------------------------------------------------------------
// RENDER DE RESULTADOS
// ------------------------------------------------------------
function etiquetaCampo(clave) {
    const mapa = {
        nombre_completo: "Nombre",
        numero_documento: "N° documento",
        fecha_nacimiento: "Fecha nacimiento",
        edad: "Edad",
        sexo: "Sexo",
    };
    return mapa[clave] || clave;
}

function renderResultado(resultado) {
    const caja = document.getElementById("resultado-cedula");
    const campos = resultado.fields || {};

    let html = "<dl>";
    for (const [clave, valor] of Object.entries(campos)) {
        html += `<dt>${etiquetaCampo(clave)}</dt><dd>${valor !== null && valor !== undefined ? valor : "—"}</dd>`;
    }
    html += "</dl>";

    if (resultado.mrz) {
        if (!resultado.mrz.encontrado) {
            html += `<div class="aviso">No se pudo localizar/leer el MRZ en la imagen.</div>`;
        } else if (!resultado.mrz.valido) {
            html += `<div class="aviso">MRZ leído, pero los dígitos de verificación no cuadran (posible error de OCR).</div>`;
        }
    }

    caja.innerHTML = html;
}

// ------------------------------------------------------------
// RUI
// ------------------------------------------------------------
function reiniciarRui() {
    document.getElementById("seccion-rui").hidden = true;
    document.getElementById("rui-cargando").hidden = true;
    document.getElementById("rui-ok").hidden = true;
    document.getElementById("rui-error").hidden = true;
    document.getElementById("rui-datos").hidden = true;
    document.getElementById("rui-datos").innerHTML = "";
}

function mostrarSoloEstadoRui(idVisible) {
    // Un solo estado del RUI visible a la vez: spinner O check O error.
    ["rui-cargando", "rui-ok", "rui-error"].forEach((id) => {
        document.getElementById(id).hidden = id !== idVisible;
    });
}

function manejarEventoRui(evento) {
    document.getElementById("seccion-rui").hidden = false;

    if (evento.status === "start") {
        mostrarSoloEstadoRui("rui-cargando");
        return;
    }

    if (evento.status === "skipped") {
        mostrarSoloEstadoRui("rui-error");
        document.getElementById("rui-error-msg").textContent =
            evento.message || "No se pudo determinar un número de documento para consultar.";
        return;
    }

    if (evento.success) {
        mostrarSoloEstadoRui("rui-ok");
        const datos = evento.data || {};
        const info = datos.data || {};
        document.getElementById("rui-datos").hidden = false;
        document.getElementById("rui-datos").innerHTML = `
            <dl style="margin:0;display:grid;grid-template-columns:auto 1fr;gap:4px 10px;">
                <dt style="font-weight:600;">Mensaje</dt><dd>${datos.message || "—"}</dd>
                <dt style="font-weight:600;">N° documento</dt><dd>${info.id || "—"}</dd>
                <dt style="font-weight:600;">Nombre (RUI)</dt><dd>${info.nombre_completo || "—"}</dd>
            </dl>`;
    } else {
        mostrarSoloEstadoRui("rui-error");
        document.getElementById("rui-error-msg").textContent =
            "No se pudo consultar el RUI (" + (evento.error || "sin conexión al servicio") + "). " +
            "El servicio del DNP necesita salida normal a internet.";
    }
}

// ------------------------------------------------------------
// PROCESAR (boton principal)
// ------------------------------------------------------------
document.getElementById("btn-procesar").addEventListener("click", async () => {
    if (!archivoCedula) return;

    const boton = document.getElementById("btn-procesar");
    boton.disabled = true;

    reiniciarPasos();
    reiniciarRui();

    const formData = new FormData();
    formData.append("cedula", archivoCedula);

    let jobId;
    try {
        const resp = await fetch("/api/jobs", { method: "POST", body: formData });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || "Error al crear el trabajo");
        jobId = data.job_id;
    } catch (err) {
        alert("No se pudo iniciar el procesamiento: " + err.message);
        actualizarBotonProcesar();
        return;
    }

    const fuente = new EventSource(`/api/jobs/${jobId}/stream`);

    fuente.onmessage = (msg) => {
        const evento = JSON.parse(msg.data);

        switch (evento.type) {
            case "stage":
                marcarEtapa(evento.stage, evento.status);
                break;
            case "result":
                renderResultado(evento.result);
                break;
            case "error":
                document.getElementById("resultado-cedula").innerHTML =
                    `<p class="resultado-vacio">Error: ${evento.message}</p>`;
                alert(`Error procesando la cédula: ${evento.message}`);
                break;
            case "rui":
                manejarEventoRui(evento);
                break;
            case "historial_actualizado":
                break;
            case "done":
                fuente.close();
                actualizarBotonProcesar();
                break;
        }
    };

    fuente.onerror = () => {
        fuente.close();
        actualizarBotonProcesar();
    };
});

// ------------------------------------------------------------
// HISTORIAL
// ------------------------------------------------------------
async function cargarHistorial() {
    const cuerpo = document.getElementById("tabla-historial-body");
    try {
        const resp = await fetch("/api/historial");
        const datos = await resp.json();

        if (!datos.length) {
            cuerpo.innerHTML = `<tr><td colspan="5" class="vacio">Aún no se ha procesado ningún graduado.</td></tr>`;
            return;
        }

        cuerpo.innerHTML = datos.map((r) => {
            let ruiTxt = "—";
            if (r.rui && r.rui.success) {
                const nombreRui = (r.rui.data && r.rui.data.nombre_completo) || "verificado";
                ruiTxt = `<span class="coincide-si">✓ ${nombreRui}</span>`;
            } else if (r.rui) {
                ruiTxt = `<span class="coincide-no">✗ no encontrado</span>`;
            }
            return `<tr>
                <td>${r.fecha}</td>
                <td>${r.nombre}</td>
                <td>${r.numero_documento}</td>
                <td>${r.edad !== null && r.edad !== undefined ? r.edad : "—"}</td>
                <td>${ruiTxt}</td>
            </tr>`;
        }).join("");
    } catch (e) {
        cuerpo.innerHTML = `<tr><td colspan="5" class="vacio">No se pudo cargar el historial.</td></tr>`;
    }
}
