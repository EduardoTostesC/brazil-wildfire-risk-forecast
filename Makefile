.PHONY: install data features train evaluate explain drift dvc-repro mlflow-ui lint api app test all clean

install:
	pip install -r requirements.txt

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

all: data features train explain drift

clean:
	rm -rf data/raw/ data/processed/ models/*.pkl models/*.joblib reports/figures/*.png
