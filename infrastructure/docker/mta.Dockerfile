FROM python:3.11.14-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY mta/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
RUN groupadd --gid 10001 vectorflow \
    && useradd --uid 10001 --gid vectorflow --create-home --home-dir /home/vectorflow vectorflow

FROM base AS parity-test
COPY --chown=vectorflow:vectorflow mta /app/mta
COPY --chown=vectorflow:vectorflow parity /app/parity
USER vectorflow
WORKDIR /app/mta

FROM base AS runtime
COPY --chown=vectorflow:vectorflow mta /app/mta
COPY --chown=vectorflow:vectorflow infrastructure/docker/mta-entrypoint.sh /usr/local/bin/mta-entrypoint
RUN sed -i 's/\r$//' /usr/local/bin/mta-entrypoint && chmod 0555 /usr/local/bin/mta-entrypoint
USER vectorflow
WORKDIR /app/mta
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('MTA_PORT', '8000') + '/readyz', timeout=3)"
ENTRYPOINT ["/usr/local/bin/mta-entrypoint"]
