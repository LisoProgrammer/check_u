---
tags: [checku, decision, adr]
---

# ADR-003 — Nombres por estructura, no por etiqueta

**Fecha**: 17/09/2026 · **Estado**: aceptada

## Contexto

En la [[Cédula amarilla con hologramas]] la etiqueta va DEBAJO del valor.
El primer intento fue buscar la palabra "APELLIDOS" y leer la línea
anterior.

**Resultado: 1 de 11 nombres correctos.**

Al volcar el OCR crudo se vio por qué. Las etiquetas están impresas en
letra muy chica y el OCR no las recupera:

```
y=  488  RIAÑO HIGUERA      ← el valor SÍ se lee bien
y=  603  ADOS               ← "APELLIDOS"
y=  650  VICKY LILIANA      ← el valor SÍ se lee bien
y=  763  NOLAAES            ← "NOMBRES"
```

Los valores se leen perfecto. Las etiquetas, no. Buscar la etiqueta para
ubicar el valor era buscar lo único ilegible de la tarjeta.

## Decisión

Usar la **estructura**, que en este formato nunca cambia:

```
NUMERO   <número grande>
<APELLIDOS>     ← primer renglón de texto grande debajo del número
<NOMBRES>       ← segundo renglón
```

Un renglón cuenta como "texto de campo" si sus palabras cumplen tres
condiciones a la vez:

1. Están en **MAYÚSCULA** y tienen 3+ letras
2. Su altura es **≥50 % de la del número** (el nombre va impreso casi tan
   grande; las etiquetas y el ruido son bastante más chicos)
3. **No se parecen a una etiqueta impresa** (comparación difusa ≥82 %
   contra APELLIDOS, NOMBRES, FIRMA, NUMERO...). Esto descarta "APELITOS"
   (82) y "ADOS" (86) sin descartar nombres cortos reales como "ROY" (80)

Además se limita la búsqueda a un 18 % del alto de la página por debajo
del número, para no confundir los nombres con el texto del reverso
(ciudad de nacimiento, de expedición), que también va en mayúscula.

## Sobre el umbral de confianza

Se bajó de 40 a **10**. Suena mal, pero está medido: en estas fotos
Tesseract reporta confianzas muy bajas **aunque acierte** — "LOPEZ" y
"ALONSO" salieron correctos con confianza 14, y un umbral de 40 los
borraba junto con el ruido.

El filtrado real lo hacen las tres condiciones de forma de arriba. La
confianza solo sirve para descartar lo manifiestamente ilegible.

## Resultado

Nombres correctos (≥85 % de similitud): **de 1/11 a 6/11**.

El mismo mecanismo se agregó como respaldo a la [[Cédula digital]], donde
recuperó el nombre completo que el [[MRZ]] truncaba ("HECTOR MANU" →
"HECTOR MANUEL CABARCAS CUADRADO").
