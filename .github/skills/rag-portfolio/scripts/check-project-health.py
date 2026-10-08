#!/usr/bin/env python3
"""Quick, project-specific sanity check for the regulatory RAG portfolio."""

from __future__ import annotations

import os
from pathlib import Path

root = Path(__file__).resolve().parents[4]
raw_dir = root / 'data' / 'raw'

print('Project root:', root)
print('Data raw directory exists:', raw_dir.exists())
print('OpenRouter key configured:', bool(os.getenv('OPENROUTER_API_KEY')))
print('PDF count:', len(list(raw_dir.glob('*.pdf'))) if raw_dir.exists() else 0)
print('Project health check complete.')
