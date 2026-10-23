.PHONY: install data features train research explain drift dvc-repro mlflow-ui lint api app test all clean

install:
	python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
	python -m pip install --require-hashes -r requirements.lock

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
	mlflow ui

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
	python -m src.reporting.generate_readme_metrics
	python -m src.reporting.generate_research_tables

all: data features train explain drift research

clean:
	@echo "Automatic deletion disabled: raw data and versioned artifacts must be preserved. Remove only explicitly reviewed generated files."
