FROM python:3.11.10-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY mto/requirements.container.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY mto /app
COPY infrastructure/docker/mto-entrypoint.sh /usr/local/bin/mto-entrypoint
RUN sed -i 's/\r$//' /usr/local/bin/mto-entrypoint && chmod +x /usr/local/bin/mto-entrypoint && \
    groupadd --gid 10002 vectorflow && useradd --uid 10002 --gid 10002 --home-dir /app vectorflow && \
    mkdir -p /app/logs && chown -R 10002:10002 /app
USER 10002:10002
EXPOSE 10015
ENTRYPOINT ["mto-entrypoint"]
