"""Affected file Pydantic model."""

from pydantic import BaseModel, Field, field_validator

__all__ = ["AffectedFile"]


class AffectedFile(BaseModel):
    """Affected file information."""

    path: str = Field(..., description="File path")
    name: str = Field(..., description="File name")
    size: int | None = Field(None, ge=0, description="File size in bytes")
    extension: str | None = Field(None, description="File extension")
    encrypted: bool | None = Field(None, description="Whether file is encrypted")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate that the file path is not empty."""
        if not v:
            raise ValueError("File path cannot be empty")
        return v
