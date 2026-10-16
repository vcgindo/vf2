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
ENV REACT_APP_API_HOST=$REACT_APP_API_HOST REACT_APP_VF_API_HOST_MTO=$REACT_APP_VF_API_HOST_MTO \
    REACT_APP_WS_API_HOST=$REACT_APP_WS_API_HOST REACT_APP_SECRET_KEY=$REACT_APP_SECRET_KEY \
    REACT_APP_AG_GRID_LICENSE_KEY=$REACT_APP_AG_GRID_LICENSE_KEY \
    REACT_APP_ENABLE_LOCAL_LOGIN=true REACT_APP_DEMO_MODE=false GENERATE_SOURCEMAP=false \
    NODE_OPTIONS=--max-old-space-size=2560
RUN npm run build
FROM nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10
COPY --from=build /app/build /usr/share/nginx/html
COPY release/nginx.template /etc/nginx/templates/vectorflow.template
COPY release/frontend-entrypoint.sh /usr/local/bin/vectorflow-frontend
RUN chmod 0555 /usr/local/bin/vectorflow-frontend
ENTRYPOINT ["/usr/local/bin/vectorflow-frontend"]
