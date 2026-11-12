#!/bin/sh
# Render the realm template into the (tmpfs-backed) import dir,
# substituting secret placeholders from env, then exec kc.sh.
# Secrets never live in the image or the repo — compose fails closed
# when the env vars are unset.
set -eu

for var in OIDC_CLIENT_SECRET KC_ADMIN_USER_PASS KC_ANALYST_USER_PASS; do
  eval "val=\${$var:-}"
  if [ -z "$val" ]; then
    echo "entrypoint: missing required env var $var" >&2
    exit 1
  fi
done

mkdir -p /opt/keycloak/data/import
sed -e "s|__OIDC_CLIENT_SECRET__|${OIDC_CLIENT_SECRET}|" \
    -e "s|__KC_ADMIN_USER_PASS__|${KC_ADMIN_USER_PASS}|" \
    -e "s|__KC_ANALYST_USER_PASS__|${KC_ANALYST_USER_PASS}|" \
    /srv/soar-realm.template.json \
    > /opt/keycloak/data/import/soar-realm.json

# SSO-EVAL-004: TLS on both planes — front channel (browser → issuer)
# and backchannel (oauth2-proxy token/JWKS calls) ride the lab PKI.
# `start-dev` force-enables a plain-HTTP listener that ignores
# --http-enabled and --http-host binds all listeners together, so the
# production `start` mode (auto-builds on boot, dev-file H2 storage)
# is the only mode that honors a TLS-only posture.
exec /opt/keycloak/bin/kc.sh start \
  --db dev-file \
  --import-realm \
  --hostname="${KC_HOSTNAME:-https://localhost:8071}" \
  --hostname-strict=false \
  --https-certificate-file=/etc/keycloak/tls/keycloak.crt \
  --https-certificate-key-file=/etc/keycloak/tls/keycloak.key \
  --http-enabled=false
