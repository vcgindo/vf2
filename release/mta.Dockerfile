FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY release/requirements-mta.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock
COPY manage.py /app/
COPY mta /app/mta
COPY vectorflow /app/vectorflow
COPY baseline /app/baseline
COPY parity /app/parity
COPY release /app/release
RUN groupadd --gid 10001 vectorflow && useradd --uid 10001 --gid 10001 vectorflow \
    && mkdir -p /var/lib/vectorflow && chown 10001:10001 /var/lib/vectorflow
USER 10001:10001
ENTRYPOINT ["python", "-m", "release.service", "mta"]
