#!/bin/sh
# s3-init — fail-closed bucket bootstrap for the logging stack (OBS-008/009).
#
# `weed shell` exits non-zero on "bucket already exists", so the rc is
# captured explicitly and the output is parsed for known-idempotent
# messages only. Every bucket must then pass a real
# write -> read -> delete probe through the filer's /buckets/ path — the
# same storage the S3 gateway serves to Loki/Tempo. Any failure exits
# non-zero; Loki/Tempo declare depends_on: service_completed_successfully,
# so a broken bootstrap blocks the pipeline at boot with a clear log
# instead of a late NoSuchBucket.
set -u

run_weed() {
  # run <args...> — captures combined output; rc in $WEED_RC
  out=$(echo "$1" | weed shell -master=s3:9333 2>&1) && WEED_RC=0 || WEED_RC=$?
}

for b in loki tempo; do
  run_weed "s3.bucket.create -name $b"
  case "$out" in
    *"already exists"* | *"create bucket"* | *Created*) : ;;
    *)
      echo "$out"
      echo "FATAL: bucket $b create failed (rc=$WEED_RC)"
      exit 1
      ;;
  esac

  run_weed "s3.bucket.list"
  echo "$out" | grep -qw "$b" || {
    echo "$out"
    echo "FATAL: bucket $b missing after create"
    exit 1
  }

  # OBS-EVAL-005: the filer path can lag behind s3's healthcheck (which
  # only proves master /cluster/status) — a re-run of this one-shot on a
  # warm stack raced and died here (observed live). Retry the write probe
  # too; it exercises the exact path we need ready.
  echo "probe-$(date +%s)" >/tmp/probe.txt
  i=0
  while [ "$i" -lt 15 ]; do
    weed filer.copy /tmp/probe.txt "http://s3:8888/buckets/$b/.s3init/" >/dev/null 2>&1 && break
    i=$((i + 1))
    sleep 2
  done
  [ "$i" -lt 15 ] || {
    echo "FATAL: write probe on $b"
    exit 1
  }
  # Filer metadata is eventually consistent — retry the read briefly.
  got=""
  i=0
  while [ "$i" -lt 15 ]; do
    got=$(wget -q -O- "http://s3:8888/buckets/$b/.s3init/probe.txt" 2>/dev/null) && break
    i=$((i + 1))
    sleep 2
  done
  [ -n "$got" ] || {
    echo "FATAL: read probe on $b"
    exit 1
  }
  run_weed "fs.rm -r /buckets/$b/.s3init"
  [ "$WEED_RC" -eq 0 ] || {
    echo "$out"
    echo "FATAL: delete probe on $b (rc=$WEED_RC)"
    exit 1
  }
  [ -n "$got" ] || {
    echo "FATAL: empty readback on $b"
    exit 1
  }
  echo "bucket $b verified (write/read/delete)"
done
echo 'buckets ready'
