# StudioCRM Multi-Account Telegram Mini App - Development Runner
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Starting StudioCRM Telegram Development Environment    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check .env file
if (-not (Test-Path ".env")) {
    if (Test-Path "backend\.env.example") {
        Write-Host "No .env found. Copying backend\.env.example to .env..." -ForegroundColor Yellow
        Copy-Item "backend\.env.example" ".env"
    }
}

# 2. Start Frontend Preview Server if node.exe is present
$nodeExe = "$env:TEMP\node.exe"
if (Test-Path $nodeExe) {
    Write-Host "Launching Telegram Mini App Frontend on http://localhost:3000..." -ForegroundColor Green
    Start-Process $nodeExe -ArgumentList "frontend\serve.cjs" -WindowStyle Hidden
    Start-Process "http://localhost:3000/preview.html"
} else {
    Write-Host "Opening standalone preview in default browser..." -ForegroundColor Green
    Start-Process "frontend\preview.html"
}

# 3. Check Docker Compose availability
if (Get-Command "docker-compose" -ErrorAction SilentlyContinue) {
    Write-Host "Starting Docker cluster (Postgres, Redis, Backend, Bot, Nginx)..." -ForegroundColor Green
    docker-compose up --build
} else {
    Write-Host "Docker is not detected in PATH." -ForegroundColor Yellow
    Write-Host "Frontend is running live at http://localhost:3000/preview.html" -ForegroundColor Green
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
