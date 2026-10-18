# DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
FROM node:20.18-alpine@sha256:053c1d99e608fe9fa0db6821edd84276277c0a663cd181f4a3e59ee20f5f07ea AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ARG REACT_APP_API_HOST=/
ARG REACT_APP_VF_API_HOST_MTO=/api/mto
ARG REACT_APP_WS_API_HOST
ARG REACT_APP_SECRET_KEY
ARG REACT_APP_AG_GRID_LICENSE_KEY
ARG FRONTEND_BUILD_HEAP_MIB
ARG VF_CONSTRAINED_BUILD=0
ENV REACT_APP_API_HOST=$REACT_APP_API_HOST REACT_APP_VF_API_HOST_MTO=$REACT_APP_VF_API_HOST_MTO \
    REACT_APP_WS_API_HOST=$REACT_APP_WS_API_HOST REACT_APP_SECRET_KEY=$REACT_APP_SECRET_KEY \
    REACT_APP_AG_GRID_LICENSE_KEY=$REACT_APP_AG_GRID_LICENSE_KEY \
    REACT_APP_ENABLE_LOCAL_LOGIN=true REACT_APP_DEMO_MODE=false GENERATE_SOURCEMAP=false
# Retain the demonstrated CRA build policy. Build logs and focused tests remain
# separate evidence; successful asset emission is not a clean TypeScript audit.
ENV CI=false TSC_COMPILE_ON_ERROR=true
COPY release/frontend-build.cjs /build-tools/frontend-build.cjs
RUN if [ -n "$FRONTEND_BUILD_HEAP_MIB" ]; then \
      case "$FRONTEND_BUILD_HEAP_MIB" in *[!0-9]*|0) echo "Invalid optional build heap" >&2; exit 1;; esac; \
      export NODE_OPTIONS="${NODE_OPTIONS:+$NODE_OPTIONS }--max-old-space-size=$FRONTEND_BUILD_HEAP_MIB"; \
    fi; \
    VF_CONSTRAINED_BUILD="$VF_CONSTRAINED_BUILD" node /build-tools/frontend-build.cjs
FROM nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10
COPY --from=build /app/build /usr/share/nginx/html
COPY release/nginx.template /etc/nginx/templates/vectorflow.template
COPY release/frontend-entrypoint.sh /usr/local/bin/vectorflow-frontend
RUN chmod 0555 /usr/local/bin/vectorflow-frontend
ENTRYPOINT ["/usr/local/bin/vectorflow-frontend"]
