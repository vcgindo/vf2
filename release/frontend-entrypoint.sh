#!/bin/sh
set -eu
case "${VF_PROXY_READ_TIMEOUT:-180}" in ''|*[!0-9]*) echo "Invalid proxy timeout" >&2; exit 1;; esac
export VF_PROXY_READ_TIMEOUT="${VF_PROXY_READ_TIMEOUT:-180}"
case "${VF_TLS_MODE:-http}" in
  http)
    case "${VF_PUBLIC_URL:-}" in http://127.0.0.1:*|http://localhost:*|http://127.0.0.1|http://localhost) :;; *) echo "HTTP requires an explicit loopback public URL" >&2; exit 1;; esac
    export VF_LISTEN='80'; export VF_TLS_DIRECTIVES=''; export VF_FORWARD_SCHEME='http';;
  https)
    case "${VF_PUBLIC_URL:-}" in https://*) :;; *) echo "TLS requires an HTTPS public URL" >&2; exit 1;; esac
    test -s /run/secrets/tls_certificate && test -s /run/secrets/tls_private_key
    export VF_LISTEN='80 ssl'
    export VF_TLS_DIRECTIVES='ssl_certificate /run/secrets/tls_certificate; ssl_certificate_key /run/secrets/tls_private_key; ssl_protocols TLSv1.2 TLSv1.3;'
    export VF_FORWARD_SCHEME='https';;
  *) echo "VF_TLS_MODE must be http or https" >&2; exit 1;;
esac
envsubst '${VF_LISTEN} ${VF_TLS_DIRECTIVES} ${VF_FORWARD_SCHEME} ${VF_PROXY_READ_TIMEOUT}' < /etc/nginx/templates/vectorflow.template > /tmp/vectorflow.conf
exec nginx -c /tmp/vectorflow.conf -g 'daemon off;'
