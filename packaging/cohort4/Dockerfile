FROM freshvcf-cohort2:20261008-final001 AS operations
FROM freshvcf-cohort3-proof:closure-003

# The build entry point verifies this local tag's immutable ID before building.
# Complete only the evidenced missing pg_dump/libpq library dependencies.
COPY --from=operations /usr/lib/x86_64-linux-gnu/libldap-2.5.so.0* /usr/lib/x86_64-linux-gnu/liblber-2.5.so.0* /usr/lib/x86_64-linux-gnu/libsasl2.so.2* /usr/lib/x86_64-linux-gnu/
# No dependency installation, application copy or serving process is introduced.
ENV DJANGO_SETTINGS_MODULE=vectorflow.settings \
    VF_MTA_CONSUMPTION_POLICY="" \
    VF_MTA_PUBLISHED_RUN="" \
    VF_MTA_PUBLISHED_DIGEST="" \
    VF_BTR_REPORTING_GENERATION="" \
    VF_MTA_FIXTURE_FILE="" \
    VF_MTA_FIXTURE_SHA256="" \
    VF_MTA_ACTIONS_ENABLED=0
COPY runtime-lock.json /opt/fresh/runtime-lock.json
ENTRYPOINT ["python", "-m", "django"]
CMD ["--help"]
