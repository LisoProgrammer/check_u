---
tags: [checku, dominio, formato]
---

# MRZ (zona de lectura mecánica)

Franja de 3 líneas × 30 caracteres impresa en el reverso de la
[[Cédula digital]]. Solo admite `A-Z`, `0-9` y `<` como relleno.

Ejemplo real (de una muestra de prueba):
```
ICCOL009196740005001<<<<<<<<<<
0410298M3211164COL1043964337<0
MORALES<BLANCO<<JORGE<<<<<<<<<
```

## Cómo se parsea

`modules/mrz/get_info.py` corta por **posiciones fijas**. Línea 2:

| Posición | Campo |
|---|---|
| 0-6 | fecha de nacimiento (AAMMDD) |
| 6 | dígito de chequeo |
| 7 | sexo |
| 8-14 | fecha de expiración |
| 15-18 | nacionalidad |
| 18-28 | **número de documento** |

## La fragilidad que hay que tener presente

Cortar por posición fija significa que **si el OCR pierde o agrega un solo
carácter, todos los campos siguientes se corren**. No falla ruidosamente:
devuelve un número que parece válido pero es de otra persona.

Dos defensas contra eso:

1. **Cruce con el texto impreso del frente** — el número grande no
   depende de posiciones (ver [[Pipeline de lectura]])
2. **La nacionalidad como señal** — va justo antes del número. Si no lee
   `COL`, o es un extranjero o el MRZ se corrió. Se avisa sin decidir por
   el usuario.

> Cuidado con la nacionalidad: Tesseract lee `C0L` (cero) muy seguido
> aunque el resto esté perfecto. La comparación tolera esa confusión.

## Nota sobre el dígito de chequeo

Se intentó usar `document_number_check` como red de seguridad y **no
funcionó**: ninguno de los 3 números reales coincide con el dígito
almacenado. O el formato del MRZ que genera el equipo no usa la fórmula
estándar, o el mapeo de ese campo en `get_info.py` apunta a otra cosa.
Queda como pregunta para quien construyó la generación del MRZ.
