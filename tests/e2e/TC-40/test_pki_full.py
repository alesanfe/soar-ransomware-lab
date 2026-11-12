#!/usr/bin/env python3
"""TC-40 ext: full PKI lifecycle — expired, not-yet-valid, revoked (real
CRL), incomplete chain and mTLS client-cert trust. A throwaway CA is
built inside the test with openssl; validation is done by openssl
itself, no simulated checks."""

import os
import shutil
import subprocess

import pytest

from tests.e2e.base import E2EBaseTest

pytestmark = [pytest.mark.e2e, pytest.mark.security]

PKI_DIR = "/tmp/tc40-pki"

CA_CNF = """[ca]
default_ca = CA_default
[CA_default]
dir = {d}
database = {d}/index.txt
new_certs_dir = {d}/newcerts
certificate = {d}/ca.crt
private_key = {d}/ca.key
serial = {d}/serial
default_md = sha256
policy = policy_any
default_days = 365
default_crl_days = 30
[policy_any]
commonName = supplied
"""


def _ossl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["openssl", *args], capture_output=True, text=True, timeout=30)


class TestPKILifecycle(E2EBaseTest):
    tc_id = "TC-40"

    @classmethod
    def setup_class(cls):
        shutil.rmtree(PKI_DIR, ignore_errors=True)
        for d in ("", "/certs", "/newcerts", "/crl"):
            os.makedirs(PKI_DIR + d, exist_ok=True)
        open(f"{PKI_DIR}/index.txt", "w").close()
        with open(f"{PKI_DIR}/serial", "w") as fh:
            fh.write("1000")
        _ossl("genrsa", "-out", f"{PKI_DIR}/ca.key", "2048")
        _ossl("req", "-x509", "-new", "-key", f"{PKI_DIR}/ca.key",
              "-subj", "/CN=tc40-ca", "-days", "365", "-out", f"{PKI_DIR}/ca.crt")
        with open(f"{PKI_DIR}/ca.cnf", "w") as fh:
            fh.write(CA_CNF.format(d=PKI_DIR))

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(PKI_DIR, ignore_errors=True)

    def _sign(self, name: str, cn: str,
              startdate: str | None = None, enddate: str | None = None) -> str:
        _ossl("genrsa", "-out", f"{PKI_DIR}/{name}.key", "2048")
        _ossl("req", "-new", "-key", f"{PKI_DIR}/{name}.key",
              "-subj", f"/CN={cn}", "-out", f"{PKI_DIR}/{name}.csr")
        args = ["ca", "-batch", "-config", f"{PKI_DIR}/ca.cnf",
                "-in", f"{PKI_DIR}/{name}.csr", "-out", f"{PKI_DIR}/{name}.crt"]
        if startdate:
            args += ["-startdate", startdate]
        if enddate:
            args += ["-enddate", enddate]
        r = _ossl(*args)
        assert r.returncode == 0, r.stderr[:300]
        return f"{PKI_DIR}/{name}.crt"

    def _verify(self, cert: str, *extra: str) -> tuple[int, str]:
        r = _ossl("verify", "-CAfile", f"{PKI_DIR}/ca.crt", *extra, cert)
        return r.returncode, (r.stdout + r.stderr)

    def test_expired_certificate_rejected(self):
        crt = self._sign("expired", "expired.lab",
                         startdate="20200101000000Z", enddate="20210101000000Z")
        code, out = self._verify(crt)
        assert code != 0 and "expired" in out.lower(), out[:200]

    def test_not_yet_valid_certificate_rejected(self):
        crt = self._sign("notyet", "notyet.lab",
                         startdate="20990101000000Z", enddate="21000101000000Z")
        code, out = self._verify(crt)
        assert code != 0 and "not yet valid" in out.lower(), out[:200]

    def test_incomplete_chain_rejected(self):
        _ossl("genrsa", "-out", f"{PKI_DIR}/foreign.key", "2048")
        _ossl("req", "-x509", "-new", "-key", f"{PKI_DIR}/foreign.key",
              "-subj", "/CN=foreign-ca", "-days", "365", "-out", f"{PKI_DIR}/foreign.crt")
        _ossl("genrsa", "-out", f"{PKI_DIR}/leaf.key", "2048")
        _ossl("req", "-new", "-key", f"{PKI_DIR}/leaf.key",
              "-subj", "/CN=leaf.lab", "-out", f"{PKI_DIR}/leaf.csr")
        r = _ossl("x509", "-req", "-in", f"{PKI_DIR}/leaf.csr",
                  "-CA", f"{PKI_DIR}/foreign.crt", "-CAkey", f"{PKI_DIR}/foreign.key",
                  "-CAcreateserial", "-days", "30", "-out", f"{PKI_DIR}/leaf.crt")
        assert r.returncode == 0, r.stderr[:200]
        code, out = self._verify(f"{PKI_DIR}/leaf.crt")
        assert code != 0 and "unable to get local issuer" in out.lower(), out[:200]

    def test_revoked_certificate_rejected_via_crl(self):
        crt = self._sign("revoked", "revoked.lab")
        r = _ossl("ca", "-batch", "-config", f"{PKI_DIR}/ca.cnf",
                  "-revoke", crt)
        assert r.returncode == 0, r.stderr[:200]
        r = _ossl("ca", "-batch", "-config", f"{PKI_DIR}/ca.cnf",
                  "-gencrl", "-out", f"{PKI_DIR}/crl/ca.crl")
        assert r.returncode == 0, r.stderr[:200]
        code, out = self._verify(
            crt, "-crl_check", "-CRLfile", f"{PKI_DIR}/crl/ca.crl")
        assert code != 0 and "revoked" in out.lower(), out[:200]

    def test_mtls_client_cert_trust_contract(self):
        """mTLS = the server verifies the client's cert against its CA:
        a client cert signed by our CA passes; a foreign one fails."""
        client = self._sign("client", "client.lab")
        code, _ = self._verify(client)
        assert code == 0, "CA-signed client cert must verify (mTLS accept)"
        _ossl("genrsa", "-out", f"{PKI_DIR}/rogue.key", "2048")
        _ossl("req", "-x509", "-new", "-key", f"{PKI_DIR}/rogue.key",
              "-subj", "/CN=rogue", "-days", "30", "-out", f"{PKI_DIR}/rogue.crt")
        code, out = self._verify(f"{PKI_DIR}/rogue.crt")
        assert code != 0, "self-signed rogue client cert must NOT verify"
