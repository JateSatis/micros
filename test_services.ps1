# PowerShell скрипт для проверки работоспособности всех сервисов

Write-Host "Проверка работоспособности микросервисов..." -ForegroundColor Cyan
Write-Host ""

$services = @(
    @{Name="Auth Service"; Url="http://localhost:8001/health"},
    @{Name="Profile Service"; Url="http://localhost:8002/health"},
    @{Name="Jobs Service"; Url="http://localhost:8003/health"},
    @{Name="Applications Service"; Url="http://localhost:8004/health"},
    @{Name="Reviews Service"; Url="http://localhost:8005/health"},
    @{Name="Mailing Service"; Url="http://localhost:8006/health"},
    @{Name="Verification Service"; Url="http://localhost:8007/health"},
    @{Name="Notifications Service"; Url="http://localhost:8008/health"}
)

foreach ($service in $services) {
    Write-Host -NoNewline "Проверка $($service.Name)... "
    try {
        $response = Invoke-WebRequest -Uri $service.Url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ OK" -ForegroundColor Green
        } else {
            Write-Host "✗ FAILED (Status: $($response.StatusCode))" -ForegroundColor Red
        }
    } catch {
        Write-Host "✗ FAILED" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Проверка завершена!" -ForegroundColor Cyan

