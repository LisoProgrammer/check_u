---
tags: [checku, herramientas]
---

# Herramientas y dependencias

## Para correr el proyecto

| Herramienta | Para qué | Cómo se instala |
|---|---|---|
| **Python 3.11+** | Todo el backend | python.org, marcando "Add python.exe to PATH" |
| **Tesseract OCR** | Reconocimiento de texto | `iniciar.ps1` lo instala con `winget` |
| `spa.traineddata` | Idioma español para Tesseract | `iniciar.ps1` lo descarga si falta |

## Paquetes de Python

| Paquete | Para qué |
|---|---|
| `flask` | El servidor del panel |
| `pytesseract` | Puente a Tesseract, y el `image_to_data` que da las **cajas** |
| `opencv-python` | Escalado, denoise, CLAHE, umbral, rotación |
| `pillow` | Manejo de imágenes |
| `pymupdf` | Lectura de PDF **sin binarios externos** (evita depender de poppler) |
| `pdf2image` | Lectura de PDF con poppler, solo como respaldo |
| `requests` | Consulta al [[RUI - Ventanilla Social DNP]] |
| **`zxing-cpp`** | Decodifica el [[Código PDF417]]. Gratis, sin licencia |
| **`rapidfuzz`** | Similitud de nombres. Ver [[ADR-004 Umbral de similitud 85]] |

Los dos últimos son nuevos. Ya están en `iniciar.ps1` y en el verificador
`webapp/entorno.py`, así que se instalan solos.

> Sobre zxing-cpp: se eligió frente a otras librerías de PDF417 porque no
> requiere licencia comercial. La referencia más citada para leer cédulas
> colombianas (`Eitol/colombian-cedula-reader`) usa Dynamsoft en su parte
> de Python, que es de pago. De ahí solo se tomó la **estructura de bytes**
> del código, que está documentada en [[Código PDF417]].

## Para desarrollar y probar

| Herramienta | Para qué |
|---|---|
| **Playwright** | Pruebas del panel en un navegador real. Ver [[Metodología de pruebas]] |
| `pwsh` (PowerShell Core) | Verificar `iniciar.ps1` en Linux antes de tocar Windows |
| `git` | Control de versiones |

## El script de arranque

`iniciar.ps1` hace todo en un solo paso y se puede correr las veces que
haga falta:

1. Verifica Python
2. Crea el `venv` si no existe
3. Instala las dependencias
4. Detecta Tesseract; si falta, lo instala con `winget` y le agrega el
   idioma español
5. **Guarda la carpeta de Tesseract en el PATH de Usuario de forma
   permanente** (el instalador silencioso de winget no siempre lo hace)
6. Corre `webapp/entorno.py` para confirmar que todo quedó bien
7. Abre el navegador y levanta el panel

Detalle de implementación que importa: **nunca activa el venv**. Llama a
`.\venv\Scripts\python.exe` por ruta completa. Activar el venv reseteaba
el PATH y hacía que Tesseract "desapareciera" entre un script y el
siguiente — un bug real que costó una sesión entera de diagnóstico.
