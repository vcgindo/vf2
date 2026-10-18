# DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d AS source-export
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/checkout
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY . /checkout/
RUN git config --global --add safe.directory /checkout && python -B /checkout/release/compose_build.py /checkout /build

FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d AS mta-dependencies
ENV PYTHONDONTWRITEBYTECODE=1
COPY --from=source-export /build/mta-context/application /candidate/
COPY --from=source-export /build/mta-context/tools /tools/
COPY --from=source-export /build/wheels /wheels/
COPY --from=source-export /build/identity.json /identity.json
RUN python -B -c "import json,subprocess; p=json.load(open('/identity.json')); subprocess.run(['python','-B','/tools/mta_packaging.py','--application','/candidate','--commit',p['source_commit'],'--native-sha256',p['native_sha256'],'--wheelhouse','/wheels'],check=True)" && python -B -m pip install --no-index --find-links=/wheels --no-deps --no-cache-dir --no-compile --prefix=/install -r /candidate/release/requirements-mta.lock

FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d AS mta
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
COPY --from=mta-dependencies /install/ /usr/local/
COPY --from=mta-dependencies /candidate/ /app/
COPY --from=source-export /build/identity.json /opt/vectorflow/release.json
COPY --from=source-export /build/export/release/image_entrypoint.py /opt/vectorflow/image_entrypoint.py
COPY --from=source-export /build/export/release/blank_database.py /operator/blank_database.py
COPY --from=source-export /build/export/release/grant_service.py /operator/grant_service.py
RUN groupadd --gid 10001 vectorflow && useradd --uid 10001 --gid 10001 vectorflow && mkdir -p /var/lib/vectorflow && chown 10001:10001 /var/lib/vectorflow
WORKDIR /app
USER 10001:10001
ENTRYPOINT ["python", "/opt/vectorflow/image_entrypoint.py"]
CMD ["python", "-m", "release.service", "mta"]

FROM python:3.11.10-slim@sha256:840e180ebcc6e5c8efab209c43f5e40fd2af98cb49db5c7103c90539c56bb30e AS auth
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY --from=source-export /build/export/release/requirements-auth.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock
COPY --from=source-export /build/export/user-service /app/
COPY --from=source-export /build/export/release /app/release/
COPY --from=source-export /build/identity.json /opt/vectorflow/release.json
RUN groupadd --gid 10001 vectorflow && useradd --uid 10001 --gid 10001 vectorflow && mkdir -p /app/logs /var/lib/vectorflow && chown 10001:10001 /app/logs /var/lib/vectorflow
USER 10001:10001
ENTRYPOINT ["python", "-m", "release.service", "auth"]

FROM python:3.11.10-slim@sha256:840e180ebcc6e5c8efab209c43f5e40fd2af98cb49db5c7103c90539c56bb30e AS mto
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY --from=source-export /build/export/release/requirements-mto.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock
COPY --from=source-export /build/export/mto /app/
COPY --from=source-export /build/export/release /app/release/
COPY --from=source-export /build/identity.json /opt/vectorflow/release.json
RUN groupadd --gid 10002 vectorflow && useradd --uid 10002 --gid 10002 vectorflow && mkdir -p /app/logs /app/Downloads /var/lib/vectorflow && chown 10002:10002 /app/logs /app/Downloads /var/lib/vectorflow
USER 10002:10002
ENTRYPOINT ["python", "-m", "release.service", "mto"]

FROM node:20.18-alpine@sha256:053c1d99e608fe9fa0db6821edd84276277c0a663cd181f4a3e59ee20f5f07ea AS frontend-build
WORKDIR /app
COPY --from=source-export /build/export/frontend/package.json /build/export/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY --from=source-export /build/export/frontend/ ./
ARG REACT_APP_API_HOST=/
ARG REACT_APP_VF_API_HOST_MTO=/api/mto
ARG REACT_APP_WS_API_HOST
ARG REACT_APP_SECRET_KEY
ARG REACT_APP_AG_GRID_LICENSE_KEY
ARG FRONTEND_BUILD_HEAP_MIB=4096
ENV REACT_APP_API_HOST=$REACT_APP_API_HOST REACT_APP_VF_API_HOST_MTO=$REACT_APP_VF_API_HOST_MTO REACT_APP_WS_API_HOST=$REACT_APP_WS_API_HOST REACT_APP_SECRET_KEY=$REACT_APP_SECRET_KEY REACT_APP_AG_GRID_LICENSE_KEY=$REACT_APP_AG_GRID_LICENSE_KEY REACT_APP_ENABLE_LOCAL_LOGIN=true REACT_APP_DEMO_MODE=false GENERATE_SOURCEMAP=false NODE_OPTIONS=--max-old-space-size=${FRONTEND_BUILD_HEAP_MIB} CI=false TSC_COMPILE_ON_ERROR=true
COPY --from=source-export /build/export/release/frontend-build.cjs /build-tools/frontend-build.cjs
RUN node /build-tools/frontend-build.cjs

FROM nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10 AS frontend
COPY --from=frontend-build /app/build /usr/share/nginx/html
COPY --from=source-export /build/export/release/nginx.template /etc/nginx/templates/vectorflow.template
COPY --from=source-export /build/export/release/frontend-entrypoint.sh /usr/local/bin/vectorflow-frontend
COPY --from=source-export /build/identity.json /opt/vectorflow/release.json
RUN chmod 0555 /usr/local/bin/vectorflow-frontend
ENTRYPOINT ["/usr/local/bin/vectorflow-frontend"]
