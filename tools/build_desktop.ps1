# Build UITOP Desktop as a Windows folder+exe under dist/UITOP/
# Requires: pip install -r requirements.txt -r requirements-desktop.txt

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Installing desktop build dependencies..."
python -m pip install -q -r requirements.txt -r requirements-desktop.txt

Write-Host "Building UITOP.exe (this may take a few minutes)..."
python -m PyInstaller --noconfirm --clean uitop-desktop.spec

$Out = Join-Path $Root "dist\UITOP\UITOP.exe"
if (Test-Path $Out) {
    Write-Host ""
    Write-Host "Build OK: $Out"
    Write-Host "Run UITOP.exe from dist\UITOP\ (keep the whole folder together)."
    Write-Host "Agents on other PCs should use http://<this-pc-lan-ip>:5500"
} else {
    Write-Error "Build finished but UITOP.exe was not found."
}
