FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=America/Caracas
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CONFIG_PATH=/app/config.yaml
ENV TIMEZONE=America/Caracas
ENV TARGET_HOUR=9
ENV TARGET_MINUTE=0
ENV CHECK_INTERVAL=30

CMD ["python", "scheduler.py"]
