---
tags: [checku, pendientes]
---

# Pendientes y próximos pasos

## Inmediato, de la mano

- [ ] **Borrar `test_samples/Cedulas_Amarillas/`** (la carpeta vieja). Las
      11 muestras ya están copiadas en `Cedulas_Amarillas_Hologramas/`.
      No se pudo borrar desde acá: el acceso a comandos en el equipo está
      caído por una actualización de Windows del 8 de septiembre
- [ ] **Conseguir 2-3 escaneos reales** de cédula amarilla (aunque sean de
      familiares, tapando lo que quieran). Es lo que más mejoraría los
      números de [[Resultados de precisión]]: con resolución real el
      [[Código PDF417]] decodifica y el número deja de depender del OCR

## Del alcance del proyecto

Lo que el [[Alcance LIA]] compromete y todavía no existe:

- [ ] Login / autenticación (estudiante y personal de grados)
- [ ] Los otros 4 documentos: Evaluación de Grado de Banner, estampilla
      Pro-Cultura, Saber Pro, Paz y Salvo de Biblioteca
- [ ] **Firma criptográfica del Paz y Salvo** y su verificación. Es un
      subsistema entero y nadie lo ha empezado
- [ ] Estadísticas con gráficos de barras y circulares
- [ ] Conectar `frontend/` (las maquetas de Jorge) con el backend
- [ ] `modules/check_id/orquestador.py` está vacío

> La comparación entre documentos **ya está escrita para N documentos**,
> no para dos fijos. Cuando lleguen los otros, solo hay que agregar su
> extractor; el cruce y la interfaz funcionan igual.

## Técnicos, para hablar con el equipo

- [ ] **Unificar el preprocesamiento**. Hoy hay dos implementaciones:
      `image_cleaner.py` (del equipo) y `modules/cedula/imagen.py`. Ver
      [[ADR-002 Preprocesamiento propio]]. Si a todos les sirve el escalado
      hacia arriba, conviene unificar
- [ ] **Preguntar por el dígito de chequeo del [[MRZ]]**: no coincide con
      ninguna de las 3 cédulas reales. ¿Qué fórmula usa el generador?
- [ ] `image_cleaner.py` sigue escribiendo un PDF de depuración en
      `test_image_cleaner/` en cada corrida
- [ ] La rama `mejoras_modulo_ocr` de GitHub está vieja (mayo 2026) y le
      falta casi todo el código actual. ¿Se puede borrar?

## Si el panel deja de ser local

Hoy los casos son archivos JSON en disco ([[ADR-005 Casos en archivos JSON]])
y el panel corre sin autenticación en `localhost`. Si pasa a ser un
servicio compartido hay que revisar las dos cosas: base de datos real y
control de acceso, porque son documentos de identidad de personas.

## Ideas de validación adicionales (sin decidir)

- Longitud y rango del número según la fecha de expedición
- Cruce de la fecha de nacimiento leída contra la que devuelve el RUI
- Mostrar las discrepancias en el historial, no solo en el caso abierto
