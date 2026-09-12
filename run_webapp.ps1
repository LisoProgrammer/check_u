# check_u - Lanzar el panel web local
# Ejecutar desde la raiz del proyecto (Check_U), en PowerShell.

if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "No existe el entorno virtual todavia. Corre primero .\setup_windows.ps1" -ForegroundColor Red
    exit 1
}

& .\venv\Scripts\Activate.ps1
Write-Host "Abriendo http://localhost:5000 ..." -ForegroundColor Cyan
Start-Process "http://localhost:5000"
python webapp\app.py
