FROM python:3.11.10-slim@sha256:840e180ebcc6e5c8efab209c43f5e40fd2af98cb49db5c7103c90539c56bb30e
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY release/requirements-auth.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock
COPY user-service /app/
COPY release /app/release
RUN groupadd --gid 10001 vectorflow && useradd --uid 10001 --gid 10001 vectorflow \
    && mkdir -p /app/logs /var/lib/vectorflow && chown 10001:10001 /app/logs /var/lib/vectorflow
USER 10001:10001
ENTRYPOINT ["python", "-m", "release.service", "auth"]
