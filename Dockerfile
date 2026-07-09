FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CONFIG_PATH=/app/config.yaml
ENV TZ=America/Caracas
ENV TARGET_HOUR=13
ENV TARGET_MINUTE=30
ENV CHECK_INTERVAL=30
ENV HEALTH_PORT=8080
ENV RUN_ON_STARTUP=true

CMD ["python", "scheduler.py"]
