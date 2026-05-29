FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip for better dependency resolution + speed
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY app/requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 -r requirements.txt

# Copy the full project (api, agents, config, graph, worker, rag, observability)
COPY app/ .

CMD ["python", "run.py"]
