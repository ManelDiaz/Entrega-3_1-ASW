FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY consumer_mongodb.py .

CMD ["python", "consumer_mongodb.py"]
