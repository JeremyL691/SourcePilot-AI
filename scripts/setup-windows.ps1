$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DesktopRoot = Join-Path $ProjectRoot "desktop"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Resolve-Python {
    $commands = @(
        @{ Command = "py"; Args = @("-3.11", "-c", "import sys; print(sys.executable)") },
        @{ Command = "python"; Args = @("-c", "import sys; print(sys.executable)") }
    )

    foreach ($candidate in $commands) {
        $command = Get-Command $candidate.Command -ErrorAction SilentlyContinue
        if (-not $command) {
            continue
        }

        try {
            $output = & $candidate.Command @($candidate.Args) 2>$null
        } catch {
            continue
        }
        if ($LASTEXITCODE -ne 0 -or -not $output) {
            continue
        }

        $python = ($output | Select-Object -Last 1).Trim()
        & $python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
        if ($LASTEXITCODE -eq 0) {
            return $python
        }
    }

    throw "Python 3.11 or newer was not found. Install it from https://www.python.org/downloads/windows/ and check 'Add python.exe to PATH'."
}

function Require-Command($Name, $InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name was not found. $InstallHint"
    }
}

Set-Location $ProjectRoot

Write-Step "Checking Windows prerequisites"
Require-Command "npm.cmd" "Install Node.js LTS from https://nodejs.org/"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { Resolve-Python }
Write-Host "Using Python: $Python"

if (-not (Test-Path $VenvPython)) {
    Write-Step "Creating Python virtual environment"
    & $Python -m venv ".venv"
}

Write-Step "Installing Python dependencies"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e "."

Write-Step "Installing desktop dependencies"
Set-Location $DesktopRoot
& npm.cmd install

Write-Step "Preparing Electron"
& npm.cmd run ensure-electron

Write-Step "Running desktop smoke check"
& npm.cmd run smoke

Write-Host ""
Write-Host "SourceHero AI setup completed. Start it with:" -ForegroundColor Green
Write-Host "cd `"$DesktopRoot`""
Write-Host "npm.cmd run dev"
