# Novel Reader - Windows Deployment Script
# Support: Docker Desktop or WSL2

param(
    [switch]$UseDocker,
    [switch]$UseWSL,
    [switch]$SkipInstall,
    [switch]$SkipDocker,
    [string]$PythonVersion = "3.11"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

function Write-Step {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error-Message {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

Write-Host @"
╔══════════════════════════════════════════════════════════════╗
║         Novel Reader - Windows Deployment Script v1.0       ║
║  Support: Docker Desktop / WSL2 / Native Python            ║
╚══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Magenta

$isWSL = $false
if (Test-Path "/proc/version") {
    $wslCheck = Get-Content "/proc/version" -ErrorAction SilentlyContinue
    if ($wslCheck -match "microsoft|WSL") {
        $isWSL = $true
    }
}

if ($isWSL) {
    Write-Host "Detected WSL2 environment, using Linux deployment" -ForegroundColor Green
    Write-Step "Calling Linux deployment script"
    bash "$ProjectRoot/deploy.sh"
    exit $LASTEXITCODE
}

$useDocker = $UseDocker
$skipDocker = $SkipDocker

if (-not $useDocker -and -not $skipDocker) {
    Write-Step "Detecting runtime environment"
    $dockerAvailable = Test-Command "docker"
    if ($dockerAvailable) {
        Write-Host "Docker Desktop detected. Use Docker? [Y/n]" -ForegroundColor Yellow
        $response = Read-Host " "
        if ($response -ne "n" -and $response -ne "N") {
            $useDocker = $true
        }
    }
}

if ($useDocker) {
    Write-Step "Using Docker Desktop deployment"
    if (-not (Test-Command "docker")) {
        Write-Error-Message "Docker Desktop not installed"
        exit 1
    }
    if (-not (Test-Command "docker-compose") -and -not (Test-Command "docker")) {
        Write-Error-Message "Docker Compose not installed"
        exit 1
    }

    Write-Host "Building Docker image..."
    docker-compose build

    Write-Host "`nStarting services..."
    docker-compose up -d

    Write-Host "`nWaiting for services..."
    Start-Sleep -Seconds 10

    Write-Host "`nService status:"
    docker-compose ps

    Write-Success "Deployment complete!"
    Write-Host "`nAccess URLs:"
    Write-Host "  Frontend: http://localhost:80" -ForegroundColor Cyan
    Write-Host "  Backend: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
} else {
    Write-Step "Native Python deployment"

    if (-not $SkipInstall) {
        Write-Host "Checking Python version..."
        if (Test-Command "python") {
            $pythonVersion = python --version 2>&1
            Write-Host "Current Python: $pythonVersion" -ForegroundColor Green
        } elseif (Test-Command "python3") {
            $pythonVersion = python3 --version 2>&1
            Write-Host "Current Python: $pythonVersion" -ForegroundColor Green
        } else {
            Write-Error-Message "Python not installed"
            exit 1
        }

        Write-Host "`nCreating virtual environment..."
        if (Test-Path "$ProjectRoot\venv") {
            Write-Warning "Virtual environment exists, skipping"
        } else {
            python -m venv "$ProjectRoot\venv"
            Write-Success "Virtual environment created"
        }

        Write-Host "`nActivating virtual environment..."
        & "$ProjectRoot\venv\Scripts\Activate.ps1"

        Write-Host "`nInstalling dependencies (using pre-built wheels)..."
        $env:PYTHONPATH = "$ProjectRoot\backend"
        pip install --upgrade pip
        pip install wheel
        pip install -r "$ProjectRoot\requirements.txt" --only-binary=:all:

        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Pre-built package installation failed, trying mixed install..."
            pip install -r "$ProjectRoot\requirements.txt"
        }

        Write-Success "Dependencies installed"
    }

    Write-Step "Initializing data directories"
    $dataDirs = @("data", "data\books", "data\index", "data\static", "data\logs", "data\cache")
    foreach ($dir in $dataDirs) {
        $dirPath = Join-Path $ProjectRoot $dir
        if (-not (Test-Path $dirPath)) {
            New-Item -ItemType Directory -Path $dirPath -Force | Out-Null
        }
    }
    Write-Success "Data directories initialized"

    Write-Step "Configuring environment variables"
    $envFile = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $envFile)) {
        Copy-Item (Join-Path $ProjectRoot ".env.example") $envFile
        Write-Success ".env file created, please set SECRET_KEY"
    } else {
        Write-Host ".env file exists"
    }

    Write-Step "Starting backend service"
    $backendDir = Join-Path $ProjectRoot "backend"
    Set-Location $backendDir

    $env:PYTHONPATH = $backendDir
    $env:DATA_DIR = Join-Path $ProjectRoot "data"
    $env:BOOKS_DIR = Join-Path $ProjectRoot "data\books"
    $env:LOG_LEVEL = "INFO"

    Write-Host "`nStart command: python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

    python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

    Write-Success "Service stopped"
}

Write-Host "`nDeployment script completed!" -ForegroundColor Green
