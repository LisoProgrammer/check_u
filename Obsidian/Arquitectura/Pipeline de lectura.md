---
tags: [checku, arquitectura, pipeline]
---

# Pipeline de lectura

De archivo subido a datos validados. Implementado en
`modules/cedula/lectura.py` + `webapp/app.py`.

```
archivo (PDF o imagen)
   │
   ├─ 1. CARGA ─────────── PyMuPDF primero, poppler como respaldo
   │                       (así no depende de instalar poppler en Windows)
   │
   ├─ 2. PREPARACIÓN ───── por cada página, dos imágenes con la MISMA geometría:
   │                         · display (color)  → se le muestra al usuario
   │                         · ocr (binarizada) → se le pasa a Tesseract
   │                       escalar a 2000 px · denoise · CLAHE · umbral adaptativo
   │                       · detectar y corregir inclinación
   │                       Ver [[ADR-002 Preprocesamiento propio]]
   │
   ├─ 3. OCR ───────────── dos pasadas:
   │                         · página completa (spa, psm 3)
   │                         · franja inferior (eng, psm 6, alfabeto A-Z0-9<)
   │                       ambas guardan la CAJA de cada palabra
   │
   ├─ 4. PDF417 ────────── intento de decodificar el [[Código PDF417]]
   │
   ├─ 5. ¿HAY MRZ? ─────── se buscan 3 líneas con "<" de relleno
   │       │
   │       ├── SÍ → [[Cédula digital]]      → digital.py
   │       └── NO → [[Cédula amarilla con hologramas]] → amarilla.py
   │                 (+ se emite el aviso "cambiando a formato amarilla")
   │
   ├─ 6. EXTRACCIÓN ────── cada módulo saca número, nombre, fecha, sexo
   │                       con su caja y su fuente
   │
   ├─ 7. RUI ───────────── se consulta el [[RUI - Ventanilla Social DNP]]
   │                       con el número extraído
   │
   ├─ 8. VALIDACIÓN ────── nombre del documento vs nombre del RUI, ≥85 %
   │                       → válida / inconsistente / por revisar
   │
   └─ 9. COMPARACIÓN ───── contra los demás documentos del caso, campo por campo
```

Cada paso emite un evento por **Server-Sent Events**, así el panel muestra
el avance en vivo sin recargar.

## La decisión del paso 5

Que la ausencia de MRZ sea la señal del formato antiguo es deliberado: es
una propiedad **estructural** del documento, no una heurística sobre el
color o la calidad de la foto. Una cédula digital siempre tiene MRZ; una
amarilla nunca lo tiene.

El aviso al usuario ("No se detecta MRZ: cambiando a cédula amarilla con
hologramas") aparece durante el proceso y desaparece al terminar: informa
sin dejar ruido permanente en pantalla.

## Cruce de fuentes (paso 6)

Para la [[Cédula digital]] no se confía ciegamente en el MRZ:

- Si el número del **frente** difiere del MRZ → **gana el frente** y se
  deja un aviso. El MRZ se desalinea entero si el OCR pierde un carácter;
  el número grande del frente no
- Si el nombre del frente es **más largo** → gana el frente. El MRZ corta
  a 30 caracteres por línea ("HECTOR MANU" en vez de "HECTOR MANUEL")
- La **caja** que se muestra siempre prefiere el texto del frente cuando
  dice lo mismo: señalar la franja MRZ para cuatro campos distintos no le
  dice nada a quien revisa
