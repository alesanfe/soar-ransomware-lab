"""Helper functions and constants for IOC generation."""

import random

_TLDS = ["com", "net", "org", "io", "biz", "info", "ru", "cn", "xyz"]
_URL_PATHS = [
    "download",
    "api/v1",
    "update",
    "config",
    "index.php",
    "login",
    "payload.exe",
    "script.js",
]
_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"


def gen_ip() -> str:
    """Generate a single random private IP."""
    p = random.choice(["10", "172", "192"])
    if p == "10":
        return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    if p == "172":
        return f"172.{random.randint(16, 31)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    return f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}"
