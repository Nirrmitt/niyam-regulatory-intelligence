# Regulatory Documents Dataset

This directory stores downloaded RBI / SEBI regulatory PDFs.

## Structure

- `raw/` - Downloaded PDF files (git-ignored)
- `sources.json` - List of source URLs and filenames to be filled manually

## How to Add Documents

1. Edit `sources.json` with document metadata (name, url, filename).
2. Run: `python scripts/download_docs.py`
3. Ingest via: `docker compose exec api python -m app.ingestion.cli --reset`
