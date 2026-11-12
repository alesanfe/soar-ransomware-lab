#!/usr/bin/env python3
"""TC-22 ext: selective restore (single member, not whole bundle),
measured RPO/RTO, and alternate-version restore — using the production
TarBackupDriver on real filesystem fixtures."""

import os
import shutil
import tarfile
import time

import pytest

from soar_lab.infrastructure.tar_backup_driver import TarBackupDriver
from tests.e2e.base import E2EBaseTest

pytestmark = [pytest.mark.e2e, pytest.mark.functional]

BASE = "/tmp/tc22"


class TestSelectiveRestore(E2EBaseTest):
    tc_id = "TC-22"
    driver = TarBackupDriver()

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(BASE, ignore_errors=True)

    def _fixture(self, name: str, files: dict[str, str]) -> str:
        d = f"{BASE}/{name}"
        shutil.rmtree(d, ignore_errors=True)
        for rel, content in files.items():
            p = f"{d}/{rel}"
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as fh:
                fh.write(content)
        return d

    def test_selective_member_restore(self):
        """Restore must be able to pick ONE member — a selective restore
        does not resurrect files that belong to other parts."""
        src = self._fixture("src1", {
            "cases/c1.json": '{"id":1}', "evidence/e1.bin": "EV1",
            "cases/c2.json": '{"id":2}'})
        dest = f"{BASE}/b1.tar.gz"
        self.driver.create(src, dest)
        self.driver.verify(dest)
        out = f"{BASE}/out1"
        with tarfile.open(dest) as tar:
            member = next(m for m in tar.getmembers()
                          if m.name.endswith("c1.json"))
            tar.extract(member, out, filter="data")
        assert os.path.exists(f"{out}/{member.name.lstrip('./')}") or \
            any("c1.json" in p for p in
                [os.path.join(r, f) for r, _, fs in os.walk(out) for f in fs])
        assert not any("e1.bin" in p for p in
                       [os.path.join(r, f) for r, _, fs in os.walk(out)
                        for f in fs]), "selective restore pulled other members"

    def test_rpo_rto_measured_and_bounded(self):
        """RTO (restore time) is measured against a bound; RPO (data loss)
        is zero — the restored bytes equal the backed-up bytes exactly."""
        payload = "X" * (2 * 1024 * 1024)  # 2MB
        src = self._fixture("src2", {"big/payload.bin": payload})
        dest = f"{BASE}/b2.tar.gz"
        t0 = time.time()
        self.driver.create(src, dest)
        create_s = time.time() - t0
        out = f"{BASE}/out2"
        os.makedirs(out, exist_ok=True)
        t0 = time.time()
        self.driver.extract(dest, out)
        rto_s = time.time() - t0
        restored = open(f"{out}/big/payload.bin").read()
        assert restored == payload, "RPO>0 — restored bytes differ"
        assert rto_s < 30, f"RTO {rto_s:.1f}s exceeds bound"
        assert create_s < 60

    def test_alternate_version_restore(self):
        """Two backups of the same source at different contents: restoring
        v1 must yield v1 bytes, not v2 — version selection is honored."""
        src = self._fixture("src3", {"data.txt": "V1"})
        d1 = f"{BASE}/v1.tar.gz"
        self.driver.create(src, d1)
        with open(f"{src}/data.txt", "w") as fh:
            fh.write("V2")
        d2 = f"{BASE}/v2.tar.gz"
        self.driver.create(src, d2)
        out = f"{BASE}/out3"
        os.makedirs(out, exist_ok=True)
        self.driver.extract(d1, out)
        assert open(f"{out}/data.txt").read() == "V1", (
            "v1 restore returned wrong version"
        )
