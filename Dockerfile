FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/root/.cache/huggingface

RUN pip install --no-cache-dir ruff

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embeddings to avoid cold-start latency during runtime
RUN python -c "from sentence_transformers import SentenceTransformer; \
    st = SentenceTransformer('BAAI/bge-small-en-v1.5'); \
    print('Embedding model loaded successfully')" 2>&1 | tee /tmp/model_status.log

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]