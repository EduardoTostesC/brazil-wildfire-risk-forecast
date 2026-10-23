# run_pipeline.ps1 - Pipeline execution script for Windows PowerShell
param (
    [Parameter(Mandatory=$false)]
    [ValidateSet("all", "data", "features", "train", "explain", "test", "api", "app", "clean")]
    [string]$Task = "all"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

function Invoke-Python {
    & python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE"
    }
}

Push-Location -LiteralPath $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " brazil-wildfire-risk-forecast - PowerShell Pipeline Tool" -ForegroundColor Cyan
Write-Host " Task: $Task" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

try { switch ($Task) {
    "data" {
        Write-Host "Downloading fire hotspot data (INPE)..." -ForegroundColor Yellow
        Invoke-Python -m src.data.download_fire
        Write-Host "Downloading climate data (NASA POWER)..." -ForegroundColor Yellow
        Invoke-Python -m src.data.download_climate
        Write-Host "Building grid and assembling dataset..." -ForegroundColor Yellow
        Invoke-Python -m src.data.build_grid
        Invoke-Python -m src.data.process_data
    }
    "features" {
        Write-Host "Engineering features..." -ForegroundColor Yellow
        Invoke-Python -m src.features.build_features
    }
    "train" {
        Write-Host "Training models..." -ForegroundColor Yellow
        Invoke-Python -m src.models.train
    }
    "explain" {
        Write-Host "Generating SHAP explainability plots..." -ForegroundColor Yellow
        Invoke-Python -m src.models.explain
    }
    "test" {
        Write-Host "Running pytest test suite..." -ForegroundColor Yellow
        Invoke-Python -m pytest tests/ -v
    }
    "api" {
        Write-Host "Starting FastAPI server on http://localhost:8000..." -ForegroundColor Green
        Invoke-Python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
    }
    "app" {
        Write-Host "Starting Streamlit dashboard on http://localhost:8501..." -ForegroundColor Green
        Invoke-Python -m streamlit run app/streamlit_app.py
    }
    "clean" {
        Write-Host "Cleaning generated data and models..." -ForegroundColor Red
        throw "Automatic deletion disabled: preserve raw data and versioned scientific artifacts. Review explicit paths before any manual cleanup."
    }
    "all" {
        Write-Host "Step 1: Processing raw data..." -ForegroundColor Yellow
        Invoke-Python -m src.data.download_fire
        Invoke-Python -m src.data.download_climate
        Invoke-Python -m src.data.build_grid
        Invoke-Python -m src.data.process_data
        Write-Host "Step 2: Building features..." -ForegroundColor Yellow
        Invoke-Python -m src.features.build_features
        Write-Host "Step 3: Training models with spatial block CV & calibration..." -ForegroundColor Yellow
        Invoke-Python -m src.models.train
        Write-Host "Step 4: Generating SHAP explanations..." -ForegroundColor Yellow
        Invoke-Python -m src.models.explain
        Write-Host "Step 5: Running tests..." -ForegroundColor Yellow
        Invoke-Python -m src.models.research
        Invoke-Python -m src.models.train_lstm
        Invoke-Python -m src.monitoring.drift_detector
        Invoke-Python -m src.data.build_sample
        Invoke-Python -m src.data.manifest --generate
        Invoke-Python -m src.data.manifest --verify
        Invoke-Python -m src.reporting.generate_readme_metrics
        Invoke-Python -m src.reporting.generate_research_tables
        Invoke-Python -m pytest tests/ -v
        Write-Host "Pipeline execution finished successfully!" -ForegroundColor Green
    }
}
} finally { Pop-Location }

