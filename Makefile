.PHONY: install data features train research finalize explain drift dvc-repro mlflow-ui lint api app test all clean
.NOTPARALLEL: all

install:
	python -m pip install --require-hashes --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-cpu.lock

data:
	python -m src.data.download_fire
	python -m src.data.download_climate
	python -m src.data.build_grid
	python -m src.data.process_data

features:
	python -m src.features.build_features

train:
	python -m src.models.train

explain:
	python -m src.models.explain

drift:
	python -m src.monitoring.drift_detector

dvc-repro:
	dvc repro

mlflow-ui:
	python -m mlflow ui --backend-store-uri sqlite:///mlflow-audit.db

lint:
	ruff check .

api:
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

app:
	streamlit run app/streamlit_app.py

test:
	pytest tests/ -v

research:
	python -m src.models.research
	python -m src.models.train_lstm

finalize:
	python -m src.reporting.decision_diagnostics
	python -m src.reporting.plot_research
	python -m src.data.build_sample
	python -m src.data.manifest --generate
	python -m src.data.manifest --verify
	python -m src.reporting.generate_readme_metrics
	python -m src.reporting.generate_research_tables
	python -m src.models.artifacts
	python -m src.models.artifacts --verify

all: data features train explain drift research finalize test

clean:
	@echo "Automatic deletion disabled: raw data and versioned artifacts must be preserved. Remove only explicitly reviewed generated files."
