"""Pydantic models for NVUE resource responses."""

from nvue_automation.models.resources.platform import EnvironmentResponse
from nvue_automation.models.resources.platform import InventoryResponse
from nvue_automation.models.resources.platform import PlatformResponse
from nvue_automation.models.resources.system import CPUInfoResponse
from nvue_automation.models.resources.system import DiskUsageResponse
from nvue_automation.models.resources.system import MemoryInfoResponse
from nvue_automation.models.resources.system import SystemResourceResponse

__all__ = [
    "PlatformResponse",
    "InventoryResponse",
    "EnvironmentResponse",
    "SystemResourceResponse",
    "CPUInfoResponse",
    "MemoryInfoResponse",
    "DiskUsageResponse",
]
