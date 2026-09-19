---
tags: [checku, arquitectura, modulo]
---

# modules/cedula

El módulo nuevo. Se encarga de lo que `modules/mrz` no puede: reconocer
cuál de los dos formatos es el documento y leer el que **no** tiene [[MRZ]].

No reemplaza nada: usa `modules/mrz` y `modules/ocr_module` por dentro.

## Archivos

| Archivo | Qué hace |
|---|---|
| `lectura.py` | **Punto de entrada**: `leer_cedula(paginas, progreso)`. Orquesta todo |
| `imagen.py` | Prepara el par de imágenes alineadas (color + binarizada) |
| `ocr_cajas.py` | OCR **con coordenadas** de cada palabra |
| `pdf417.py` | Decodifica el [[Código PDF417]] del reverso |
| `digital.py` | Lee la [[Cédula digital]] (MRZ + cruce con el frente) |
| `amarilla.py` | Lee la [[Cédula amarilla con hologramas]] |
| `similitud.py` | Compara nombres. Ver [[ADR-004 Umbral de similitud 85]] |
| `test_precision.py` | Mide precisión contra las muestras reales |

## Lo que aporta sobre lo que ya había

1. **Detección automática de formato** (la razón de existir del módulo)
2. **Lectura del formato amarillo**, que antes no se podía
3. **Coordenadas de cada dato**, para poder dibujar el recuadro sobre el
   documento en el panel. Antes el OCR solo devolvía texto

## Estructuras clave

```python
CampoLeido:
    valor: str | None       # "1043964337"
    caja: dict | None       # {x, y, ancho, alto} en píxeles
    fuente: str             # "pdf417" | "produccion" | "etiqueta" | "estructura" | "mrz"
    confianza: float | None
    pagina: int             # en qué página del documento está la caja
```

`fuente` es importante para el usuario: el panel muestra "leído del código
de barras PDF417" o "leído del MRZ" debajo de cada dato, para que quien
revisa sepa cuánto confiar.

La `caja` sale en píxeles y `lectura.py` la normaliza a fracciones 0..1
del tamaño de la página antes de mandarla al navegador, así no importa a
qué tamaño se esté mostrando el documento.

## Cómo usarlo

```python
from modules.cedula import leer_cedula

resultado = leer_cedula(paginas_pil, progreso=callback)
resultado.formato          # "digital" | "amarilla_hologramas" | "desconocido"
resultado.campos           # {"numero_documento": {...}, "nombre_completo": {...}}
resultado.paginas          # imágenes a color, alineadas con las cajas
```

Para medir precisión:
```
python -m modules.cedula.test_precision test_samples/Cedulas_Amarillas_Hologramas
```
