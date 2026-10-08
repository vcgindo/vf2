FROM postgres:16.15-bookworm AS pgtools
FROM freshvcf-cohort2:20261008-final001 AS accepted_mta
FROM freshvcf-daily3006-user-service:captcha-001

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app

COPY --from=pgtools /usr/lib/postgresql/16/bin/pg_dump /usr/local/bin/pg_dump
COPY --from=pgtools /usr/lib/postgresql/16/bin/pg_restore /usr/local/bin/pg_restore
COPY --from=pgtools /usr/lib/x86_64-linux-gnu/libpq.so.5* /usr/lib/x86_64-linux-gnu/
COPY --from=accepted_mta /usr/local/lib/python3.11/site-packages/psycopg /usr/local/lib/python3.11/site-packages/psycopg
COPY --from=accepted_mta /usr/local/lib/python3.11/site-packages/psycopg_binary /usr/local/lib/python3.11/site-packages/psycopg_binary
COPY --from=accepted_mta /usr/local/lib/python3.11/site-packages/psycopg_binary.libs /usr/local/lib/python3.11/site-packages/psycopg_binary.libs
COPY --from=accepted_mta /usr/local/lib/python3.11/site-packages/psycopg-3.3.6.dist-info /usr/local/lib/python3.11/site-packages/psycopg-3.3.6.dist-info
COPY --from=accepted_mta /usr/local/lib/python3.11/site-packages/psycopg_binary-3.3.6.dist-info /usr/local/lib/python3.11/site-packages/psycopg_binary-3.3.6.dist-info
COPY vectorflow /app/vectorflow
COPY mta /app/mta
COPY parity /app/parity
COPY baseline /app/baseline
COPY tools/cohort3_*.py /app/tools/
COPY user-service/api_gateway /app/api_gateway

# The immutable user image already contains Django, DRF, SimpleJWT, requests,
# PyCryptodome, psycopg2 and every retained authentication dependency. No network
# install or alternate migration package is introduced by this proof image.
ENTRYPOINT ["python"]
CMD ["-m", "tools.cohort3_identity_bootstrap", "--help"]
