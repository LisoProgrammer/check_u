/* ==========================================================================
   Check_U - Panel de validacion documental
   --------------------------------------------------------------------------
   Flujo: se suelta un documento -> se abre su pestaña -> se procesa solo
   (sin boton) -> se dibujan los recuadros de donde salio cada dato -> se
   valida contra el RUI -> si hay mas de un documento, se comparan entre
   si y se dibujan las lineas que unen los datos equivalentes.

   Todo el estado vive en el objeto `estado`; el servidor guarda el caso
   en disco, asi que recargar la pagina o volver mañana no pierde nada.
   ========================================================================== */

"use strict";

const estado = {
    casoId: null,
    titulo: null,
    documentos: new Map(),   // id -> datos del documento
    orden: [],               // ids en el orden en que se subieron
    comparaciones: [],
    pestaña: null,           // id de documento, o "comparacion"
    entornoOk: true,
};

const CAMPOS = [
    { clave: "numero_documento", etiqueta: "N° documento" },
    { clave: "nombre_completo", etiqueta: "Nombre completo" },
    { clave: "fecha_nacimiento", etiqueta: "Fecha de nacimiento" },
    { clave: "sexo", etiqueta: "Sexo" },
];

const ETAPAS = [
    { clave: "cargando", texto: "Leyendo el archivo" },
    { clave: "preparando", texto: "Preparando la imagen" },
    { clave: "ocr", texto: "Reconociendo el texto (OCR)" },
    { clave: "detectando_formato", texto: "Detectando el formato" },
    { clave: "extrayendo", texto: "Extrayendo los datos" },
    { clave: "rui", texto: "Consultando el RUI" },
];

const NOMBRES_FUENTE = {
    pdf417: "código de barras PDF417",
    produccion: "línea de producción del reverso",
    etiqueta: "texto impreso",
    estructura: "texto impreso",
    mrz: "MRZ",
};

const ESTADOS = {
    valida: { titulo: "Válida", icono: "M5 13l4 4L19 7" },
    inconsistente: { titulo: "Inconsistente", icono: "M6 6l12 12M18 6L6 18" },
    por_revisar: { titulo: "Por revisar", icono: "M12 8v5M12 16.5v.01" },
    vacia: { titulo: "Sin documentos", icono: "M12 8v5M12 16.5v.01" },
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function crear(etiqueta, clase, texto) {
    const nodo = document.createElement(etiqueta);
    if (clase) nodo.className = clase;
    if (texto !== undefined) nodo.textContent = texto;
    return nodo;
}

function icono(d, tamaño) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    if (tamaño) {
        svg.style.width = tamaño + "px";
        svg.style.height = tamaño + "px";
    }
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", d);
    svg.appendChild(path);
    return svg;
}

/* ==========================================================================
   TEMA CLARO / OSCURO
   --------------------------------------------------------------------------
   Por defecto se sigue el tema del sistema: el atributo data-tema queda en
   "sistema" y el CSS resuelve con prefers-color-scheme. El boton impone
   "claro" u "oscuro" y esa eleccion se recuerda.
   ========================================================================== */

function temaGuardado() {
    try {
        return localStorage.getItem("checku-tema") || "sistema";
    } catch (e) {
        return "sistema";
    }
}

function aplicarTema(tema) {
    document.documentElement.setAttribute("data-tema", tema);
    try {
        if (tema === "sistema") localStorage.removeItem("checku-tema");
        else localStorage.setItem("checku-tema", tema);
    } catch (e) {
        /* modo privado o almacenamiento bloqueado: el tema igual funciona,
           solo no se recuerda para la proxima visita. */
    }
}

function oscuroActivo() {
    const tema = document.documentElement.getAttribute("data-tema");
    if (tema === "oscuro") return true;
    if (tema === "claro") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/* ==========================================================================
   LLAMADAS AL SERVIDOR
   ========================================================================== */

async function api(ruta, opciones) {
    const respuesta = await fetch(ruta, opciones);
    if (!respuesta.ok) {
        let mensaje = `Error ${respuesta.status}`;
        try {
            const datos = await respuesta.json();
            if (datos.error) mensaje = datos.error;
        } catch (e) { /* respuesta sin JSON */ }
        throw new Error(mensaje);
    }
    return respuesta.json();
}

async function comprobarEntorno() {
    try {
        const salud = await api("/api/salud");
        estado.entornoOk = salud.ok;

        const aviso = $("#aviso-entorno");
        const lista = $("#aviso-entorno-lista");
        lista.innerHTML = "";

        if (salud.ok) {
            aviso.hidden = true;
            return;
        }

        salud.problemas.forEach((problema) => {
            const li = crear("li");
            li.innerHTML =
                `<strong>${problema.titulo || problema.componente || "Problema"}</strong>: ` +
                `${problema.detalle || ""} ${problema.solucion || ""}`;
            lista.appendChild(li);
        });
        aviso.hidden = false;
    } catch (e) {
        /* Si ni siquiera responde /api/salud, el servidor no esta arriba;
           el propio fetch de subida lo va a reportar con mas contexto. */
    }
}

/* ==========================================================================
   CASOS
   ========================================================================== */

function nuevoCaso() {
    // Solo limpia la pantalla. El caso se crea en el servidor recien
    // cuando entra el primer documento: si no, con solo abrir el panel se
    // llenaba el historial de casos vacios "(sin identificar)".
    estado.casoId = null;
    estado.titulo = null;
    estado.documentos.clear();
    estado.orden = [];
    estado.comparaciones = [];
    estado.pestaña = null;
    olvidarUltimoCaso();
    render();
}

async function asegurarCaso() {
    if (estado.casoId) return estado.casoId;

    const caso = await api("/api/casos", { method: "POST" });
    estado.casoId = caso.id;
    guardarUltimoCaso(caso.id);
    return caso.id;
}

function olvidarUltimoCaso() {
    try {
        localStorage.removeItem("checku-caso");
    } catch (e) { /* sin almacenamiento */ }
}

function guardarUltimoCaso(id) {
    try {
        localStorage.setItem("checku-caso", id);
    } catch (e) { /* sin almacenamiento: se pierde solo el "retomar solo" */ }
}

function ultimoCaso() {
    try {
        return localStorage.getItem("checku-caso");
    } catch (e) {
        return null;
    }
}

async function abrirCaso(id) {
    const caso = await api(`/api/casos/${id}`);

    estado.casoId = caso.id;
    estado.titulo = caso.titulo;
    estado.documentos.clear();
    estado.orden = [];
    estado.comparaciones = caso.comparaciones || [];

    (caso.documentos || []).forEach((documento) => {
        estado.documentos.set(documento.id, documento);
        estado.orden.push(documento.id);
    });

    estado.pestaña = estado.orden[0] || null;
    guardarUltimoCaso(caso.id);
    cerrarHistorial();
    render();
}

async function borrarDocumento(documentoId) {
    const respuesta = await api(
        `/api/casos/${estado.casoId}/documentos/${documentoId}`,
        { method: "DELETE" }
    );

    estado.documentos.delete(documentoId);
    estado.orden = estado.orden.filter((id) => id !== documentoId);
    estado.comparaciones = respuesta.comparaciones || [];

    if (estado.pestaña === documentoId) {
        estado.pestaña = estado.orden[0] || null;
    }
    render();
}

/* ==========================================================================
   SUBIDA Y PROCESAMIENTO
   ========================================================================== */

async function subirArchivos(archivos) {
    if (!archivos || !archivos.length) return;

    await asegurarCaso();

    for (const archivo of archivos) {
        await subirUno(archivo);
    }
}

async function subirUno(archivo) {
    const datos = new FormData();
    datos.append("archivo", archivo);

    let respuesta;
    try {
        respuesta = await api(`/api/casos/${estado.casoId}/documentos`, {
            method: "POST",
            body: datos,
        });
    } catch (e) {
        alert(`No se pudo subir "${archivo.name}": ${e.message}`);
        return;
    }

    // Marcador provisional para que la pestaña aparezca de inmediato,
    // antes de que el servidor devuelva nada: el usuario ve que su
    // archivo ya entro al sistema.
    const documento = {
        id: respuesta.documento_id,
        nombre_archivo: respuesta.nombre_archivo,
        procesando: true,
        etapa: "cargando",
        paginas: [],
        campos: {},
        avisos: [],
        errores: [],
    };

    estado.documentos.set(documento.id, documento);
    estado.orden.push(documento.id);
    estado.pestaña = documento.id;
    render();

    await seguirProceso(respuesta.trabajo_id, documento.id);
}

function seguirProceso(trabajoId, documentoId) {
    return new Promise((resolver) => {
        const flujo = new EventSource(`/api/trabajos/${trabajoId}/stream`);

        flujo.onmessage = (mensaje) => {
            let evento;
            try {
                evento = JSON.parse(mensaje.data);
            } catch (e) {
                return;
            }

            const documento = estado.documentos.get(documentoId);
            if (!documento) return;

            switch (evento.tipo) {
                case "etapa":
                    documento.etapa = evento.etapa;
                    actualizarEtapas(documentoId);
                    break;

                case "progreso":
                    documento.etapa = evento.etapa;
                    if (evento.etapa === "formato") {
                        documento.formato = evento.formato;
                        documento.formato_nombre = evento.formato_nombre;
                        // Aviso transitorio de cambio de formato: se muestra
                        // mientras dura el proceso y se va al terminar.
                        if (evento.cambio) mostrarAvisoFormato(evento.mensaje);
                    }
                    actualizarEtapas(documentoId);
                    break;

                case "paginas":
                    documento.paginas = evento.paginas;
                    if (estado.pestaña === documentoId) render();
                    break;

                case "documento":
                    estado.documentos.set(documentoId, {
                        ...evento.datos,
                        procesando: false,
                    });
                    break;

                case "comparaciones":
                    estado.comparaciones = evento.comparaciones || [];
                    if (evento.titulo) estado.titulo = evento.titulo;
                    estado.estadoCaso = evento.estado;
                    break;

                case "error":
                    documento.procesando = false;
                    documento.errores = [evento.mensaje];
                    break;

                case "fin":
                    documento.procesando = false;
                    ocultarAvisoFormato();
                    flujo.close();
                    render();
                    resolver();
                    break;
            }
        };

        flujo.onerror = () => {
            const documento = estado.documentos.get(documentoId);
            if (documento && documento.procesando) {
                documento.procesando = false;
                documento.errores = [
                    "Se perdió la conexión con el servidor durante el proceso.",
                ];
            }
            ocultarAvisoFormato();
            flujo.close();
            render();
            resolver();
        };
    });
}

let temporizadorAviso = null;

function mostrarAvisoFormato(mensaje) {
    const aviso = $("#aviso-formato");
    $("#aviso-formato-texto").textContent = mensaje;
    aviso.hidden = false;
    clearTimeout(temporizadorAviso);
}

function ocultarAvisoFormato() {
    // Pequeña demora para que el aviso alcance a leerse aunque el
    // documento se procese muy rapido.
    clearTimeout(temporizadorAviso);
    temporizadorAviso = setTimeout(() => {
        $("#aviso-formato").hidden = true;
    }, 900);
}

/* ==========================================================================
   RENDER
   ========================================================================== */

function render() {
    renderCarrusel();
    renderPaneles();
    renderEstadoCaso();
    requestAnimationFrame(dibujarLineas);
}

function renderEstadoCaso() {
    const barra = $("#barra-estado");
    if (!estado.casoId || !estado.orden.length) {
        barra.hidden = true;
        return;
    }

    const estados = estado.orden
        .map((id) => estado.documentos.get(id))
        .filter((d) => d && d.validacion)
        .map((d) => d.validacion.estado);

    let global = "valida";
    if (!estados.length) global = "por_revisar";
    else if (estados.includes("inconsistente")) global = "inconsistente";
    else if (estados.includes("por_revisar")) global = "por_revisar";

    // Una discrepancia entre documentos tambien vuelve inconsistente el caso.
    estado.comparaciones.forEach((par) => {
        par.campos.forEach((campo) => {
            if (campo.coincide === false) global = "inconsistente";
        });
    });

    barra.hidden = false;
    $("#estado-punto").className = "punto " + global;
    $("#estado-texto").textContent =
        (estado.titulo ? estado.titulo + " · " : "") + ESTADOS[global].titulo;
}

function renderCarrusel() {
    const pista = $("#carrusel-pista");
    pista.innerHTML = "";

    estado.orden.forEach((id) => {
        const documento = estado.documentos.get(id);
        if (!documento) return;

        const pestaña = crear("button", "pestaña");
        if (estado.pestaña === id) pestaña.classList.add("activa");

        const punto = crear("span", "pestaña-estado");
        if (documento.procesando) punto.classList.add("procesando");
        else if (documento.validacion) punto.classList.add(documento.validacion.estado);
        pestaña.appendChild(punto);

        pestaña.appendChild(crear("span", null, documento.nombre_archivo));

        const cerrar = crear("span", "pestaña-cerrar");
        cerrar.appendChild(icono("M6 6l12 12M18 6L6 18", 12));
        cerrar.title = "Quitar este documento del caso";
        cerrar.addEventListener("click", (evento) => {
            evento.stopPropagation();
            borrarDocumento(id);
        });
        pestaña.appendChild(cerrar);

        pestaña.addEventListener("click", () => {
            estado.pestaña = id;
            render();
        });

        pista.appendChild(pestaña);
    });

    // La pestaña de comparacion solo tiene sentido con dos o mas documentos.
    if (estado.comparaciones.length) {
        const pestaña = crear("button", "pestaña");
        if (estado.pestaña === "comparacion") pestaña.classList.add("activa");

        const hayDiferencia = estado.comparaciones.some((par) =>
            par.campos.some((campo) => campo.coincide === false)
        );

        const punto = crear("span", "pestaña-estado");
        punto.classList.add(hayDiferencia ? "inconsistente" : "valida");
        pestaña.appendChild(punto);
        pestaña.appendChild(crear("span", null, "Comparación"));

        pestaña.addEventListener("click", () => {
            estado.pestaña = "comparacion";
            render();
        });

        pista.appendChild(pestaña);
    }
}

function renderPaneles() {
    const contenedor = $("#paneles");
    contenedor.innerHTML = "";

    const vacio = $("#panel-vacio");
    vacio.hidden = estado.orden.length > 0;

    if (!estado.orden.length) return;

    if (estado.pestaña === "comparacion") {
        contenedor.appendChild(panelComparacion());
        return;
    }

    const documento = estado.documentos.get(estado.pestaña);
    if (documento) contenedor.appendChild(panelDocumento(documento));
}

/* ------------------------------------------------ Panel de un documento -- */

function panelDocumento(documento) {
    const panel = crear("section", "panel-doc activo");
    panel.dataset.documento = documento.id;

    const cuerpo = crear("div", "doc-cuerpo");

    const capa = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    capa.setAttribute("class", "capa-lineas");
    cuerpo.appendChild(capa);

    cuerpo.appendChild(visorDocumento(documento));
    cuerpo.appendChild(panelDatos(documento));

    panel.appendChild(cuerpo);
    return panel;
}

function visorDocumento(documento) {
    const visor = crear("div", "visor");
    visor.dataset.visor = documento.id;

    if (!documento.paginas || !documento.paginas.length) {
        const vacio = crear("div", "visor-vacio");
        vacio.appendChild(icono("M12 8v5M12 16.5v.01", 26));
        vacio.appendChild(
            crear(
                "span",
                null,
                documento.procesando
                    ? "Procesando el documento…"
                    : "No se pudo generar la vista del documento."
            )
        );
        visor.appendChild(vacio);
        return visor;
    }

    const contenedor = crear("div", "visor-paginas");
    // Al desplazar el documento hay que recalcular las lineas, que se
    // dibujan en coordenadas de pantalla.
    contenedor.addEventListener("scroll", dibujarLineas, { passive: true });

    documento.paginas.forEach((pagina) => {
        const caja = crear("div", "visor-pagina");
        caja.dataset.pagina = pagina.indice;

        const img = document.createElement("img");
        img.src = pagina.url;
        img.alt = `Página ${pagina.indice + 1} de ${documento.nombre_archivo}`;
        img.loading = "lazy";
        img.addEventListener("load", dibujarLineas);
        caja.appendChild(img);

        // Recuadros de los campos que salieron de esta pagina.
        //
        // Varios campos pueden compartir exactamente la misma region: en la
        // cedula digital, todo lo que sale del MRZ viene de esa unica
        // franja. Dibujar cuatro recuadros identicos encimados solo hace
        // que sus etiquetas se pisen, asi que se agrupan en uno con la
        // etiqueta combinada.
        agruparPorCaja(documento.campos, pagina.indice).forEach((grupo) => {
            const recuadro = crear("div", "recuadro");
            recuadro.dataset.campo = grupo.claves[0];
            recuadro.dataset.campos = grupo.claves.join(" ");
            recuadro.dataset.documento = documento.id;
            recuadro.dataset.etiqueta = grupo.etiquetas.join(" · ");
            recuadro.style.left = grupo.caja.x * 100 + "%";
            recuadro.style.top = grupo.caja.y * 100 + "%";
            recuadro.style.width = grupo.caja.ancho * 100 + "%";
            recuadro.style.height = grupo.caja.alto * 100 + "%";

            recuadro.addEventListener("mouseenter", () =>
                grupo.claves.forEach((clave) => resaltar(clave, true))
            );
            recuadro.addEventListener("mouseleave", () =>
                grupo.claves.forEach((clave) => resaltar(clave, false))
            );

            caja.appendChild(recuadro);
        });

        contenedor.appendChild(caja);
    });

    visor.appendChild(contenedor);
    return visor;
}

function agruparPorCaja(campos, indicePagina) {
    const grupos = new Map();

    CAMPOS.forEach(({ clave, etiqueta }) => {
        const campo = (campos || {})[clave];
        if (!campo || !campo.caja || campo.pagina !== indicePagina) return;

        // Se redondea para que dos cajas practicamente iguales cuenten como
        // la misma (el OCR puede devolver diferencias de un pixel).
        const c = campo.caja;
        const llave = [c.x, c.y, c.ancho, c.alto]
            .map((n) => Math.round(n * 400))
            .join(":");

        if (!grupos.has(llave)) {
            grupos.set(llave, { caja: c, claves: [], etiquetas: [] });
        }
        grupos.get(llave).claves.push(clave);
        grupos.get(llave).etiquetas.push(etiqueta);
    });

    return Array.from(grupos.values());
}

function panelDatos(documento) {
    const datos = crear("div", "datos");
    datos.dataset.datos = documento.id;

    // --- Tarjeta de datos extraidos ---
    const tarjeta = crear("div", "tarjeta");
    tarjeta.appendChild(crear("h3", null, "Datos extraídos"));

    if (documento.formato_nombre) {
        const chip = crear("div", "formato-chip");
        chip.appendChild(
            icono(
                documento.formato === "digital"
                    ? "M4 7h16v10H4zM8 17v2M16 17v2"
                    : "M4 5h16v14H4zM8 9h4M8 13h8",
                14
            )
        );
        chip.appendChild(crear("span", null, documento.formato_nombre));
        tarjeta.appendChild(chip);
    }

    CAMPOS.forEach(({ clave, etiqueta }) => {
        const campo = (documento.campos || {})[clave];

        const fila = crear("div", "campo");
        fila.dataset.campo = clave;
        fila.appendChild(crear("span", "campo-etiqueta", etiqueta));

        const valor = crear(
            "span",
            "campo-valor" + (campo && campo.valor ? "" : " ausente"),
            campo && campo.valor ? campo.valor : "sin determinar"
        );
        fila.appendChild(valor);

        if (campo && campo.fuente) {
            fila.appendChild(
                crear(
                    "span",
                    "campo-fuente",
                    "leído del " + (NOMBRES_FUENTE[campo.fuente] || campo.fuente)
                )
            );
        }

        fila.addEventListener("mouseenter", () => resaltar(clave, true));
        fila.addEventListener("mouseleave", () => resaltar(clave, false));

        tarjeta.appendChild(fila);
    });

    if (documento.edad !== null && documento.edad !== undefined) {
        const fila = crear("div", "campo");
        fila.appendChild(crear("span", "campo-etiqueta", "Edad"));
        fila.appendChild(crear("span", "campo-valor", `${documento.edad} años`));
        tarjeta.appendChild(fila);
    }

    datos.appendChild(tarjeta);

    // --- Tarjeta de validacion / progreso ---
    datos.appendChild(
        documento.procesando ? tarjetaEtapas(documento) : tarjetaValidacion(documento)
    );

    return datos;
}

function tarjetaEtapas(documento) {
    const tarjeta = crear("div", "tarjeta");
    tarjeta.dataset.etapas = documento.id;
    tarjeta.appendChild(crear("h3", null, "Procesando"));
    tarjeta.appendChild(listaEtapas(documento));
    return tarjeta;
}

function listaEtapas(documento) {
    const lista = crear("div", "etapas");
    const actual = ETAPAS.findIndex((e) => e.clave === documento.etapa);

    ETAPAS.forEach((etapa, indice) => {
        const fila = crear("div", "etapa");
        if (actual >= 0 && indice < actual) fila.classList.add("lista");
        if (indice === actual) fila.classList.add("activa");
        fila.appendChild(crear("span", "etapa-punto"));
        fila.appendChild(crear("span", null, etapa.texto));
        lista.appendChild(fila);
    });

    return lista;
}

function actualizarEtapas(documentoId) {
    const documento = estado.documentos.get(documentoId);
    const tarjeta = document.querySelector(`[data-etapas="${documentoId}"]`);
    if (!documento || !tarjeta) return;

    const vieja = tarjeta.querySelector(".etapas");
    if (vieja) vieja.replaceWith(listaEtapas(documento));
}

function tarjetaValidacion(documento) {
    const tarjeta = crear("div", "tarjeta");
    tarjeta.appendChild(crear("h3", null, "Validación contra el RUI"));

    const validacion = documento.validacion;

    if (!validacion) {
        tarjeta.appendChild(
            crear("p", "campo-fuente", "Sin resultado de validación todavía.")
        );
        return tarjeta;
    }

    const info = ESTADOS[validacion.estado] || ESTADOS.por_revisar;

    const veredicto = crear("div", "veredicto " + validacion.estado);
    const marca = crear("div", "veredicto-icono");
    marca.appendChild(icono(info.icono, 15));
    veredicto.appendChild(marca);

    const texto = crear("div");
    texto.appendChild(crear("div", "veredicto-titulo", info.titulo));
    texto.appendChild(crear("div", "veredicto-detalle", validacion.detalle || ""));
    veredicto.appendChild(texto);

    tarjeta.appendChild(veredicto);

    if (validacion.similitud !== null && validacion.similitud !== undefined) {
        const medidor = crear("div", "medidor");
        const relleno = crear("div", "medidor-relleno");
        relleno.style.width = Math.max(0, Math.min(100, validacion.similitud)) + "%";
        if (validacion.estado === "inconsistente") {
            relleno.style.background = "var(--error)";
        }
        medidor.appendChild(relleno);
        tarjeta.appendChild(medidor);

        const pie = crear("div", "medidor-pie");
        pie.appendChild(
            crear("span", null, `Similitud: ${validacion.similitud.toFixed(0)} %`)
        );
        pie.appendChild(crear("span", null, `Mínimo: ${validacion.umbral} %`));
        tarjeta.appendChild(pie);
    }

    if (validacion.nombre_rui) {
        const fila = crear("div", "campo");
        fila.appendChild(crear("span", "campo-etiqueta", "Nombre según el RUI"));
        fila.appendChild(crear("span", "campo-valor", validacion.nombre_rui));
        tarjeta.appendChild(fila);
    }

    const notas = [].concat(documento.avisos || [], documento.errores || []);
    if (notas.length) {
        const lista = crear("ul", "avisos");
        notas.forEach((nota) => lista.appendChild(crear("li", null, nota)));
        tarjeta.appendChild(lista);
    }

    return tarjeta;
}

/* ------------------------------------------------- Panel de comparacion -- */

function panelComparacion() {
    const panel = crear("section", "panel-doc activo");
    const cuerpo = crear("div", "comparacion-cuerpo");

    const capa = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    capa.setAttribute("class", "capa-lineas");
    cuerpo.appendChild(capa);

    estado.comparaciones.forEach((par) => {
        const docA = estado.documentos.get(par.documento_a);
        const docB = estado.documentos.get(par.documento_b);
        if (!docA || !docB) return;

        const bloque = crear("div", "comparacion-par");
        bloque.dataset.par = `${par.documento_a}|${par.documento_b}`;

        const titulo = crear("h2", "comparacion-titulo");
        titulo.appendChild(icono("M8 7h8M8 12h8M8 17h5", 15));
        titulo.appendChild(
            crear("span", null, `${par.nombre_a}  ·  ${par.nombre_b}`)
        );
        bloque.appendChild(titulo);

        const columnas = crear("div", "comparacion-columnas");
        columnas.appendChild(visorComparacion(docA, par, "a"));
        columnas.appendChild(visorComparacion(docB, par, "b"));
        bloque.appendChild(columnas);

        const resumen = crear("div", "comparacion-resumen");
        par.campos.forEach((campo) => {
            const fila = crear("div", "fila-comparacion");
            fila.dataset.campo = campo.campo;
            fila.appendChild(crear("span", "etiqueta", campo.etiqueta));
            fila.appendChild(crear("span", "valor", campo.valor_a || "—"));

            let clase = "na";
            let texto = "sin comparar";
            if (campo.coincide === true) {
                clase = "si";
                texto =
                    campo.campo === "numero_documento"
                        ? "igual"
                        : `coincide ${campo.similitud.toFixed(0)} %`;
            } else if (campo.coincide === false) {
                clase = "no";
                texto =
                    campo.campo === "numero_documento"
                        ? "distinto"
                        : `difiere (${campo.similitud.toFixed(0)} %)`;
            }
            fila.appendChild(crear("span", "marca " + clase, texto));
            fila.appendChild(crear("span", "valor", campo.valor_b || "—"));

            fila.addEventListener("mouseenter", () => resaltar(campo.campo, true));
            fila.addEventListener("mouseleave", () => resaltar(campo.campo, false));

            resumen.appendChild(fila);
        });

        bloque.appendChild(resumen);
        cuerpo.appendChild(bloque);
    });

    panel.appendChild(cuerpo);
    return panel;
}

function visorComparacion(documento, par, lado) {
    const visor = crear("div", "visor");
    visor.dataset.visorComparacion = `${par.documento_a}|${par.documento_b}|${lado}`;

    const contenedor = crear("div", "visor-paginas");
    contenedor.addEventListener("scroll", dibujarLineas, { passive: true });

    (documento.paginas || []).forEach((pagina) => {
        const caja = crear("div", "visor-pagina");

        const img = document.createElement("img");
        img.src = pagina.url;
        img.alt = documento.nombre_archivo;
        img.loading = "lazy";
        img.addEventListener("load", dibujarLineas);
        caja.appendChild(img);

        par.campos.forEach((campo) => {
            const cajaCampo = lado === "a" ? campo.caja_a : campo.caja_b;
            const paginaCampo = lado === "a" ? campo.pagina_a : campo.pagina_b;
            if (!cajaCampo || paginaCampo !== pagina.indice) return;

            const recuadro = crear("div", "recuadro");
            recuadro.dataset.campo = campo.campo;
            recuadro.dataset.lado = lado;
            recuadro.dataset.etiqueta = campo.etiqueta;
            if (campo.coincide === true) recuadro.classList.add("coincide");
            if (campo.coincide === false) recuadro.classList.add("difiere");

            recuadro.style.left = cajaCampo.x * 100 + "%";
            recuadro.style.top = cajaCampo.y * 100 + "%";
            recuadro.style.width = cajaCampo.ancho * 100 + "%";
            recuadro.style.height = cajaCampo.alto * 100 + "%";

            recuadro.addEventListener("mouseenter", () => resaltar(campo.campo, true));
            recuadro.addEventListener("mouseleave", () => resaltar(campo.campo, false));

            caja.appendChild(recuadro);
        });

        contenedor.appendChild(caja);
    });

    visor.appendChild(contenedor);
    return visor;
}

/* ==========================================================================
   LINEAS ENTRE RECUADROS Y DATOS
   --------------------------------------------------------------------------
   Se dibujan en un SVG que cubre el panel entero. Las posiciones se sacan
   con getBoundingClientRect y se pasan a coordenadas del SVG, asi que hay
   que redibujar cuando cambia el tamaño de la ventana o se desplaza el
   visor. Un recuadro que quedo fuera de la parte visible del visor no se
   dibuja: la linea apuntaria a un punto que el usuario no ve.
   ========================================================================== */

function visible(rectanguloHijo, rectanguloPadre) {
    return (
        rectanguloHijo.bottom > rectanguloPadre.top + 2 &&
        rectanguloHijo.top < rectanguloPadre.bottom - 2
    );
}

function curva(x1, y1, x2, y2) {
    const control = Math.max(24, Math.abs(x2 - x1) * 0.4);
    return `M ${x1} ${y1} C ${x1 + control} ${y1}, ${x2 - control} ${y2}, ${x2} ${y2}`;
}

function dibujarLineas() {
    $$(".capa-lineas").forEach((capa) => {
        capa.innerHTML = "";

        const base = capa.parentElement.getBoundingClientRect();
        capa.setAttribute("viewBox", `0 0 ${base.width} ${base.height}`);
        capa.setAttribute("width", base.width);
        capa.setAttribute("height", base.height);

        if (base.width < 700) return;   // en pantallas angostas no hay espacio

        if (estado.pestaña === "comparacion") dibujarLineasComparacion(capa, base);
        else dibujarLineasDocumento(capa, base);
    });
}

function dibujarLineasDocumento(capa, base) {
    const panel = capa.parentElement;
    const visor = panel.querySelector(".visor-paginas");
    if (!visor) return;

    const marco = visor.getBoundingClientRect();

    panel.querySelectorAll(".recuadro").forEach((recuadro) => {
        const r = recuadro.getBoundingClientRect();
        if (!visible(r, marco)) return;

        const claves = (recuadro.dataset.campos || recuadro.dataset.campo || "").split(" ");

        // Un recuadro compartido por varios campos tira una linea a cada
        // uno: asi se ve que los cuatro datos salieron de la misma franja.
        claves.filter(Boolean).forEach((clave) => {
            const fila = panel.querySelector(`.campo[data-campo="${clave}"]`);
            if (!fila) return;

            const f = fila.getBoundingClientRect();

            const x1 = r.right - base.left;
            const y1 = r.top + r.height / 2 - base.top;
            const x2 = f.left - base.left;
            const y2 = f.top + f.height / 2 - base.top;

            const trazo = document.createElementNS("http://www.w3.org/2000/svg", "path");
            trazo.setAttribute("d", curva(x1, y1, x2, y2));
            trazo.dataset.campo = clave;
            capa.appendChild(trazo);
        });
    });
}

function dibujarLineasComparacion(capa, base) {
    capa.parentElement.querySelectorAll(".comparacion-par").forEach((bloque) => {
        const visores = bloque.querySelectorAll(".visor-paginas");
        if (visores.length < 2) return;

        const marcoA = visores[0].getBoundingClientRect();
        const marcoB = visores[1].getBoundingClientRect();

        bloque.querySelectorAll('.recuadro[data-lado="a"]').forEach((recuadroA) => {
            const clave = recuadroA.dataset.campo;
            const recuadroB = bloque.querySelector(
                `.recuadro[data-lado="b"][data-campo="${clave}"]`
            );
            if (!recuadroB) return;

            const a = recuadroA.getBoundingClientRect();
            const b = recuadroB.getBoundingClientRect();
            if (!visible(a, marcoA) || !visible(b, marcoB)) return;

            const x1 = a.right - base.left;
            const y1 = a.top + a.height / 2 - base.top;
            const x2 = b.left - base.left;
            const y2 = b.top + b.height / 2 - base.top;

            const trazo = document.createElementNS("http://www.w3.org/2000/svg", "path");
            trazo.setAttribute("d", curva(x1, y1, x2, y2));
            trazo.dataset.campo = clave;
            if (recuadroA.classList.contains("coincide")) trazo.classList.add("coincide");
            if (recuadroA.classList.contains("difiere")) trazo.classList.add("difiere");
            capa.appendChild(trazo);

            // Porcentaje de similitud sobre la linea.
            const fila = bloque.querySelector(`.fila-comparacion[data-campo="${clave}"]`);
            const marca = fila && fila.querySelector(".marca");
            if (marca) {
                const texto = document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "text"
                );
                texto.setAttribute("x", (x1 + x2) / 2);
                texto.setAttribute("y", (y1 + y2) / 2 - 6);
                texto.setAttribute("text-anchor", "middle");
                texto.textContent = marca.textContent;
                capa.appendChild(texto);
            }
        });
    });
}

function resaltar(clave, encendido) {
    $$(
        `.recuadro[data-campo="${clave}"], .recuadro[data-campos~="${clave}"]`
    ).forEach((nodo) => nodo.classList.toggle("resaltado", encendido));
    $$(`.campo[data-campo="${clave}"], .fila-comparacion[data-campo="${clave}"]`).forEach(
        (nodo) => nodo.classList.toggle("resaltado", encendido)
    );
    $$(`.capa-lineas path[data-campo="${clave}"]`).forEach((nodo) =>
        nodo.classList.toggle("resaltada", encendido)
    );
}

/* ==========================================================================
   HISTORIAL
   ========================================================================== */

async function abrirHistorial() {
    const cajon = $("#cajon-historial");
    const lista = $("#lista-casos");
    lista.innerHTML = "";
    cajon.hidden = false;

    let casos = [];
    try {
        casos = await api("/api/casos");
    } catch (e) {
        lista.appendChild(crear("p", "cajon-nota", "No se pudo cargar el historial."));
        return;
    }

    if (!casos.length) {
        lista.appendChild(
            crear("p", "cajon-nota", "Todavía no hay casos guardados.")
        );
        return;
    }

    casos.forEach((caso) => {
        const fila = crear("div", "caso");
        if (caso.id === estado.casoId) fila.classList.add("actual");

        const punto = crear("span", "punto " + (caso.estado || "por_revisar"));
        fila.appendChild(punto);

        const info = crear("div", "caso-info");
        info.appendChild(crear("div", "caso-titulo", caso.titulo));
        info.appendChild(
            crear(
                "div",
                "caso-meta",
                `${caso.documentos} documento${caso.documentos === 1 ? "" : "s"} · ` +
                    `${(caso.actualizado || "").replace("T", " ")}`
            )
        );
        fila.appendChild(info);

        const borrar = crear("button", "boton boton-icono boton-peligro");
        borrar.appendChild(icono("M4 7h16M9 7V5h6v2M7 7l1 13h8l1-13", 15));
        borrar.title = "Borrar este caso";
        borrar.addEventListener("click", async (evento) => {
            evento.stopPropagation();
            if (!confirm(`¿Borrar el caso de ${caso.titulo}?`)) return;
            await api(`/api/casos/${caso.id}`, { method: "DELETE" });
            if (caso.id === estado.casoId) nuevoCaso();
            abrirHistorial();
        });
        fila.appendChild(borrar);

        fila.addEventListener("click", () => abrirCaso(caso.id));
        lista.appendChild(fila);
    });
}

function cerrarHistorial() {
    $("#cajon-historial").hidden = true;
}

/* ==========================================================================
   ARRANQUE
   ========================================================================== */

function conectarEventos() {
    $("#btn-tema").addEventListener("click", () => {
        aplicarTema(oscuroActivo() ? "claro" : "oscuro");
    });

    $("#btn-nuevo").addEventListener("click", nuevoCaso);
    $("#btn-historial").addEventListener("click", abrirHistorial);
    $("#btn-cerrar-historial").addEventListener("click", cerrarHistorial);
    $("#cajon-fondo").addEventListener("click", cerrarHistorial);

    const input = $("#input-archivo");
    $("#btn-agregar").addEventListener("click", () => input.click());
    $("#btn-vacio-subir").addEventListener("click", () => input.click());

    input.addEventListener("change", () => {
        subirArchivos(Array.from(input.files));
        input.value = "";
    });

    // Arrastrar y soltar en cualquier parte de la ventana.
    let arrastres = 0;
    const capa = $("#soltar-aqui");

    window.addEventListener("dragenter", (evento) => {
        evento.preventDefault();
        arrastres += 1;
        capa.hidden = false;
    });

    window.addEventListener("dragover", (evento) => evento.preventDefault());

    window.addEventListener("dragleave", (evento) => {
        evento.preventDefault();
        arrastres -= 1;
        if (arrastres <= 0) {
            arrastres = 0;
            capa.hidden = true;
        }
    });

    window.addEventListener("drop", (evento) => {
        evento.preventDefault();
        arrastres = 0;
        capa.hidden = true;
        if (evento.dataTransfer && evento.dataTransfer.files.length) {
            subirArchivos(Array.from(evento.dataTransfer.files));
        }
    });

    window.addEventListener("resize", dibujarLineas);
    window.addEventListener("scroll", dibujarLineas, { passive: true });

    document.addEventListener("keydown", (evento) => {
        if (evento.key === "Escape") cerrarHistorial();
    });
}

async function iniciar() {
    aplicarTema(temaGuardado());
    conectarEventos();
    await comprobarEntorno();

    // Se retoma el ultimo caso si sigue existiendo; si no, se arranca en
    // limpio (sin crear nada todavia en el servidor).
    const anterior = ultimoCaso();
    if (anterior) {
        try {
            await abrirCaso(anterior);
            return;
        } catch (e) { /* el caso ya no existe en el servidor */ }
    }

    nuevoCaso();
}

iniciar();
