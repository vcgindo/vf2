FROM postgres:16.15-alpine
COPY infrastructure/docker/postgres-init.sh /docker-entrypoint-initdb.d/10-create-vectorflow-databases.sh
RUN sed -i 's/\r$//' /docker-entrypoint-initdb.d/10-create-vectorflow-databases.sh \
    && chmod 0555 /docker-entrypoint-initdb.d/10-create-vectorflow-databases.sh
