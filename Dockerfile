FROM python:3.10-slim

WORKDIR /app

ARG BUILD_ENVIRONMENT=prod

ENV YOURVIBES_AI_CONFIG_FILE=$BUILD_ENVIRONMENT

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y ca-certificates

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache

COPY src /app/src
COPY config /app/config

CMD ["python", "src/main.py"]