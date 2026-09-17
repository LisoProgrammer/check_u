---
tags: [checku, decision, adr]
---

# ADR-004 — Similitud de nombres al 85 % con token_sort_ratio

**Fecha**: 17/09/2026 · **Estado**: aceptada

## Contexto

El equipo acordó validar comparando el nombre extraído contra el que
devuelve el [[RUI - Ventanilla Social DNP|RUI]], con un mínimo de **85 %**.

Comparar texto crudo no sirve: dos escrituras del MISMO nombre casi nunca
son idénticas carácter por carácter.

- El [[MRZ]] entrega "apellidos, nombres"; el RUI entrega "nombres apellidos"
- Las tildes y la Ñ se pierden o se leen mal
- El OCR agrega o come letras sueltas
- El MRZ recorta a 30 caracteres por línea

## Decisión

1. **Normalizar**: mayúsculas, sin tildes, sin signos, un solo espacio.
   La Ñ se convierte en N a propósito: el RUI y el OCR no siempre coinciden
2. **Comparar con `token_sort_ratio`** de rapidfuzz, que ordena las
   palabras antes de comparar

## Por qué NO `token_set_ratio`

Daría 100 % cuando un nombre es subconjunto del otro. "HECTOR" contra
"HECTOR MANUEL CABARCAS CUADRADO" pasaría como coincidencia perfecta, y
**ese es justo el error que esta validación tiene que atrapar**.

Medido con `token_sort_ratio`, ese caso da **32 % → inconsistente**. ✓

## Comportamiento verificado

| Caso | Similitud | Estado |
|---|---|---|
| Nombre idéntico | 100 % | válida |
| Orden invertido (MRZ vs RUI) | 100 % | válida |
| MRZ truncado ("HECTOR MANU") | 97 % | válida |
| Con/sin tildes (RIAÑO vs RIANO) | 100 % | válida |
| Error de OCR (GRACIA vs GARCIA) | 96 % | válida |
| **Otra persona** | 43 % | **inconsistente** |
| **Subconjunto ("HECTOR")** | 32 % | **inconsistente** |

## Nota sobre los números de documento

Los números **no** usan similitud: se comparan exactos, sin puntos ni
ceros a la izquierda. Un 95 % de parecido en una cédula no significa "casi
correcto", significa que es el documento de otra persona.
