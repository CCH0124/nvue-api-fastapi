"""Pydantic models for Platform resource responses."""

from typing import Any

from pydantic import BaseModel
from pydantic import Field


class PlatformResponse(BaseModel):
    """Platform hardware summary information."""

    data: dict[str, Any] = Field(..., description="Basic platform information")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "manufacturer": "NVIDIA",
                "model": "SN4700",
                "serial_number": "MT2345X00001",
                "hardware_version": "A1",
                "asic": "Spectrum-3",
                "cpu_architecture": "x86_64",
                "product_name": "NVIDIA SN4700 Switch",
            }
        }


class InventoryResponse(BaseModel):
    """Hardware inventory response."""

    data: dict[str, Any] = Field(..., description="Complete inventory data")

    class Config:
        json_schema_extra = {
            "example": {
                "data": {
                    "asic": {"description": "Switch ASIC", "model": "Spectrum-3"},
                    "cpu": {
                        "description": "Central Processing Unit",
                        "model": "Intel Xeon",
                    },
                }
            }
        }


class EnvironmentResponse(BaseModel):
    """Environment monitoring data."""

    temperature: dict[str, Any] = Field(..., description="Temperature sensor readings")
    fans: dict[str, Any] = Field(..., description="Fan status and RPM")
    psu: dict[str, Any] = Field(..., description="Power supply unit status")

    class Config:
        json_schema_extra = {
            "example": {
                "temperature": {
                    "Board-Sensor-Near-Virtual-Switch": {
                        "crit": 85,
                        "current": "25.0",
                        "max": 80,
                        "min": 5,
                        "state": "ok",
                    },
                    "Board-Sensor-at-Front-Left-Corner": {
                        "crit": 85,
                        "current": "25.0",
                        "max": 80,
                        "min": 5,
                        "state": "ok",
                    },
                    "Board-Sensor-at-Front-Right-Corner": {
                        "crit": 85,
                        "current": "25.0",
                        "max": 80,
                        "min": 5,
                        "state": "ok",
                    },
                    "Board-Sensor-near-CPU": {
                        "crit": 85,
                        "current": "25.0",
                        "max": 80,
                        "min": 5,
                        "state": "ok",
                    },
                    "Board-Sensor-near-Fan": {
                        "crit": 85,
                        "current": "25.0",
                        "max": 80,
                        "min": 5,
                        "state": "ok",
                    },
                    "PSU1-Temp-Sensor": {
                        "crit": 85,
                        "current": "25.0",
                        "max": 80,
                        "min": 5,
                        "state": "ok",
                    },
                    "PSU2-Temp-Sensor": {
                        "crit": 85,
                        "current": "25.0",
                        "max": 80,
                        "min": 5,
                        "state": "ok",
                    },
                },
                "fans": {
                    "FAN1/1": {
                        "current-speed": "6000",
                        "direction": "N/A",
                        "max-speed": "29000",
                        "min-speed": "2500",
                        "state": "ok",
                    },
                    "FAN1/2": {
                        "current-speed": "6000",
                        "direction": "N/A",
                        "max-speed": "29000",
                        "min-speed": "2500",
                        "state": "ok",
                    },
                    "FAN2/1": {
                        "current-speed": "6000",
                        "direction": "N/A",
                        "max-speed": "29000",
                        "min-speed": "2500",
                        "state": "ok",
                    },
                    "FAN2/2": {
                        "current-speed": "6000",
                        "direction": "N/A",
                        "max-speed": "29000",
                        "min-speed": "2500",
                        "state": "ok",
                    },
                    "FAN3/1": {
                        "current-speed": "6000",
                        "direction": "N/A",
                        "max-speed": "29000",
                        "min-speed": "2500",
                        "state": "ok",
                    },
                    "FAN3/2": {
                        "current-speed": "6000",
                        "direction": "N/A",
                        "max-speed": "29000",
                        "min-speed": "2500",
                        "state": "ok",
                    },
                    "PSU1/FAN": {
                        "current-speed": "6000",
                        "direction": "N/A",
                        "max-speed": "29000",
                        "min-speed": "2500",
                        "state": "ok",
                    },
                    "PSU2/FAN": {
                        "current-speed": "6000",
                        "direction": "N/A",
                        "max-speed": "29000",
                        "min-speed": "2500",
                        "state": "ok",
                    },
                },
                "psu": {
                    "PSU1": {
                        "capacity": "N/A",
                        "current": "N/A",
                        "power": "N/A",
                        "state": "ok",
                        "voltage": "N/A",
                    },
                    "PSU2": {
                        "capacity": "N/A",
                        "current": "N/A",
                        "power": "N/A",
                        "state": "ok",
                        "voltage": "N/A",
                    },
                },
            }
        }
