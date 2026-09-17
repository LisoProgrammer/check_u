---
tags: [checku, arquitectura, backend]
---

# Backend del panel

`webapp/app.py`. Flask con hilos y Server-Sent Events.

## Conceptos

**Caso** = una solicitud, es decir una persona con los documentos que
presentó. Vive en disco, así que se puede cerrar el navegador y retomarlo.
Ver [[ADR-005 Casos en archivos JSON]].

**Documento** = un archivo dentro de un caso. Hoy solo cédula, pero ya
guarda un campo `tipo` y las comparaciones están escritas para N
documentos, porque vienen los otros 4 del [[Alcance LIA]].

## Estados

Los mismos nombres del formato de inscripción:

| Estado | Cuándo |
|---|---|
| `valida` | El RUI encontró a la persona y el nombre coincide ≥85 % |
| `inconsistente` | El RUI la encontró pero el nombre NO coincide |
| `por_revisar` | No se pudo decidir: no se leyó el número, el RUI no respondió, o no hay registro |

El estado del **caso** es el peor de sus documentos, y una discrepancia
entre dos documentos también lo vuelve `inconsistente`.

Que `por_revisar` exista es el punto: no pretende resolver todo
automáticamente, sino **separar lo que necesita ojo humano de lo que no**.

## API

| Ruta | Método | Qué hace |
|---|---|---|
| `/api/casos` | GET | Lista casos (oculta los vacíos) |
| `/api/casos` | POST | Crea un caso |
| `/api/casos/<id>` | GET | Caso completo con documentos y comparaciones |
| `/api/casos/<id>` | DELETE | Borra el caso y su carpeta |
| `/api/casos/<id>/documentos` | POST | Sube un archivo y arranca el proceso |
| `/api/casos/<id>/documentos/<doc>` | DELETE | Quita un documento y recompara |
| `.../paginas/<n>` | GET | La imagen de esa página |
| `/api/trabajos/<id>/stream` | GET | **SSE** con el avance |
| `/api/salud` | GET | Estado del entorno (Tesseract, PyMuPDF, paquetes) |

## Eventos SSE

```
{tipo: "etapa",         etapa: "cargando" | "rui"}
{tipo: "progreso",      etapa: "preparando" | "ocr" | "detectando_formato" |
                               "formato" | "extrayendo" | "listo",
                        cambio: true, mensaje: "No se detecta MRZ..."}
{tipo: "paginas",       paginas: [...]}
{tipo: "documento",     datos: {...}}
{tipo: "comparaciones", comparaciones: [...], estado, titulo}
{tipo: "error",         mensaje}
{tipo: "fin"}
```

## Comparación entre documentos

Se compara **cada par** de documentos del caso, campo por campo. El número
se compara **exacto** (un 95 % de parecido en un número de cédula no
significa "casi correcto", significa que es otra persona); el nombre usa
el umbral de similitud.

De cada campo se guarda la caja de los dos lados, que es lo que le permite
al panel dibujar la línea que une un dato con el otro.
