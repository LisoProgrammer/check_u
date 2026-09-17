# Check_U - Instalar (si hace falta) y abrir el panel web
# ---------------------------------------------------------
# Uso: clic derecho sobre este archivo > "Ejecutar con PowerShell",
# o desde una terminal, parado en la carpeta del proyecto:
#
#     .\iniciar.ps1
#
# Se puede correr las veces que haga falta: la primera vez instala
# todo lo necesario; las siguientes veces esos pasos se saltan solos
# (ya estan hechos) y va directo a abrir el panel.

$ErrorActionPreference = "Stop"

# Correr siempre desde la carpeta donde esta este script, sin importar
# desde donde se haya lanzado (doble clic, otra terminal, etc.).
Set-Location $PSScriptRoot

Write-Host "== 1. Verificando Python ==" -ForegroundColor Cyan
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "No se encontro 'python' en el PATH." -ForegroundColor Red
    Write-Host "Instala Python 3.11+ desde https://www.python.org/downloads/ (marca la casilla 'Add python.exe to PATH' durante la instalacion) y vuelve a correr este script." -ForegroundColor Yellow
    exit 1
}
python --version

Write-Host "`n== 2. Entorno virtual (venv) ==" -ForegroundColor Cyan
if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    python -m venv venv
    Write-Host "Creado." -ForegroundColor Green
} else {
    Write-Host "Ya existe, se reutiliza." -ForegroundColor Yellow
}
# Se usa el python/pip DE ADENTRO del venv por su ruta completa (nunca
# se "activa" el venv): asi no depende de Activate.ps1 ni de PATH, y se
# evita un bug ya visto donde reactivar el venv reseteaba el PATH y
# hacia que Tesseract "desapareciera" entre un script y el siguiente.
$pythonVenv = ".\venv\Scripts\python.exe"
$pipVenv = ".\venv\Scripts\pip.exe"

Write-Host "`n== 3. Dependencias de Python ==" -ForegroundColor Cyan
& $pipVenv install --upgrade pip | Out-Null
# zxing-cpp lee el codigo de barras PDF417 del reverso de la cedula
# amarilla con hologramas; rapidfuzz compara nombres contra el RUI.
& $pipVenv install pdf2image pytesseract pillow opencv-python flask requests pymupdf zxing-cpp rapidfuzz

Write-Host "`n== 4. Tesseract OCR ==" -ForegroundColor Cyan
$tesseract = Get-Command tesseract -ErrorAction SilentlyContinue

if (-not $tesseract) {
    Write-Host "No esta en el PATH. Intentando instalarlo con winget (puede pedirte confirmar en una ventana aparte)..." -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        try {
            winget install -e --id UB-Mannheim.TesseractOCR --accept-source-agreements --accept-package-agreements
        } catch {
            Write-Host "winget no pudo instalarlo solo: $($_.Exception.Message)" -ForegroundColor Red
        }
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
        Write-Host "No se encontro 'winget' en este equipo (viene con Windows 10/11 actualizado, o desde 'App Installer' en la Microsoft Store)." -ForegroundColor Red
        Write-Host "Instala Tesseract a mano desde https://github.com/UB-Mannheim/tesseract/wiki (marca 'Spanish' y 'Add to PATH')." -ForegroundColor Yellow
    }
} else {
    Write-Host "Encontrado: $($tesseract.Source)" -ForegroundColor Green
}

if ($tesseract) {
    $tesseractDir = Split-Path $tesseract.Source -Parent

    # El instalador silencioso de winget no siempre agrega la carpeta de
    # Tesseract al PATH permanente (el que queda guardado en el registro
    # de Windows) -- se agrega aca para que quede disponible tambien en
    # terminales nuevas, sin depender de repetir este script.
    try {
        $pathUsuario = [Environment]::GetEnvironmentVariable("Path", "User")
        if ($pathUsuario -notlike "*$tesseractDir*") {
            $nuevoPathUsuario = if ([string]::IsNullOrEmpty($pathUsuario)) { $tesseractDir } else { "$pathUsuario;$tesseractDir" }
            [Environment]::SetEnvironmentVariable("Path", $nuevoPathUsuario, "User")
            Write-Host "Carpeta de Tesseract agregada al PATH de Usuario (permanente)." -ForegroundColor Green
        }
    } catch {
        Write-Host "No se pudo guardar el PATH de forma permanente; no es grave, el panel lo detecta igual por su cuenta." -ForegroundColor Yellow
    }
    if ($env:Path -notlike "*$tesseractDir*") {
        $env:Path += ";$tesseractDir"
    }

    # winget instala Tesseract sin el selector de idiomas del instalador
    # interactivo, asi que casi siempre falta 'spa' (espanol).
    $tessdataDir = Join-Path $tesseractDir "tessdata"
    $spaFile = Join-Path $tessdataDir "spa.traineddata"
    if (Test-Path $spaFile) {
        Write-Host "Paquete de idioma espanol (spa) ya esta instalado." -ForegroundColor Green
    } elseif (Test-Path $tessdataDir) {
        Write-Host "Falta el idioma espanol (spa). Descargandolo..." -ForegroundColor Yellow
        try {
            Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata" -OutFile $spaFile
            Write-Host "Instalado en $spaFile" -ForegroundColor Green
        } catch {
            Write-Host "No se pudo descargar automaticamente: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "Descargalo a mano desde https://github.com/tesseract-ocr/tessdata y colocalo en $tessdataDir" -ForegroundColor Yellow
        }
    } else {
        Write-Host "No se encontro la carpeta tessdata en $tessdataDir; revisa tu instalacion de Tesseract." -ForegroundColor Yellow
    }
}

Write-Host "`n== 5. Lectura de PDF (PyMuPDF) ==" -ForegroundColor Cyan
Write-Host "Ya quedo instalado en el paso 3 (pip); no necesita nada mas en Windows (poppler es opcional, solo como respaldo)." -ForegroundColor Green

Write-Host "`n== 6. Verificacion final del entorno ==" -ForegroundColor Cyan
& $pythonVenv webapp\entorno.py
$entornoOk = ($LASTEXITCODE -eq 0)

if (-not $entornoOk) {
    Write-Host "`n== Falta corregir algo antes de abrir el panel ==" -ForegroundColor Yellow
    Write-Host "Revisa el reporte de arriba, corrigelo y vuelve a correr '.\iniciar.ps1'." -ForegroundColor Yellow
    Write-Host "Si acabas de instalar Tesseract y el problema persiste, prueba abriendo una terminal nueva (o reiniciando VS Code) y corriendo este script otra vez." -ForegroundColor Yellow
    exit 1
}

Write-Host "`n== Todo listo: abriendo Check_U ==" -ForegroundColor Cyan
Write-Host "http://localhost:5000" -ForegroundColor White
Write-Host "(para cerrar el panel: Ctrl+C en esta ventana)" -ForegroundColor DarkGray

# El servidor tarda un par de segundos en arrancar; se abre el
# navegador desde un job aparte para no bloquear el arranque de abajo,
# que corre en primer plano (asi Ctrl+C lo cierra normal y se ve el
# log del servidor en esta misma ventana).
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:5000"
} | Out-Null

& $pythonVenv webapp\app.py
