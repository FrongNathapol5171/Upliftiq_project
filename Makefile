# UpliftIQ — common tasks
.PHONY: help setup pipeline pipeline-criteo api web test docker clean

DATASET ?= hillstrom
SEED ?= 42

help:
	@echo "setup            create venv + install backend deps"
	@echo "pipeline         run seeded train pipeline (DATASET=$(DATASET) SEED=$(SEED))"
	@echo "pipeline-criteo  run the scale benchmark on Criteo (subsampled)"
	@echo "api              start FastAPI on :8000"
	@echo "web              start Next.js simulator on :3000"
	@echo "test             run pytest"
	@echo "docker           docker compose up --build (one-command demo)"

setup:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

pipeline:
	. .venv/bin/activate && python -m pipeline.run --dataset $(DATASET) --seed $(SEED)

pipeline-criteo:
	. .venv/bin/activate && python -m pipeline.run --dataset criteo --seed $(SEED)

api:
	. .venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

web:
	cd web && npm install && npm run dev

test:
	. .venv/bin/activate && python -m pytest tests/ -q

docker:
	docker compose up --build

clean:
	rm -rf models/*/ scores/*.parquet reports/*/ web/.next web/out
