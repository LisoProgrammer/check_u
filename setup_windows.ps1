# check_u - Setup del entorno Python local (Windows)
# Ejecutar desde dentro de la carpeta del proyecto (Check_U), en PowerShell.

$ErrorActionPreference = "Stop"

Write-Host "== 1. Verificando Python ==" -ForegroundColor Cyan
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "No se encontro 'python' en el PATH. Instala Python 3.11+ desde https://www.python.org/downloads/ (marca 'Add python.exe to PATH') y vuelve a correr este script." -ForegroundColor Red
    exit 1
}
python --version

Write-Host "`n== 2. Creando entorno virtual (venv) ==" -ForegroundColor Cyan
if (-not (Test-Path ".\venv")) {
    python -m venv venv
} else {
    Write-Host "Ya existe .\venv, se reutiliza." -ForegroundColor Yellow
}

Write-Host "`n== 3. Instalando dependencias de Python ==" -ForegroundColor Cyan
& .\venv\Scripts\pip.exe install --upgrade pip
& .\venv\Scripts\pip.exe install pdf2image pytesseract pillow opencv-python flask requests pymupdf

Write-Host "`n== 4. Verificando Tesseract OCR ==" -ForegroundColor Cyan
$tesseract = Get-Command tesseract -ErrorAction SilentlyContinue

if (-not $tesseract) {
    Write-Host "Tesseract no esta en el PATH." -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue

    if ($winget) {
        Write-Host "Intentando instalarlo automaticamente con winget (puede pedirte confirmar en una ventana aparte)..." -ForegroundColor Yellow
        try {
            winget install -e --id UB-Mannheim.TesseractOCR --accept-source-agreements --accept-package-agreements
        } catch {
            Write-Host "winget no pudo instalarlo solo: $($_.Exception.Message)" -ForegroundColor Red
        }

        # El instalador de winget no actualiza el PATH de ESTA sesion de
        # PowerShell (solo el de sesiones nuevas). Si el ejecutable quedo
        # en la ruta habitual, lo agregamos al PATH de este proceso para
        # poder seguir con el resto del setup sin reabrir la terminal.
        $tesseractPathComun = "C:\Program Files\Tesseract-OCR"
        if ((Test-Path "$tesseractPathComun\tesseract.exe") -and ($env:Path -notlike "*$tesseractPathComun*")) {
            $env:Path += ";$tesseractPathComun"
        }

        $tesseract = Get-Command tesseract -ErrorAction SilentlyContinue
        if ($tesseract) {
            Write-Host "Tesseract instalado: $($tesseract.Source)" -ForegroundColor Green
        } else {
            Write-Host "No se pudo confirmar la instalacion. Instalalo a mano desde https://github.com/UB-Mannheim/tesseract/wiki (marca 'Add to PATH' y el idioma 'Spanish')." -ForegroundColor Red
        }
    } else {
        Write-Host "No se encontro 'winget' en este equipo (viene con Windows 10/11 actualizado, desde 'App Installer' en la Microsoft Store)." -ForegroundColor Red
        Write-Host "Instala Tesseract a mano desde https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Yellow
        Write-Host "Durante la instalacion, en 'Additional language data' marca 'Spanish' (spa), y marca 'Add to PATH' si te lo ofrece." -ForegroundColor Yellow
    }
} else {
    Write-Host "Tesseract encontrado: $($tesseract.Source)" -ForegroundColor Green
}

if ($tesseract) {
    $tesseractDir = Split-Path $tesseract.Source -Parent

    # El instalador silencioso de winget deja tesseract.exe en disco pero
    # NO siempre agrega su carpeta al PATH de Usuario/Maquina (el que
    # queda guardado de forma permanente en el registro de Windows) -
    # esto es lo que causaba que, aunque este mismo script lo encontrara
    # bien, 'run_webapp.ps1' fallara despues al buscarlo (una terminal
    # nueva, o volver a activar el venv, no tenian de donde heredarlo).
    # Lo agregamos aqui de forma permanente para que no vuelva a pasar.
    try {
        $pathUsuario = [Environment]::GetEnvironmentVariable("Path", "User")
        if ($pathUsuario -notlike "*$tesseractDir*") {
            Write-Host "Agregando '$tesseractDir' al PATH de Usuario (permanente)..." -ForegroundColor Yellow
            $nuevoPathUsuario = if ([string]::IsNullOrEmpty($pathUsuario)) { $tesseractDir } else { "$pathUsuario;$tesseractDir" }
            [Environment]::SetEnvironmentVariable("Path", $nuevoPathUsuario, "User")
            Write-Host "Listo. Quedara disponible en terminales nuevas sin repetir este paso." -ForegroundColor Green
        }
    } catch {
        Write-Host "No se pudo guardar el PATH de forma permanente ($($_.Exception.Message)); no es grave, el panel web igual lo detecta por su cuenta." -ForegroundColor Yellow
    }
    if ($env:Path -notlike "*$tesseractDir*") {
        $env:Path += ";$tesseractDir"
    }

    # winget instala Tesseract en modo silencioso, sin el selector de
    # idiomas del instalador interactivo - asi que casi siempre falta
    # 'spa' (espanol). Lo descargamos aparte si no esta, en vez de pedir
    # reinstalar todo a mano.
    $tessdataDir = Join-Path $tesseractDir "tessdata"
    $spaFile = Join-Path $tessdataDir "spa.traineddata"

    $idiomas = & tesseract --list-langs 2>&1
    Write-Host $idiomas

    if (Test-Path $spaFile) {
        Write-Host "Paquete de idioma espanol (spa) ya esta instalado." -ForegroundColor Green
    } elseif (Test-Path $tessdataDir) {
        Write-Host "Falta el paquete de idioma espanol (spa). Descargandolo..." -ForegroundColor Yellow
        try {
            Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata" -OutFile $spaFile
            Write-Host "Paquete de idioma espanol instalado en $spaFile" -ForegroundColor Green
        } catch {
            Write-Host "No se pudo descargar automaticamente: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "Descargalo a mano desde https://github.com/tesseract-ocr/tessdata y colocalo en $tessdataDir" -ForegroundColor Yellow
        }
    } else {
        Write-Host "No se encontro la carpeta tessdata en $tessdataDir para agregar el idioma espanol; revisa tu instalacion de Tesseract." -ForegroundColor Yellow
    }
}

Write-Host "`n== 5. Verificando lectura de PDF (PyMuPDF / Poppler) ==" -ForegroundColor Cyan
Write-Host "PyMuPDF ya quedo instalado en el paso 3 (pip) y es la forma principal de leer PDFs: no necesita nada mas instalado en Windows." -ForegroundColor Green
$poppler = Get-Command pdftoppm -ErrorAction SilentlyContinue
if ($poppler) {
    Write-Host "Poppler tambien esta disponible ($($poppler.Source)) - se usa como respaldo, no es obligatorio." -ForegroundColor Green
} else {
    Write-Host "Poppler no esta instalado, pero no hace falta: la app usa PyMuPDF. Es opcional; si igual lo quieres:" -ForegroundColor Yellow
    Write-Host "  https://github.com/oschwartz10612/poppler-windows/releases (agrega 'Library\bin' al PATH)." -ForegroundColor Yellow
}

Write-Host "`n== 6. Verificacion final del entorno ==" -ForegroundColor Cyan
& .\venv\Scripts\python.exe webapp\entorno.py
$entornoOk = ($LASTEXITCODE -eq 0)

if ($entornoOk) {
    Write-Host "`n== Listo ==" -ForegroundColor Cyan
    Write-Host "Para probar el modulo de OCR por separado:" -ForegroundColor Cyan
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "  python -m modules.ocr_module.test.test_ocr" -ForegroundColor White
    Write-Host "`nNOTA: ese test busca 'modules/test_data/cc2_escaneada.pdf', que no esta en el repo (solo existe 'cc_escaneada.pdf'). Puede que Lisandro tenga ese archivo local sin subir a git." -ForegroundColor Yellow

    Write-Host "`n== Panel web (flujo completo) ==" -ForegroundColor Cyan
    Write-Host "  .\run_webapp.ps1" -ForegroundColor White
    Write-Host "  (o a mano: .\venv\Scripts\Activate.ps1  y luego  python webapp\app.py)" -ForegroundColor White
    Write-Host "  Luego abre http://localhost:5000 en el navegador." -ForegroundColor White
} else {
    Write-Host "`n== Falta corregir algo antes de usar el panel ==" -ForegroundColor Yellow
    Write-Host "Revisa el reporte de arriba. Si acabas de instalar algo y el problema persiste, prueba a abrir una terminal nueva (o reiniciar VS Code) y correr '.\setup_windows.ps1' otra vez." -ForegroundColor Yellow
}
