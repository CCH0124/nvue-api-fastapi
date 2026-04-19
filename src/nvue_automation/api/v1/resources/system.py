"""
System API Endpoints.

This module provides REST API endpoints for accessing system resource information
including CPU, memory, and disk usage.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger

from nvue_automation.config.settings import Settings
from nvue_automation.core.client import AsyncNVUEClient
from nvue_automation.core.exceptions import NVUEAPIError
from nvue_automation.models.resources.system import CPUInfoResponse
from nvue_automation.models.resources.system import DiskUsageResponse
from nvue_automation.models.resources.system import MemoryInfoResponse
from nvue_automation.models.resources.system import SystemResourceResponse
from nvue_automation.models.schemas import ErrorResponse
from nvue_automation.services.resources.system_service import SystemService

router = APIRouter(prefix="/api/v1/system", tags=["System"])


async def get_system_service() -> AsyncGenerator[SystemService, None]:
    """
    Dependency injection: Create SystemService with AsyncNVUEClient.

    Yields:
        SystemService: Configured system service instance
    """
    settings = Settings()
    async with AsyncNVUEClient(settings) as client:
        yield SystemService(client)


@router.get(
    "/resources",
    response_model=SystemResourceResponse,
    summary="Get System Resource Summary",
    description="""
    Get comprehensive system resource summary including:
    - CPU usage and statistics
    - Memory utilization
    - Disk usage
    - Hostname and timezone

    This is a high-level overview endpoint ideal for dashboards and monitoring.
    All resource metrics are aggregated in a single response.
    """,
    responses={
        200: {"description": "System resources retrieved successfully", "model": SystemResourceResponse},
        500: {"description": "Internal server error or NVUE API error", "model": ErrorResponse},
    },
)
async def get_resource_summary(service: Annotated[SystemService, Depends(get_system_service)]):
    """
    Get system resource summary.

    Returns CPU, memory, disk, and basic system info in a single call.
    """
    logger.info("[API] GET /system/resources")
    try:
        resources = await service.get_resource_summary()
        logger.info("[API] System resources retrieved")
        return SystemResourceResponse(**resources)
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get system resources | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get system resources: {str(e)}") from e


@router.get(
    "/cpu",
    response_model=CPUInfoResponse,
    summary="Get CPU Information",
    description="""
    Get CPU information and usage statistics including:
    - CPU model and architecture
    - Number of cores
    - Current usage percentage
    - Load averages (1min, 5min, 15min)

    Useful for monitoring CPU performance and detecting high load conditions.
    """,
    responses={
        200: {"description": "CPU information retrieved successfully", "model": CPUInfoResponse},
        500: {"description": "Internal server error or NVUE API error", "model": ErrorResponse},
    },
)
async def get_cpu_info(service: Annotated[SystemService, Depends(get_system_service)]):
    """Get CPU information and usage."""
    logger.info("[API] GET /system/cpu")
    try:
        cpu_data = await service.get_cpu_info()
        logger.info(f"[API] CPU info retrieved | usage={cpu_data.get('usage')}%")
        return CPUInfoResponse(data=cpu_data)
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get CPU info | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get CPU info: {str(e)}") from e


@router.get(
    "/memory",
    response_model=MemoryInfoResponse,
    summary="Get Memory Information",
    description="""
    Get memory usage statistics including:
    - Total memory (MB)
    - Used memory (MB)
    - Free memory (MB)
    - Utilization percentage
    - Buffers and cache

    Useful for monitoring memory consumption and detecting potential memory issues.
    """,
    responses={
        200: {"description": "Memory information retrieved successfully", "model": MemoryInfoResponse},
        500: {"description": "Internal server error or NVUE API error", "model": ErrorResponse},
    },
)
async def get_memory_info(service: Annotated[SystemService, Depends(get_system_service)]):
    """Get memory information and usage."""
    logger.info("[API] GET /system/memory")
    try:
        memory_data = await service.get_memory_info()
        logger.info(f"[API] Memory info retrieved | utilization={memory_data.get('utilization')}%")
        return MemoryInfoResponse(data=memory_data)
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get memory info | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get memory info: {str(e)}") from e


@router.get(
    "/disk",
    response_model=DiskUsageResponse,
    summary="Get Disk Usage",
    description="""
    Get disk usage information including:
    - Total disk space (GB)
    - Used space (GB)
    - Available space (GB)
    - Utilization percentage

    Useful for monitoring disk consumption and preventing disk space issues.
    """,
    responses={
        200: {"description": "Disk usage retrieved successfully", "model": DiskUsageResponse},
        500: {"description": "Internal server error or NVUE API error", "model": ErrorResponse},
    },
)
async def get_disk_usage(service: Annotated[SystemService, Depends(get_system_service)]):
    """Get disk usage information."""
    logger.info("[API] GET /system/disk")
    try:
        disk_data = await service.get_disk_usage()
        logger.info(f"[API] Disk usage retrieved | utilization={disk_data.get('utilization')}%")
        return DiskUsageResponse(data=disk_data)
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get disk usage | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get disk usage: {str(e)}") from e


@router.get(
    "/info",
    summary="Get System Information",
    description="""
    Get general system configuration information including:
    - Hostname
    - Timezone
    - Message of the day
    - Global system settings
    """,
    responses={
        200: {"description": "System information retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_system_info(service: Annotated[SystemService, Depends(get_system_service)]):
    """Get general system information."""
    logger.info("[API] GET /system/info")
    try:
        system_info = await service.get_system_info()
        logger.info(f"[API] System info retrieved | hostname={system_info.get('hostname')}")
        return {"data": system_info}
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get system info | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get system info: {str(e)}") from e
