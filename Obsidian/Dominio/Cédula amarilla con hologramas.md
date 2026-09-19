---
tags: [checku, dominio, cedula]
aliases: [cédula amarilla, cédula vieja, formato antiguo]
---

# Cédula amarilla con hologramas

**Nombre oficial** que usa la Registraduría Nacional del Estado Civil para
el formato expedido entre **2000 y 2020**. Ver [[ADR-001 Nombre del formato antiguo]]
para por qué se usa este nombre en todo el código.

**Sigue siendo válida**: la Registraduría dice que ambos formatos conviven
mientras se masifica la [[Cédula digital]].

## Qué trae

**Frente**:
```
REPUBLICA DE COLOMBIA
IDENTIFICACION PERSONAL
CEDULA DE CIUDADANIA
NUMERO        40.048.750          [foto]
RIAÑO HIGUERA          <- valor
APELLIDOS              <- etiqueta, DEBAJO del valor
VICKY LILIANA          <- valor
NOMBRES                <- etiqueta, DEBAJO del valor
<firma>
FIRMA
```

**Reverso**: huella del índice derecho, fecha y lugar de nacimiento,
estatura, G.S. RH, sexo, fecha y lugar de expedición, firma del
Registrador, el **[[Código PDF417]]** y una línea de producción.

## Las tres cosas que definen cómo se lee

### 1. NO tiene MRZ

Todo el parseo por posiciones fijas de `modules/mrz` no aplica. La
ausencia de MRZ es justamente la señal que usa el sistema para saber que
es este formato.

### 2. La etiqueta va DEBAJO del valor

Al revés que la digital. Y peor: en fotos de calidad normal esas
etiquetas salen **ilegibles** ("ADOS" por APELLIDOS, "NOLAAES" por
NOMBRES). Por eso los nombres se ubican por estructura, no por etiqueta:
ver [[ADR-003 Nombres por estructura]].

### 3. La línea de producción repite el número

```
A-0704900-00150296-F-0040048750-20090211
│    │        │      │     │         └── fecha de producción
│    │        │      │     └── número de documento, a 10 dígitos
│    │        │      └── sexo
│    │        └── consecutivo
│    └── código de la registraduría
└── letra de serie
```

`0040048750` → quitando ceros → `40048750`. Es una **segunda fuente
independiente** del OCR del número grande del frente, y su patrón es tan
rígido que es fácil validar que se leyó bien.

## Orden de confianza al resolver el número

1. **[[Código PDF417]]** — lectura digital con corrección de errores
2. **Línea de producción** — patrón rígido, verificable
3. **Número grande del frente** — OCR suelto
