# Start Hearth on Windows 10 / 11.
# Creates a virtual environment on first run, then keeps Hearth running: it restarts after an
# update from GitHub (exit code 3) and after any crash. Run it with start.cmd, or let
# scripts\install_service.ps1 start it hidden at sign-in.
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Test-Tls13($exe, [string[]]$pre = @()) {
    try {
        & $exe @pre -c "import ssl, sys; sys.exit(0 if ssl.HAS_TLSv1_3 and sys.version_info >= (3, 9) else 1)" 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    } catch { return $false }
}

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy) -or -not (Test-Tls13 $venvPy)) {
    if (Test-Path ".venv") { Remove-Item -Recurse -Force ".venv" }
    # Prefer the py launcher that python.org's installer adds, then python on PATH.
    $made = $false
    foreach ($candidate in @(@("py", "-3"), @("python"))) {
        $exe, $pre = $candidate[0], @($candidate | Select-Object -Skip 1)
        if ((Get-Command $exe -ErrorAction SilentlyContinue) -and (Test-Tls13 $exe $pre)) {
            Write-Host "Setting up Hearth's Python environment..."
            & $exe @pre -m venv .venv
            $made = $true
            break
        }
    }
    if (-not $made) {
        Write-Host "Hearth needs Python 3.10 or newer. Install it from https://www.python.org/downloads/windows/"
        Write-Host "(tick 'Add python.exe to PATH'), then run start.cmd again."
        exit 1
    }
}

function Sync-Requirements {
    $sum = (Get-FileHash -Algorithm SHA256 "requirements.txt").Hash
    $marker = ".venv\.requirements"
    if (-not (Test-Path $marker) -or (Get-Content $marker -Raw).Trim() -ne $sum) {
        & $venvPy -m pip --version 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { & $venvPy -m ensurepip | Out-Null }
        & $venvPy -m pip install -q --disable-pip-version-check -r requirements.txt
        Set-Content -Path $marker -Value $sum
    }
}

while ($true) {
    try { Sync-Requirements } catch { Write-Host "Couldn't install packages: $_" }
    if (-not (Test-Path "adblock\blocklist.txt")) { & $venvPy scripts\build_blocklist.py }
    & $venvPy -m hearth
    if ($LASTEXITCODE -eq 3) { Write-Host "Restarting with the new version..."; continue }
    Write-Host "Hearth stopped (exit code $LASTEXITCODE). Restarting in 5 seconds; close this window to stop it."
    Start-Sleep -Seconds 5
}
