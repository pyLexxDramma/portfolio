# Скрипт для запуска сервера с выводом логов в консоль
$ErrorActionPreference = "Stop"

Write-Host "=== Запуск сервера Unified Parser ===" -ForegroundColor Green
Write-Host ""

# Переходим в директорию проекта
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Пытаемся найти Python
$pythonCmd = $null

# Проверяем различные варианты
$pythonVariants = @("python", "python3", "py", "python.exe")

foreach ($variant in $pythonVariants) {
    try {
        $result = Get-Command $variant -ErrorAction SilentlyContinue
        if ($result) {
            $pythonCmd = $variant
            Write-Host "Найден Python: $($result.Source)" -ForegroundColor Green
            break
        }
    } catch {
        continue
    }
}

# Если не нашли, пробуем найти в стандартных местах
if (-not $pythonCmd) {
    $pythonPaths = @(
        "$env:LOCALAPPDATA\Programs\Python",
        "C:\Python*",
        "C:\Program Files\Python*",
        "C:\Program Files (x86)\Python*"
    )
    
    foreach ($pathPattern in $pythonPaths) {
        $found = Get-ChildItem -Path $pathPattern -ErrorAction SilentlyContinue -Recurse -Filter "python.exe" | Select-Object -First 1
        if ($found) {
            $pythonCmd = $found.FullName
            Write-Host "Найден Python: $pythonCmd" -ForegroundColor Green
            break
        }
    }
}

if (-not $pythonCmd) {
    Write-Host "ОШИБКА: Python не найден!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Пожалуйста:" -ForegroundColor Yellow
    Write-Host "1. Установите Python или добавьте его в PATH" -ForegroundColor Yellow
    Write-Host "2. Или укажите полный путь к python.exe" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Для просмотра логов используйте:" -ForegroundColor Cyan
    Write-Host "  Get-Content logs\parser.log -Wait -Tail 0" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "Запускаю сервер..." -ForegroundColor Yellow
Write-Host "Логи будут отображаться ниже. Для остановки нажмите Ctrl+C" -ForegroundColor Cyan
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Gray
Write-Host ""

# Запускаем сервер
& $pythonCmd run_server.py

