FROM python:3.11-slim

WORKDIR /app

# System deps for TensorFlow
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/ml_service/

# Create model directory
RUN mkdir -p /app/models/two_tower /app/models/reranker

ENV PYTHONPATH=/app
ENV ML_MODEL_PATH=/app/models
ENV ML_HOST=0.0.0.0
ENV ML_PORT=8001

EXPOSE 8001

CMD ["uvicorn", "ml_service.app:app", "--host", "0.0.0.0", "--port", "8001"]
