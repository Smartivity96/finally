# Start FinAlly in Docker. Usage: scripts\start_windows.ps1 [-Build] [-NoOpen]
param(
    [switch]$Build,
    [switch]$NoOpen
)
$ErrorActionPreference = "Stop"

$Image = "finally"
$Container = "finally"
$Volume = "finally-data"
$Port = if ($env:PORT) { $env:PORT } else { 8000 }
$Url = "http://localhost:$Port"

Set-Location (Join-Path $PSScriptRoot "..")

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker is not running. Start Docker and try again."
    exit 1
}

docker image inspect $Image *> $null
if ($Build -or $LASTEXITCODE -ne 0) {
    Write-Host "Building image '$Image'..."
    docker build -t $Image .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# Replace any existing container (running or stopped) so the script is idempotent
docker container inspect $Container *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Removing existing container '$Container'..."
    docker rm -f $Container *> $null
}

if (Test-Path ".env") {
    $EnvArgs = @("--env-file", ".env")
} else {
    Write-Warning "No .env file found; running with LLM_MOCK=true (see .env.example)."
    $EnvArgs = @("-e", "LLM_MOCK=true")
}

docker run -d --name $Container -v "${Volume}:/app/db" -p "${Port}:8000" @EnvArgs $Image | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "FinAlly is running at $Url"

if (-not $NoOpen) {
    Start-Process $Url
}
