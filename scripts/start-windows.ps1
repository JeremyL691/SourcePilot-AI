$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DesktopRoot = Join-Path $ProjectRoot "desktop"

Set-Location $DesktopRoot
& npm.cmd run dev
