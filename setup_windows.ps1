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
            Write-Host "IMPORTANTE: abre una terminal nueva (o reinicia PowerShell/VS Code) antes de correr 'run_webapp.ps1', para que el PATH quede guardado de forma permanente." -ForegroundColor Yellow
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
    tesseract --list-langs
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
    Write-Host "Revisa el reporte de arriba. Si instalaste Tesseract recien, es posible que necesites ABRIR UNA TERMINAL NUEVA para que el PATH quede guardado, y luego volver a correr '.\setup_windows.ps1' para confirmar." -ForegroundColor Yellow
}
