FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

ENV DB_PATH=/data/sent.db \
    PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
