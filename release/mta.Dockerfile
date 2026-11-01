# **DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d AS admission
ARG VF_NATIVE_RELEASE_COMMIT
ARG VF_NATIVE_RELEASE_SHA256
ARG VF_SOURCE_MANIFEST_SHA256
ARG PACKAGING_TOOL_SHA256
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY tools/mta_packaging.py /tools/mta_packaging.py
RUN python -B -c "import hashlib,re,os; assert re.fullmatch('[0-9a-f]{40}', os.environ.get('VF_NATIVE_RELEASE_COMMIT','')); assert re.fullmatch('[0-9a-f]{64}', os.environ.get('VF_NATIVE_RELEASE_SHA256','')); assert re.fullmatch('[0-9a-f]{64}', os.environ.get('VF_SOURCE_MANIFEST_SHA256','')); assert hashlib.sha256(open('/tools/mta_packaging.py','rb').read()).hexdigest() == os.environ.get('PACKAGING_TOOL_SHA256')"
COPY application/ /candidate/
RUN python -B /tools/mta_packaging.py --application /candidate --commit "$VF_NATIVE_RELEASE_COMMIT" --native-sha256 "$VF_NATIVE_RELEASE_SHA256"

FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d AS dependencies
ARG VF_NATIVE_RELEASE_COMMIT
ARG VF_NATIVE_RELEASE_SHA256
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=admission /candidate /candidate
COPY --from=admission /tools /tools
COPY wheels/ /wheels/
RUN python -B /tools/mta_packaging.py --application /candidate --commit "$VF_NATIVE_RELEASE_COMMIT" --native-sha256 "$VF_NATIVE_RELEASE_SHA256" --wheelhouse /wheels && python -B -m pip install --no-index --find-links=/wheels --no-deps --no-cache-dir --no-compile --prefix=/install -r /candidate/release/requirements-mta.lock

FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d
ARG VF_NATIVE_RELEASE_COMMIT
ARG VF_NATIVE_RELEASE_SHA256
ARG VF_SOURCE_MANIFEST_SHA256
LABEL org.opencontainers.image.revision=$VF_NATIVE_RELEASE_COMMIT vectorflow.native-manifest-sha256=$VF_NATIVE_RELEASE_SHA256 vectorflow.source-manifest-sha256=$VF_SOURCE_MANIFEST_SHA256
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app VF_NATIVE_RELEASE_COMMIT=$VF_NATIVE_RELEASE_COMMIT VF_NATIVE_RELEASE_SHA256=$VF_NATIVE_RELEASE_SHA256
COPY --from=dependencies /install/ /usr/local/
COPY --from=admission /candidate/ /app/
COPY identity.json /opt/vectorflow/release.json
COPY tools/image_entrypoint.py /opt/vectorflow/image_entrypoint.py
RUN groupadd --gid 10001 vectorflow && useradd --uid 10001 --gid 10001 vectorflow && mkdir -p /var/lib/vectorflow && chown 10001:10001 /var/lib/vectorflow
WORKDIR /app
USER 10001:10001
ENTRYPOINT ["python", "/opt/vectorflow/image_entrypoint.py"]
CMD ["python", "-m", "release.service", "mta"]
