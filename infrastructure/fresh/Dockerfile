FROM postgres:16.15-bookworm AS pgtools
FROM python:3.11.14-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 liblz4-1 libzstd1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=pgtools /usr/lib/postgresql/16/bin/pg_dump /usr/local/bin/pg_dump
COPY --from=pgtools /usr/lib/postgresql/16/bin/pg_restore /usr/local/bin/pg_restore
COPY --from=pgtools /usr/lib/x86_64-linux-gnu/libpq.so.5* /usr/lib/x86_64-linux-gnu/
COPY manage.py /app/
COPY vectorflow /app/vectorflow
COPY mta /app/mta
COPY parity /app/parity
COPY tests /app/tests
COPY baseline /app/baseline
RUN groupadd --gid 10001 vectorflow && useradd --uid 10001 --gid vectorflow vectorflow
USER 10001:10001
CMD ["gunicorn", "vectorflow.wsgi:application", "--preload", "--bind", "0.0.0.0:8000", "--workers", "2"]
