FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаем директорию для данных
RUN mkdir -p /app/data

# Том для хранения данных
VOLUME ["/app/data"]

CMD ["python", "main.py"]
