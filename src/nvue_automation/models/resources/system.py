"""Pydantic models for System resource responses."""

from typing import Any

from pydantic import BaseModel
from pydantic import Field


class CPUInfoResponse(BaseModel):
    """CPU information and statistics."""

    data: dict[str, Any] = Field(..., description="CPU information and usage statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "data": {
                    "core-count": 1,
                    "model": "QEMU Virtual CPU version 2.5+",
                    "utilization": 0.5999999999999943,
                }
            }
        }


class MemoryInfoResponse(BaseModel):
    """Memory information and statistics."""

    data: dict[str, Any] = Field(..., description="Memory usage statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "data": {
                    "Physical": {
                        "buffer": 39649280,
                        "cache": 440995840,
                        "free": 94654464,
                        "total": 1793617920,
                        "used": 1409921024,
                        "utilization": 78.60765708674454,
                    },
                    "Swap": {"free": 0, "total": 0, "used": 0, "utilization": 0},
                }
            }
        }


class DiskUsageResponse(BaseModel):
    """Disk usage information."""

    data: dict[str, Any] = Field(..., description="Disk usage statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "data": {
                    "/": {
                        "available": "2.7G",
                        "file-system": "/dev/sda5",
                        "size": "5.4G",
                        "used": "2.5G",
                        "used-percent": "48%",
                    },
                    "/dev": {
                        "available": "847M",
                        "file-system": "udev",
                        "size": "847M",
                        "used": "0",
                        "used-percent": "0%",
                    },
                    "/dev/shm": {
                        "available": "835M",
                        "file-system": "tmpfs",
                        "size": "856M",
                        "used": "21M",
                        "used-percent": "3%",
                    },
                    "/run": {
                        "available": "171M",
                        "file-system": "tmpfs",
                        "size": "172M",
                        "used": "960K",
                        "used-percent": "1%",
                    },
                    "/run/lock": {
                        "available": "5.0M",
                        "file-system": "tmpfs",
                        "size": "5.0M",
                        "used": "0",
                        "used-percent": "0%",
                    },
                    "/tmp": {
                        "available": "856M",
                        "file-system": "tmpfs",
                        "size": "856M",
                        "used": "4.0K",
                        "used-percent": "1%",
                    },
                }
            }
        }


class SystemResourceResponse(BaseModel):
    """
    Complete system resource summary.

    Includes CPU, memory, and disk information, plus all fields from /system endpoint.
    Uses extra='allow' to preserve all NVUE API response fields.
    """

    model_config = {
        "extra": "allow",
        "json_schema_extra": {
            "example": {
                "cpu": {
                    "core-count": 1,
                    "model": "QEMU Virtual CPU version 2.5+",
                    "utilization": 0.5999999999999943,
                },
                "memory": {
                    "Physical": {
                        "buffer": 39837696,
                        "cache": 441163776,
                        "free": 94396416,
                        "total": 1793617920,
                        "used": 1409830912,
                        "utilization": 78.60263305130225,
                    },
                    "Swap": {"free": 0, "total": 0, "used": 0, "utilization": 0},
                },
                "disk": {
                    "/": {
                        "available": "2.7G",
                        "file-system": "/dev/sda5",
                        "size": "5.4G",
                        "used": "2.5G",
                        "used-percent": "48%",
                    },
                    "/dev": {
                        "available": "847M",
                        "file-system": "udev",
                        "size": "847M",
                        "used": "0",
                        "used-percent": "0%",
                    },
                    "/dev/shm": {
                        "available": "835M",
                        "file-system": "tmpfs",
                        "size": "856M",
                        "used": "21M",
                        "used-percent": "3%",
                    },
                    "/run": {
                        "available": "171M",
                        "file-system": "tmpfs",
                        "size": "172M",
                        "used": "960K",
                        "used-percent": "1%",
                    },
                    "/run/lock": {
                        "available": "5.0M",
                        "file-system": "tmpfs",
                        "size": "5.0M",
                        "used": "0",
                        "used-percent": "0%",
                    },
                    "/tmp": {
                        "available": "856M",
                        "file-system": "tmpfs",
                        "size": "856M",
                        "used": "4.0K",
                        "used-percent": "1%",
                    },
                },
                "build": "Cumulus Linux 5.12.1",
                "date-time": "2026-04-01 05:16:05",
                "health-status": "OK",
                "hostname": "itachi-switch",
                "maintenance": {"mode": "disabled", "ports": "enabled"},
                "platform": "N/A",
                "product-name": "Cumulus Linux",
                "product-release": "5.12.1",
                "status": "N/A",
                "swap-memory": "0 Bytes used / 0 Bytes free / 0 Bytes total",
                "system-memory": "1.31 GB used / 90.02 MB free / 1.67 GB total",
                "timezone": "Etc/UTC",
                "uptime": 11982,
                "version": {
                    "build-date": "Thu Feb 27 09:38:55 UTC 2025",
                    "image": "5.12.1.1000",
                    "kernel": "6.1.0-cl-1-amd64",
                    "onie": "N/A",
                },
            }
        },
    }

    cpu: dict[str, Any] = Field(..., description="CPU information and usage")
    memory: dict[str, Any] = Field(..., description="Memory usage statistics")
    disk: dict[str, Any] = Field(..., description="Disk usage information")
