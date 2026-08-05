"""Seed Wazuh host config directory with default files from the Wazuh image.

The Wazuh 4.14.0 manager image expects a non-empty /wazuh-config-mount and
requires /var/ossec/etc/ossec.conf to be present. After a `make reset`, the
host `artifacts/data/wazuh/etc` directory is cleaned and only a few tracked
files are restored, so it is not enough for the container to start. This
script copies the default `etc` contents from the Wazuh image and lets the
container generate fresh sslmanager certificates on first run.
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
WAZUH_ETC = ROOT / "artifacts" / "data" / "wazuh" / "etc"
WAZUH_CONFIG = ROOT / "artifacts" / "data" / "wazuh" / "config"
IMAGE = "wazuh/wazuh-manager:4.14.0"


def run(cmd: list[str], check: bool = True) -> int:
    print(" ".join(cmd))
    return subprocess.run(cmd, check=check, text=True).returncode


def main():
    WAZUH_ETC.mkdir(parents=True, exist_ok=True)
    if (WAZUH_ETC / "ossec.conf").exists():
        print("[seed-wazuh] ossec.conf already present, skipping seed")
    else:
        print("[seed-wazuh] ossec.conf missing, seeding default Wazuh config")
        host_path = str(WAZUH_ETC.resolve()).replace("\\", "/")
        if os.name == "nt":
            host_path = host_path[0].lower() + host_path[1:]
        cmd = [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "sh",
            "-v",
            f"{host_path}:/target",
            IMAGE,
            "-c",
            "cp -an /var/ossec/data_tmp/permanent/var/ossec/etc/. /target/",
        ]
        run(cmd)

        if (WAZUH_ETC / "ossec.conf").exists():
            print("[seed-wazuh] ossec.conf created successfully")
        else:
            print("[seed-wazuh] WARN: ossec.conf was not created")

    # Always remove cert/key on host so Wazuh regenerates fresh ones.
    # Deleting on the host avoids permission issues inside the container bind mount.
    import stat

    for name in ("sslmanager.cert", "sslmanager.key"):
        path = WAZUH_ETC / name
        if path.exists():
            try:
                # Ensure writable before unlinking (Windows bind mounts may be read-only).
                path.chmod(stat.S_IWRITE)
                path.unlink()
                print(f"[seed-wazuh] removed {name}")
            except Exception as exc:
                print(f"[seed-wazuh] WARN: could not remove {name}: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
