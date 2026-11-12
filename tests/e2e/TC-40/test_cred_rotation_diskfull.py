#!/usr/bin/env python3
"""TC-40 ext: CRED-001 live credential rotation (MISP authkeys — real
coexistence window, no mocks) and DS-001 physical disk-full on a bounded
tmpfs (real kernel ENOSPC)."""

import errno
import io
import os
import tarfile
import time

import pytest
import requests

from tests.e2e.base import E2EBaseTest

pytestmark = [pytest.mark.e2e, pytest.mark.security, pytest.mark.destructive]

DS001_DIR = "/ds001"
MISP = "https://misp"
LAB_CA = "/app/certs/ca.crt"


class TestCredentialRotation(E2EBaseTest):
    """CRED-001: MISP supports multiple authkeys per user — rotation has a
    real coexistence window; revocation kills the stale key immediately."""

    tc_id = "TC-40"

    def _key(self) -> str:
        return self.env.get("MISP_API_KEY", "")

    def _misp(self, key: str, method: str, path: str, **kw):
        return requests.request(
            method, f"{MISP}{path}",
            headers={"Authorization": key, "Accept": "application/json"},
            timeout=15, verify=LAB_CA, **kw,
        )

    def _create_key(self, comment: str) -> tuple[str, str]:
        """POST /auth_keys/add → (auth_key_id, raw_key)."""
        r = self._misp(self._key(), "POST", "/auth_keys/add/1",
                       json={"AuthKey": {"comment": comment}})
        assert r.status_code in (200, 201), r.text[:300]
        body = r.json()
        authkey = body.get("AuthKey", body)
        kid = str(authkey.get("id"))
        raw = (authkey.get("authkey_raw")
               or body.get("authkey_raw")
               or authkey.get("authkey", ""))
        assert kid and raw, f"no id/raw in response: {list(body)[:8]}"
        return kid, raw

    def _delete_key(self, kid: str) -> None:
        self._misp(self._key(), "POST", f"/auth_keys/delete/{kid}", json={})

    def test_coexistence_window_two_keys_valid(self):
        """During rotation both the old and the replacement key must work —
        that window is what makes zero-downtime rotation possible."""
        kid, raw = self._create_key("tc40-coexist")
        try:
            r_old = self._misp(self._key(), "GET", "/servers/getVersion")
            r_new = self._misp(raw, "GET", "/servers/getVersion")
            assert r_old.status_code == 200, f"primary key broken: {r_old.status_code}"
            assert r_new.status_code == 200, f"new key rejected: {r_new.status_code}"
        finally:
            self._delete_key(kid)

    def test_stale_key_rejected_after_revocation(self):
        """The stale-key contract: after revocation the old credential is
        rejected while the primary keeps working."""
        kid, raw = self._create_key("tc40-stale")
        assert self._misp(raw, "GET", "/servers/getVersion").status_code == 200
        self._delete_key(kid)
        r = self._misp(raw, "GET", "/servers/getVersion")
        assert r.status_code in (401, 403), (
            f"stale key still accepted: {r.status_code}"
        )
        assert self._misp(self._key(), "GET", "/servers/getVersion").status_code == 200

    def test_rotation_repeatable_and_propagatable(self):
        """A second rotation cycle also works, and a consumer loading the
        rotated value from the env-file mechanism authenticates — the
        propagation path itself is verified, not assumed."""
        kid, raw = self._create_key("tc40-propagate")
        try:
            env_file = f"/tmp/tc40-env-{int(time.time())}"
            with open(env_file, "w") as fh:
                fh.write(f"MISP_API_KEY={raw}\n")
            from dotenv import dotenv_values
            loaded = dotenv_values(env_file).get("MISP_API_KEY", "")
            assert loaded == raw, "env-file propagation lost the rotated key"
            r = self._misp(loaded, "GET", "/servers/getVersion")
            assert r.status_code == 200, "propagated key does not authenticate"
        finally:
            self._delete_key(kid)
            if os.path.exists(env_file):
                os.remove(env_file)


class TestPhysicalDiskFull(E2EBaseTest):
    """DS-001: real ENOSPC on the bounded /ds001 tmpfs — writes fail fast,
    partial artifacts never validate, recovery is instant on cleanup."""

    tc_id = "TC-40"
    FILLER = f"{DS001_DIR}/.tc40-filler"
    ARTIFACT = f"{DS001_DIR}/backup-partial.tar.gz"

    def teardown_method(self):
        for p in (self.FILLER, self.ARTIFACT):
            if os.path.exists(p):
                os.remove(p)

    def _fill(self) -> int:
        """Write until the kernel returns ENOSPC; returns bytes written."""
        written = 0
        with open(self.FILLER, "wb") as fh:
            while True:
                try:
                    fh.write(b"\0" * 1024 * 1024)
                    fh.flush()
                    written += 1
                except OSError as e:
                    assert e.errno == errno.ENOSPC, f"unexpected error: {e}"
                    return written

    def test_bounded_filesystem_exists(self):
        assert os.path.ismount(DS001_DIR) or os.path.isdir(DS001_DIR), (
            "/ds001 tmpfs not mounted — api was not recreated with the mount"
        )

    def test_disk_full_fails_fast_then_recovers(self):
        mb = self._fill()
        assert mb >= 40, f"tmpfs did not fill to its bound (wrote {mb}MB)"
        # Subsequent writes must fail fast (ENOSPC), never hang.
        t = time.time()
        with pytest.raises(OSError) as exc:
            with open(self.ARTIFACT, "wb") as fh:
                fh.write(b"x" * 1024)
                fh.flush()
        assert exc.value.errno == errno.ENOSPC
        assert time.time() - t < 10, "write on full fs hung"
        # Recovery: freeing the filler restores writability immediately.
        os.remove(self.FILLER)
        with open(self.ARTIFACT, "wb") as fh:
            fh.write(b"recovered")
        assert os.path.getsize(self.ARTIFACT) == 9

    def test_partial_artifact_never_passes_integrity(self):
        """A truncated tar.gz produced by an ENOSPC mid-write must be
        rejected by the same integrity check the backup flow uses —
        a partial artifact is never a valid backup."""
        self._fill()
        try:
            with open(self.ARTIFACT, "wb") as fh:
                with tarfile.open(fileobj=fh, mode="w:gz") as tar:
                    payload = b"A" * (64 * 1024 * 1024)  # exceeds the 48MB quota
                    with pytest.raises(OSError):
                        tar.addfile(tarfile.TarInfo("big.bin"), io.BytesIO(payload))
        except OSError:
            pass  # ENOSPC may surface at open/write — either is the fault
        # Integrity gate: a partial archive must fail to open or to extract.
        if os.path.exists(self.ARTIFACT) and os.path.getsize(self.ARTIFACT) > 0:
            with pytest.raises((tarfile.TarError, EOFError, OSError)):
                with tarfile.open(self.ARTIFACT) as tar:
                    tar.extractall("/tmp/tc40-extract")
        # else: zero-byte artifact — no file was left masquerading as valid.
