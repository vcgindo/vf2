FROM python:3.11.10-slim@sha256:840e180ebcc6e5c8efab209c43f5e40fd2af98cb49db5c7103c90539c56bb30e
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY release/requirements-mto.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock
COPY mto /app/
COPY release /app/release
RUN groupadd --gid 10002 vectorflow && useradd --uid 10002 --gid 10002 vectorflow \
    && mkdir -p /app/logs /app/Downloads /var/lib/vectorflow && chown 10002:10002 /app/logs /app/Downloads /var/lib/vectorflow
USER 10002:10002
ENTRYPOINT ["python", "-m", "release.service", "mto"]
