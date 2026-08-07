# Single parametrized image for every AIRTR service (build ARG SERVICE selects one).
# Intentionally-vulnerable lab — never deploy to a real/untrusted network.
FROM python:3.11-slim
ARG SERVICE
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app \
    AIRTR_SEED_DIR=/app/seed-data SCOREBOARD_URL=http://scoreboard:9000
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common/ /app/common/
COPY seed-data/ /app/seed-data/
COPY services/${SERVICE}/ /app/service/
CMD ["python", "/app/service/app.py"]
