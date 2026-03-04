param(
    [string]$Python = "",
    [switch]$SkipTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-PythonCommand {
    param([string]$Preferred)

    if ($Preferred) {
        if (Test-Path $Preferred) {
            return @{ Cmd = (Resolve-Path $Preferred).Path; Args = @() }
        }
        return @{ Cmd = $Preferred; Args = @() }
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -c "import sys" *> $null
        if ($LASTEXITCODE -eq 0) {
            return @{ Cmd = "py"; Args = @("-3.12") }
        }

        & py -3 -c "import sys" *> $null
        if ($LASTEXITCODE -eq 0) {
            return @{ Cmd = "py"; Args = @("-3") }
        }
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{ Cmd = "python"; Args = @() }
    }

    throw "Python not found. Install Python 3.12+ or pass -Python <path>."
}

function Assert-PythonVersion {
    param(
        [string]$Cmd,
        [string[]]$Args
    )

    $version = & $Cmd @Args -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
    & $Cmd @Args -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)"
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.12+ required. Found $version"
    }

    return $version
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "=== AI Groove Writer Service Setup (PowerShell) ==="

$pythonRef = Resolve-PythonCommand -Preferred $Python
$pythonCmd = [string]$pythonRef.Cmd
$pythonArgs = [string[]]$pythonRef.Args

$resolvedVersion = Assert-PythonVersion -Cmd $pythonCmd -Args $pythonArgs
Write-Host "Using Python $resolvedVersion via: $pythonCmd $($pythonArgs -join ' ')"

$venvDir = Join-Path $scriptDir ".venv"
if (-not (Test-Path $venvDir)) {
    Write-Host "Creating virtual environment..."
    & $pythonCmd @pythonArgs -m venv .venv
} else {
    Write-Host "Virtual environment already exists at .venv"
}

$venvPython = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Could not find venv python at $venvPython"
}

Write-Host "Upgrading pip..."
& $venvPython -m pip install --upgrade pip

Write-Host "Installing dependencies..."
& $venvPython -m pip install -r requirements.txt

if ((-not (Test-Path ".env")) -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

if (-not $SkipTests) {
    Write-Host "Running tests..."
    & $venvPython -m pytest tests -v
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Start service with:"
Write-Host "  .venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8787"
