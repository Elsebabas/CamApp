$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = Join-Path $projectRoot "venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "No se encontró venv. Crea el entorno e instala requirements-dev.txt."
}

Write-Host "Ejecutando pruebas..."
& $python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Las pruebas fallaron." }

Write-Host "Compilando CamApp.exe..."
& $python -m PyInstaller --noconfirm --clean `
    --workpath ".installer_work" `
    --distpath "installer_artifacts" `
    CamApp.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller no pudo compilar CamApp." }

$isccCandidates = @(
    (Join-Path $projectRoot ".tools\InnoSetup\ISCC.exe"),
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "CamApp.exe fue generado, pero falta Inno Setup 6 para crear el instalador."
}

Write-Host "Creando instalador..."
& $iscc "installer.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup no pudo crear el instalador." }

Write-Host "Proceso completado: installer_artifacts\CamApp-Setup-1.0.0.exe"
