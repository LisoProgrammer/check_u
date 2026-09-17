---
tags: [checku, dominio, formato]
---

# Código PDF417

Código de barras 2D en el reverso de la [[Cédula amarilla con hologramas]].
**La [[Cédula digital]] no lo usa** (usa QR + [[MRZ]]).

Es la fuente **más confiable** para el formato amarillo: mientras el texto
impreso hay que adivinarlo con OCR, el PDF417 trae los datos codificados
digitalmente y con corrección de errores. O se lee bien o no se lee — nunca
devuelve un número "casi correcto".

## Estructura

531 bytes con posiciones fijas. Los campos de texto vienen rellenados a la
derecha con bytes nulos.

| Campo | Bytes |
|---|---|
| Código AFIS | 2-10 |
| Tarjeta de huella | 40-48 |
| **Número de documento** | 48-58 |
| Primer apellido | 58-81 |
| Segundo apellido | 81-104 |
| Primer nombre | 104-127 |
| Segundo nombre | 127-150 |
| Sexo | 151-152 |
| Año / mes / día de nacimiento | 152-160 |
| Municipio / departamento | 160-165 |
| RH | 166-168 |

25 filas × 21 columnas de datos, nivel de seguridad 5.

## Implementación

`modules/cedula/pdf417.py`, con la librería **zxing-cpp** (gratis, sin
licencia). Se prueban varias versiones de la imagen (original, ampliada al
doble, con contraste forzado) porque el decodificador es sensible al
tamaño de las barras.

Validaciones antes de aceptar el resultado: el número debe tener ≥6
dígitos, y el primer apellido y el primer nombre deben ser letras. Si no,
devuelve `None` y la lectura cae al OCR — mejor eso que entregar basura.

## Limitación conocida y medida

**No decodifica en ninguna de las 11 muestras de prueba.** Se comprobó
explícitamente. Son imágenes de 277-472 px de ancho para las dos caras
juntas; a esa resolución las barras se funden. Necesita ~1000 px o más
solo para el código.

Esto no es un defecto del código: es la razón por la que existe el
respaldo por OCR y la línea de producción.
