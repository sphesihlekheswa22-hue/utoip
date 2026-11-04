# Build standalone UITOP Agent .exe (no Python needed on other PCs)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Installing build dependencies..."
python -m pip install -q -r requirements.txt pyinstaller

Write-Host "Building UITOP-Agent.exe..."
python -m PyInstaller --noconfirm --clean uitop-agent.spec

$Out = Join-Path $Root "dist\UITOP-Agent.exe"
if (Test-Path $Out) {
    Write-Host ""
    Write-Host "Build OK: $Out"
    Write-Host "Users download it from Computers -> Add device in UITOP."
} else {
    Write-Error "Build finished but UITOP-Agent.exe was not found."
}
