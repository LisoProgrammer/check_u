# Check_U

Proyecto de ingeniería (UTB): lee una **cédula** (PDF o foto/escaneo),
extrae los datos (nombre, número de documento, fecha de nacimiento,
edad, sexo) y consulta el RUI del DNP con el número obtenido, todo
desde un panel web local.

## Cómo usarlo (Windows)

1. Si no lo tenés, instalá Python 3.11 o más nuevo desde
   [python.org/downloads](https://www.python.org/downloads/) — al
   instalarlo, marcá la casilla **"Add python.exe to PATH"**.
2. Descargá o cloná este repositorio en tu computador.
3. Abrí la carpeta del proyecto y hacé doble clic en **`iniciar.ps1`**
   (o, desde una terminal parada en esa carpeta, corré `.\iniciar.ps1`).

Ese único script se encarga de todo:

- Crea el entorno virtual de Python (`venv`) si no existe.
- Instala las librerías necesarias (`pdf2image`, `pytesseract`,
  `pillow`, `opencv-python`, `flask`, `requests`, `pymupdf`).
- Detecta si falta Tesseract OCR y trata de instalarlo solo con
  `winget` (incluido el paquete de idioma español); si no puede, te
  deja el link para instalarlo a mano.
- Verifica que todo haya quedado bien configurado.
- Abre `http://localhost:5000` en el navegador y deja el panel
  corriendo en esa misma ventana.

**Se puede correr las veces que haga falta**: la primera vez instala
todo; las siguientes veces esos pasos ya están hechos, se saltan
solos, y el script va directo a abrir el panel. Para cerrarlo, `Ctrl+C`
en la ventana de la terminal.

Si el script se detiene con un error, va a decir exactamente qué
falta y cómo solucionarlo — corregilo y volvé a correr `.\iniciar.ps1`.

## Qué hace el panel

1. Subís una **cédula** (PDF o imagen).
2. Al darle a **Procesar**, el archivo pasa por varias etapas visibles
   en tiempo real (leyendo → convirtiendo → procesando → corrigiendo
   inclinación → limpiando/OCR).
3. Se extraen los datos (nombre, número de documento, fecha de
   nacimiento, edad, sexo) y se muestran apenas termina.
4. Se consulta el RUI del DNP con el número de documento obtenido.
5. Cada procesamiento queda guardado y aparece en la pestaña
   **Historial**.

## Estructura del proyecto

- `iniciar.ps1` — instala todo lo necesario (si hace falta) y abre el
  panel web. Es lo único que hay que correr.
- `webapp/` — servidor Flask, interfaz web y su propio
  [README](webapp/README.md) con el detalle técnico y el historial de
  bugs encontrados y corregidos.
- `modules/ocr_module/` — lectura de PDF/imagen y OCR (Tesseract).
- `modules/mrz/` — parseo del MRZ (franja de datos de la cédula).
- `modules/check_id/` — consulta al RUI del DNP.
- `test_samples/` — cédulas de prueba (reales, para pruebas locales;
  no se suben al repositorio).

## Notas para el equipo

- El desarrollo y las pruebas de este proyecto se hacen en Windows;
  no se mantienen instrucciones para Linux/WSL.
- Si alguien agrega una dependencia nueva de Python, hay que sumarla
  también a la lista de instalación dentro de `iniciar.ps1` (paso "3.
  Dependencias de Python"), si no cada quien tiene que instalarla a
  mano.
