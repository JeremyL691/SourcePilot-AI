# Build an embedded Python runtime for the Electron desktop bundle on Windows.
# Downloads python-build-standalone and installs SourceHero deps into it.
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DesktopRoot = Join-Path $ProjectRoot "desktop"
$RuntimeDir  = Join-Path $DesktopRoot "runtime\python-win"

$PbsTag     = "20251002"
$PbsVersion = "3.11.13"
$Arch       = if ([Environment]::Is64BitOperatingSystem) { "x86_64" } else { "i686" }
$PbsUrl     = "https://github.com/astral-sh/python-build-standalone/releases/download/$PbsTag/cpython-$PbsVersion+$PbsTag-$Arch-pc-windows-msvc-install_only.tar.gz"

$WorkDir = New-Item -ItemType Directory -Path (Join-Path $env:TEMP "sourcehero-runtime-$([guid]::NewGuid())") -Force
try {
    Write-Host "==> Downloading python-build-standalone ($PbsVersion, win-$Arch)" -ForegroundColor Cyan
    $archive = Join-Path $WorkDir "python.tar.gz"
    Invoke-WebRequest -Uri $PbsUrl -OutFile $archive

    Write-Host "==> Extracting runtime"
    tar -xzf $archive -C $WorkDir.FullName

    if (Test-Path $RuntimeDir) { Remove-Item -Recurse -Force $RuntimeDir }
    New-Item -ItemType Directory -Path $RuntimeDir | Out-Null
    Copy-Item (Join-Path $WorkDir.FullName "python\*") $RuntimeDir -Recurse

    $Py = Join-Path $RuntimeDir "python.exe"
    if (-not (Test-Path $Py)) { throw "Embedded python.exe not found at $Py" }

    Write-Host "==> Installing SourceHero dependencies into embedded runtime (PYTHONPATH wires app/ at runtime)"
    & $Py -m pip install --upgrade pip
    & $Py -m pip install `
      "beautifulsoup4>=4.12.3" "fastapi>=0.111.0" "feedparser>=6.0.11" "pandas>=2.2.2" `
      "pydantic>=2.7.0" "openai>=1.0.0" "pypdf>=4.2.0" "python-dotenv>=1.0.1" `
      "python-multipart>=0.0.9" "requests>=2.32.0" "sqlalchemy>=2.0.30" `
      "streamlit>=1.35.0" "uvicorn>=0.30.0" "platformdirs>=4.2.0"

    Write-Host ""
    Write-Host "✅ Embedded runtime ready at: $RuntimeDir" -ForegroundColor Green
    & $Py --version
}
finally {
    Remove-Item -Recurse -Force $WorkDir
}
