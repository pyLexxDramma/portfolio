# Скрипт для запуска сервера с активированным venv
$ErrorActionPreference = "Stop"

Write-Host "=== Запуск сервера Unified Parser ===" -ForegroundColor Green
Write-Host ""

# Переходим в директорию проекта
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Проверяем наличие venv
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "ОШИБКА: Виртуальное окружение не найдено!" -ForegroundColor Red
    Write-Host "Создайте venv командой:" -ForegroundColor Yellow
    Write-Host "  python -m venv venv" -ForegroundColor White
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "  pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

# Активируем виртуальное окружение
Write-Host "Активирую виртуальное окружение..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Проверяем, что Python доступен
$pythonExe = ".\venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "ОШИБКА: Python в venv не найден!" -ForegroundColor Red
    exit 1
}

Write-Host "Виртуальное окружение активировано" -ForegroundColor Green
Write-Host ""
Write-Host "Запускаю сервер..." -ForegroundColor Yellow
Write-Host "Логи будут отображаться ниже. Для остановки нажмите Ctrl+C" -ForegroundColor Cyan
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Gray
Write-Host ""

# Запускаем сервер
& $pythonExe run_server.py

