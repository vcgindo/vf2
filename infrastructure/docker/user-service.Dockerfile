FROM python:3.11.10-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY user-service/requirements.container.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY user-service /app
COPY infrastructure/docker/user-service-entrypoint.sh /usr/local/bin/user-service-entrypoint
COPY infrastructure/docker/user-service-key-init.py /usr/local/bin/user-service-key-init.py
RUN sed -i 's/\r$//' /usr/local/bin/user-service-entrypoint && chmod +x /usr/local/bin/user-service-entrypoint && \
    groupadd --gid 10001 vectorflow && useradd --uid 10001 --gid 10001 --home-dir /app vectorflow && \
    mkdir -p /app/logs && chown -R 10001:10001 /app
USER 10001:10001
EXPOSE 10016
ENTRYPOINT ["user-service-entrypoint"]
