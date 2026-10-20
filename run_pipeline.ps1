# run_pipeline.ps1 - Pipeline execution script for Windows PowerShell
param (
    [Parameter(Mandatory=$false)]
    [ValidateSet("all", "data", "features", "train", "explain", "test", "api", "app", "clean")]
    [string]$Task = "all"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " brazil-wildfire-risk-forecast - PowerShell Pipeline Tool" -ForegroundColor Cyan
Write-Host " Task: $Task" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

switch ($Task) {
    "data" {
        Write-Host "Downloading fire hotspot data (INPE)..." -ForegroundColor Yellow
        python -m src.data.download_fire
        Write-Host "Downloading climate data (NASA POWER)..." -ForegroundColor Yellow
        python -m src.data.download_climate
        Write-Host "Building grid and assembling dataset..." -ForegroundColor Yellow
        python -m src.data.build_grid
        python -m src.data.process_data
    }
    "features" {
        Write-Host "Engineering features..." -ForegroundColor Yellow
        python -m src.features.build_features
    }
    "train" {
        Write-Host "Training models..." -ForegroundColor Yellow
        python -m src.models.train
    }
    "explain" {
        Write-Host "Generating SHAP explainability plots..." -ForegroundColor Yellow
        python -m src.models.explain
    }
    "test" {
        Write-Host "Running pytest test suite..." -ForegroundColor Yellow
        pytest tests/ -v
    }
    "api" {
        Write-Host "Starting FastAPI server on http://localhost:8000..." -ForegroundColor Green
        uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
    }
    "app" {
        Write-Host "Starting Streamlit dashboard on http://localhost:8501..." -ForegroundColor Green
        streamlit run app/streamlit_app.py
    }
    "clean" {
        Write-Host "Cleaning generated data and models..." -ForegroundColor Red
        Remove-Item -Path "$ProjectRoot\data\raw\*" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -Path "$ProjectRoot\data\processed\*" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -Path "$ProjectRoot\models\*.joblib" -Force -ErrorAction SilentlyContinue
        Remove-Item -Path "$ProjectRoot\reports\figures\*.png" -Force -ErrorAction SilentlyContinue
        Write-Host "Clean complete." -ForegroundColor Green
    }
    "all" {
        Write-Host "Step 1: Processing raw data..." -ForegroundColor Yellow
        python -m src.data.build_grid
        python -m src.data.process_data
        Write-Host "Step 2: Building features..." -ForegroundColor Yellow
        python -m src.features.build_features
        Write-Host "Step 3: Training models with spatial block CV & calibration..." -ForegroundColor Yellow
        python -m src.models.train
        Write-Host "Step 4: Generating SHAP explanations..." -ForegroundColor Yellow
        python -m src.models.explain
        Write-Host "Step 5: Running tests..." -ForegroundColor Yellow
        pytest tests/ -v
        Write-Host "Pipeline execution finished successfully!" -ForegroundColor Green
    }
}

