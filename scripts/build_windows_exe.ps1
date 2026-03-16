param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/5] Installing runtime dependencies..."
& $PythonExe -m pip install -q -r requirements.txt

Write-Host "[2/5] Installing build dependencies..."
& $PythonExe -m pip install -q -r requirements-build.txt

Write-Host "[3/5] Cleaning old build artifacts..."
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }

Write-Host "[4/5] Building executable with PyInstaller..."
& $PythonExe -m PyInstaller --noconfirm --clean --log-level WARN silver_octo_umbrella.spec

Write-Host "[5/5] Creating downloadable zip..."
$zipPath = "dist\OSINTResearchPlatform-windows-x64.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path "dist\OSINTResearchPlatform.exe" -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host "Build complete."
Write-Host "Executable: dist\OSINTResearchPlatform.exe"
Write-Host "Portable zip: $zipPath"
