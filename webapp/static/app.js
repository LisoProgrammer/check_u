// ============================================================
// Check_U - Panel de administrador (frontend)
// ============================================================

const estadoArchivos = { documento: null, cedula: null };

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
// DROPZONES
// ------------------------------------------------------------
function configurarDropzone(target) {
    const zona = document.querySelector(`.dropzone[data-target="${target}"]`);
    const input = document.getElementById(`input-${target}`);

    const asignarArchivo = (file) => {
        if (!file) return;
        estadoArchivos[target] = file;
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

configurarDropzone("documento");
configurarDropzone("cedula");

function actualizarBotonProcesar() {
    const boton = document.getElementById("btn-procesar");
    boton.disabled = !(estadoArchivos.documento && estadoArchivos.cedula);
}

// ------------------------------------------------------------
// PASOS / PROGRESO
// ------------------------------------------------------------
const ETAPAS = ["leyendo", "convirtiendo", "procesando", "inclinacion", "limpiando"];

function marcarEtapa(target, stage, status) {
    const li = document.querySelector(`#pasos-${target} li[data-stage="${stage}"]`);
    if (!li) return;
    li.classList.remove("en-progreso", "completado");
    li.classList.add(status === "done" ? "completado" : "en-progreso");

    if (status === "done") {
        const idx = ETAPAS.indexOf(stage);
        const pct = Math.round(((idx + 1) / ETAPAS.length) * 100);
        document.getElementById(`barra-${target}`).style.width = pct + "%";
    }
}

function reiniciarPasos(target) {
    document.querySelectorAll(`#pasos-${target} li`).forEach((li) => {
        li.classList.remove("en-progreso", "completado");
    });
    document.getElementById(`barra-${target}`).style.width = "0%";
    const caja = document.getElementById(`resultado-${target}`);
    caja.hidden = true;
    caja.innerHTML = "";
}

// ------------------------------------------------------------
// RENDER DE RESULTADOS POR DOCUMENTO
// ------------------------------------------------------------
function renderResultado(target, resultado) {
    const caja = document.getElementById(`resultado-${target}`);
    caja.hidden = false;

    const campos = resultado.fields || {};
    let html = "<dl>";
    for (const [clave, valor] of Object.entries(campos)) {
        html += `<dt>${etiquetaCampo(clave)}</dt><dd>${valor !== null && valor !== undefined ? valor : "—"}</dd>`;
    }
    html += "</dl>";

    if (target === "cedula" && resultado.mrz) {
        if (!resultado.mrz.encontrado) {
            html += `<div class="aviso">No se pudo localizar/leer el MRZ en la imagen.</div>`;
        } else if (!resultado.mrz.valido) {
            html += `<div class="aviso">MRZ leído, pero los dígitos de verificación no cuadran (posible error de OCR).</div>`;
        }
    }

    caja.innerHTML = html;
}

function etiquetaCampo(clave) {
    const mapa = {
        nombre_completo: "Nombre",
        numero_documento: "N° documento",
        fecha_nacimiento: "Fecha nacimiento",
        edad: "Edad",
        sexo: "Sexo",
        institucion_educativa: "Institución",
        puntaje_global: "Puntaje ICFES",
    };
    return mapa[clave] || clave;
}

// ------------------------------------------------------------
// COMPARACION
// ------------------------------------------------------------
function renderComparacion(filas) {
    const seccion = document.getElementById("seccion-comparacion");
    const cuerpo = document.getElementById("tabla-comparacion-body");
    cuerpo.innerHTML = "";

    if (!filas.length) {
        seccion.hidden = true;
        return;
    }

    filas.forEach((fila) => {
        const tr = document.createElement("tr");
        let coincideHtml;
        if (fila.coincide === true) coincideHtml = `<span class="coincide-si"><i class="fa-solid fa-check"></i> Sí</span>`;
        else if (fila.coincide === false) coincideHtml = `<span class="coincide-no"><i class="fa-solid fa-xmark"></i> No</span>`;
        else coincideHtml = `<span class="coincide-na">—</span>`;

        tr.innerHTML = `<td>${fila.campo}</td><td>${fila.documento}</td><td>${fila.cedula}</td><td>${coincideHtml}</td>`;
        cuerpo.appendChild(tr);
    });

    seccion.hidden = false;
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

function manejarEventoRui(evento) {
    const seccion = document.getElementById("seccion-rui");
    seccion.hidden = false;

    if (evento.status === "start") {
        document.getElementById("rui-cargando").hidden = false;
        return;
    }

    document.getElementById("rui-cargando").hidden = true;

    if (evento.status === "skipped") {
        document.getElementById("rui-error").hidden = false;
        document.getElementById("rui-error-msg").textContent = evento.message || "No se pudo determinar un número de documento para consultar.";
        return;
    }

    if (evento.success) {
        document.getElementById("rui-ok").hidden = false;
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
        document.getElementById("rui-error").hidden = false;
        document.getElementById("rui-error-msg").textContent =
            "No se pudo consultar el RUI (" + (evento.error || "sin conexión al servicio") + "). " +
            "Nota: el servicio del DNP solo es alcanzable desde una red con salida normal a internet.";
    }
}

// ------------------------------------------------------------
// PROCESAR (boton principal)
// ------------------------------------------------------------
document.getElementById("btn-procesar").addEventListener("click", async () => {
    const boton = document.getElementById("btn-procesar");
    boton.disabled = true;

    reiniciarPasos("documento");
    reiniciarPasos("cedula");
    reiniciarRui();
    document.getElementById("seccion-comparacion").hidden = true;

    const formData = new FormData();
    formData.append("documento", estadoArchivos.documento);
    formData.append("cedula", estadoArchivos.cedula);
    formData.append("documento_tipo", document.getElementById("documento_tipo").value);

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
                marcarEtapa(evento.target, evento.stage, evento.status);
                break;
            case "result":
                renderResultado(evento.target, evento.result);
                break;
            case "error":
                alert(`Error procesando ${evento.target}: ${evento.message}`);
                break;
            case "comparison":
                renderComparacion(evento.rows);
                break;
            case "rui":
                manejarEventoRui(evento);
                break;
            case "historial_actualizado":
                // se refresca solo si el usuario abre la pestaña
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
            if (r.rui && r.rui.success) ruiTxt = `<span class="coincide-si">✓ ${r.rui.data ? "" : ""}${(r.rui.data && r.rui.data.nombre_completo) || "verificado"}</span>`;
            else if (r.rui) ruiTxt = `<span class="coincide-no">✗ no encontrado</span>`;
            return `<tr>
                <td>${r.fecha}</td>
                <td>${r.nombre}</td>
                <td>${r.numero_documento}</td>
                <td>${r.tipo_documento}</td>
                <td>${ruiTxt}</td>
            </tr>`;
        }).join("");
    } catch (e) {
        cuerpo.innerHTML = `<tr><td colspan="5" class="vacio">No se pudo cargar el historial.</td></tr>`;
    }
}
