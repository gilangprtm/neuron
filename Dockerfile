FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY main.py .

# Data directory for graph.db, fastembed cache, vault mirror
RUN mkdir -p /app/data

EXPOSE 9120

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9120"]
