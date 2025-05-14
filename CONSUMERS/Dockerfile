FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY consumer_storage.py .
COPY consumer_alert.py .
COPY consumer_stats.py .

CMD ["python", "consumer_storage.py"]
# Para usar otro consumer, cambia el CMD por:
# CMD ["python", "consumer_alert.py"]
# o
# CMD ["python", "consumer_stats.py"]