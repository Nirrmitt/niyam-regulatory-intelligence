up:
docker compose up -d --build

ingest:
python -m scripts.ingest --strategy all

test:
pytest tests/

health:
docker compose logs -f api | grep health