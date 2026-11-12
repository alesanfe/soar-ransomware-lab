#!/bin/sh
# s3 entrypoint — renders iam.config.json from env vars at boot, then execs
# the SeaweedFS all-in-one server (OBS-012/013/015).
#
# - The committed iam.config.json is a TEMPLATE (%%VAR%% placeholders): no
#   real credentials live in git.
# - Every S3_* variable is required (set -u + explicit check): the
#   container fails fast with a clear message instead of authenticating
#   with a "change-me" default.
# - Per-component identities: loki/tempo get bucket-scoped non-admin creds;
#   the admin identity exists for weed shell / manual operations only.
set -eu

required="S3_ADMIN_ACCESS_KEY S3_ADMIN_SECRET_KEY \
LOKI_S3_ACCESS_KEY LOKI_S3_SECRET_KEY \
TEMPO_S3_ACCESS_KEY TEMPO_S3_SECRET_KEY"
for v in $required; do
  eval "val=\${$v:-}"
  case "$val" in
    "" | *change-me* | *changeme* | password | admin | soar-s3)
      echo "FATAL: \$$v is unset or a forbidden default" >&2
      exit 1
      ;;
  esac
done

sed \
  -e "s|%%S3_ADMIN_ACCESS_KEY%%|$S3_ADMIN_ACCESS_KEY|g" \
  -e "s|%%S3_ADMIN_SECRET_KEY%%|$S3_ADMIN_SECRET_KEY|g" \
  -e "s|%%LOKI_S3_ACCESS_KEY%%|$LOKI_S3_ACCESS_KEY|g" \
  -e "s|%%LOKI_S3_SECRET_KEY%%|$LOKI_S3_SECRET_KEY|g" \
  -e "s|%%TEMPO_S3_ACCESS_KEY%%|$TEMPO_S3_ACCESS_KEY|g" \
  -e "s|%%TEMPO_S3_SECRET_KEY%%|$TEMPO_S3_SECRET_KEY|g" \
  /etc/seaweedfs/iam.config.json >/tmp/iam.config.json
chmod 600 /tmp/iam.config.json

exec weed server \
  -dir=/data -ip=s3 -ip.bind=0.0.0.0 \
  -dataCenter=dc1 -rack=rack1 \
  -master.defaultReplication=010 \
  -s3 -s3.port=8333 -s3.autoCreateBucket \
  -s3.config=/tmp/iam.config.json
