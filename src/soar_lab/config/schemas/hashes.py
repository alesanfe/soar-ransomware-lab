"""Network event and file hash Pydantic models."""

from pydantic import BaseModel, Field
from pydantic.networks import IPv4Address

__all__ = ["NetworkEvent", "FileHash"]


class NetworkEvent(BaseModel):
    """Network event model."""

    src_ip: IPv4Address = Field(..., description="Source IP address")
    dst_ip: IPv4Address | None = Field(None, description="Destination IP address")
    src_port: int | None = Field(None, ge=1, le=65535, description="Source port")
    dst_port: int | None = Field(None, ge=1, le=65535, description="Destination port")
    protocol: str | None = Field(None, pattern=r"^(TCP|UDP|ICMP)$", description="Network protocol")


class FileHash(BaseModel):
    """File hash model."""

    sha256: str = Field(
        ..., min_length=64, max_length=64, pattern=r"^[a-fA-F0-9]{64}$", description="SHA256 hash"
    )
    md5: str | None = Field(
        None, min_length=32, max_length=32, pattern=r"^[a-fA-F0-9]{32}$", description="MD5 hash"
    )
    sha1: str | None = Field(
        None, min_length=40, max_length=40, pattern=r"^[a-fA-F0-9]{40}$", description="SHA1 hash"
    )
