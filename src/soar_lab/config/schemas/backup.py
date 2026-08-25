"""Backup report Pydantic model."""

from datetime import datetime

from pydantic import BaseModel, Field

__all__ = ["BackupReport"]


class BackupReport(BaseModel):
    """Backup report model."""

    backup_id: str = Field(..., pattern=r"^BACKUP-\d{8}_\d{6}$", description="Backup ID")
    timestamp: datetime = Field(..., description="Backup timestamp")
    backup_type: str = Field(..., pattern=r"^(manual|scheduled|auto)$", description="Backup type")
    components: dict[str, bool] = Field(..., description="Backup components status")
    total_size_mb: float = Field(..., ge=0, description="Total backup size in MB")
    compression_ratio: float | None = Field(None, ge=0, le=1, description="Compression ratio")
    success: bool = Field(..., description="Backup success status")
    error_message: str | None = Field(None, description="Error message if failed")
    retention_days: int = Field(default=7, ge=1, description="Retention period in days")
