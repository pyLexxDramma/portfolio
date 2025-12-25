# Скрипт для просмотра логов сервера в реальном времени
$logFile = "logs\parser.log"

if (-not (Test-Path $logFile)) {
    Write-Host "Файл логов не найден: $logFile" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== ПРОСМОТР ЛОГОВ СЕРВЕРА ===" -ForegroundColor Green
Write-Host "Файл: $logFile" -ForegroundColor Cyan
Write-Host "Для выхода нажмите Ctrl+C`n" -ForegroundColor Yellow

# Показываем последние 50 строк
Get-Content $logFile -Tail 50

# Мониторим файл в реальном времени
Get-Content $logFile -Wait -Tail 0

