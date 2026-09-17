---
tags: [checku, decision, adr]
---

# ADR-002 — Preprocesamiento propio en vez de ImageCleaner

**Fecha**: 17/09/2026 · **Estado**: aceptada

## Contexto

`modules/ocr_module/preprocess/image_cleaner.py` ya existía y lo usa el
resto del proyecto. Es código de otro integrante del equipo.

Al probarlo con las cédulas amarillas aparecieron tres problemas:

1. **`_resize_image` solo REDUCE**: `if width > resize_width`. Las
   muestras reales vienen de 277 a 472 px de ancho, así que se quedaban
   en su tamaño original — justo lo que hace que el OCR falle
2. **Escribe un PDF de depuración en CADA llamada**
   (`create_image_stage_pdf`). Para un panel interactivo donde el usuario
   espera respuesta inmediata, eso es tiempo y basura en disco por página
3. **No expone la rotación**, y hacía falta aplicar la MISMA rotación a
   una versión a color para poder dibujar recuadros encima

## Decisión

Escribir `modules/cedula/imagen.py` con los mismos pasos (denoise →
blur → CLAHE → umbral adaptativo), pero:

- **Escala en ambos sentidos**, hasta 2000 px de ancho, con tope de 6×
- **No escribe nada en disco**
- Devuelve un **par de imágenes con la misma geometría**: una a color para
  mostrar y una binarizada para OCR

**No se modificó `image_cleaner.py`.** Es código ajeno y lo usa el resto
del proyecto; cambiarlo podía romperle el trabajo a otro.

## Consecuencias

- El OCR mejora mucho en material de baja resolución (ver
  [[Resultados de precisión]])
- Los recuadros pueden dibujarse exactamente sobre el dato
- Hay dos implementaciones parecidas de preprocesamiento en el repo. Vale
  la pena hablarlo con el equipo: si a todos les sirve el escalado hacia
  arriba, conviene unificar en `image_cleaner.py`. Anotado en
  [[Pendientes y próximos pasos]]
