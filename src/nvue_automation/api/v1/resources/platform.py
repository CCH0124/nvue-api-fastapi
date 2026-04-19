"""
Platform API Endpoints.

This module provides REST API endpoints for accessing platform hardware information
including ASIC, inventory, environment sensors, and transceivers.
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
from nvue_automation.models.resources.platform import EnvironmentResponse
from nvue_automation.models.resources.platform import PlatformResponse
from nvue_automation.models.schemas import ErrorResponse
from nvue_automation.services.resources.platform_service import PlatformService

router = APIRouter(prefix="/api/v1/platform", tags=["Platform"])


async def get_platform_service() -> AsyncGenerator[PlatformService, None]:
    """
    Dependency injection: Create PlatformService with AsyncNVUEClient.

    Yields:
        PlatformService: Configured platform service instance
    """
    settings = Settings()
    async with AsyncNVUEClient(settings) as client:
        yield PlatformService(client)


@router.get(
    "",
    response_model=PlatformResponse,
    summary="Display platform information",
    description="""
    Get comprehensive platform hardware summary including:
    - Manufacturer and model information
    - Serial number and hardware version
    - ASIC type and model
    - CPU architecture

    This is a high-level overview endpoint ideal for dashboards and monitoring.
    """,
    responses={
        200: {"description": "Platform summary retrieved successfully", "model": PlatformResponse},
        500: {"description": "Internal server error or NVUE API error", "model": ErrorResponse},
    },
)
async def get_platform(service: Annotated[PlatformService, Depends(get_platform_service)]):
    """
    Get platform hardware summary.

    Returns key platform information in a single call for dashboard/monitoring use.
    """
    logger.info("[API] GET /platform")
    try:
        summary = await service.get_platform()
        logger.info(f"[API] Platform summary retrieved | manufacturer={summary.get('manufacturer')}")
        return PlatformResponse(data=summary)
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get platform summary | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get platform summary: {str(e)}") from e


# @router.get(
#     "/inventory",
#     response_model=InventoryResponse,
#     summary="Get Hardware Inventory",
#     description="""
#     Get complete hardware inventory including all platform components:
#     - ASIC information
#     - CPU details
#     - Memory modules
#     - Storage devices
#     - Network adapters

#     This endpoint provides detailed component-level information.
#     """,
#     responses={
#         200: {"description": "Inventory retrieved successfully", "model": InventoryResponse},
#         500: {"description": "Internal server error or NVUE API error", "model": ErrorResponse},
#     },
# )
# async def get_inventory(service: PlatformService = Depends(get_platform_service)):
#     """Get complete hardware inventory."""
#     logger.info("[API] GET /platform/inventory")
#     try:
#         inventory = await service.get_inventory()
#         logger.info(f"[API] Inventory retrieved | items={len(inventory)}")
#         return InventoryResponse(data=inventory)
#     except NVUEAPIError as e:
#         logger.warning(f"[API] NVUE API error | status={e.status_code}")
#         raise
#     except Exception as e:
#         logger.error(f"[API] Failed to get inventory | error={type(e).__name__}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to get inventory: {str(e)}") from e


# @router.get(
#     "/inventory/{item_id}",
#     summary="Get Inventory Item Details",
#     description="""
#     Get detailed information about a specific inventory item.

#     Common item IDs:
#     - `asic` - Switch ASIC information
#     - `cpu` - CPU details
#     - `eeprom` - EEPROM data
#     """,
#     responses={
#         200: {"description": "Inventory item retrieved successfully"},
#         404: {"description": "Inventory item not found", "model": ErrorResponse},
#         500: {"description": "Internal server error", "model": ErrorResponse},
#     },
# )
# async def get_inventory_item(
#     item_id: str = Path(..., description="Inventory item identifier (e.g., 'asic', 'cpu')"),
#     service: PlatformService = Depends(get_platform_service),
# ):
#     """Get specific inventory item details."""
#     logger.info(f"[API] GET /platform/inventory/{item_id}")
#     try:
#         item = await service.get_inventory_item(item_id)
#         logger.info(f"[API] Inventory item retrieved | item_id={item_id}")
#         return {"data": item}
#     except NVUEAPIError as e:
#         logger.warning(f"[API] NVUE API error | item_id={item_id} | status={e.status_code}")
#         raise
#     except Exception as e:
#         logger.error(f"[API] Failed to get inventory item | item_id={item_id} | error={type(e).__name__}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to get inventory item '{item_id}': {str(e)}") from e


# @router.get(
#     "/asic",
#     summary="Get ASIC Information",
#     description="""
#     Get switching ASIC (Application-Specific Integrated Circuit) information.

#     Returns chip-level details including:
#     - ASIC model and type
#     - Capabilities
#     - Port configuration
#     """,
#     responses={
#         200: {"description": "ASIC information retrieved successfully"},
#         500: {"description": "Internal server error", "model": ErrorResponse},
#     },
# )
# async def get_asic_info(service: PlatformService = Depends(get_platform_service)):
#     """Get ASIC information."""
#     logger.info("[API] GET /platform/asic")
#     try:
#         asic = await service.get_asic_info()
#         logger.info("[API] ASIC information retrieved")
#         return {"data": asic}
#     except NVUEAPIError as e:
#         logger.warning(f"[API] NVUE API error | status={e.status_code}")
#         raise
#     except Exception as e:
#         logger.error(f"[API] Failed to get ASIC info | error={type(e).__name__}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to get ASIC info: {str(e)}") from e


@router.get(
    "/environment",
    response_model=EnvironmentResponse,
    summary="Get Platform Environment Monitoring Summary",
    description="""
    Get complete environment monitoring data including:
    - Temperature sensors (all zones)
    - Fan status and RPM
    - Power supply (PSU) status

    This endpoint aggregates all environmental sensors for health monitoring.
    """,
    responses={
        200: {"description": "Environment data retrieved successfully", "model": EnvironmentResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_environment(service: Annotated[PlatformService, Depends(get_platform_service)]):
    """Get environment monitoring summary."""
    logger.info("[API] GET /platform/environment")
    try:
        environment = await service.get_environment_summary()
        logger.info("[API] Environment data retrieved")
        return EnvironmentResponse(**environment)
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get environment data | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get environment data: {str(e)}") from e


@router.get(
    "/environment/temperature",
    summary="Get Temperature Sensors",
    description="Get all temperature sensor readings.",
    responses={
        200: {"description": "Temperature data retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_temperature(service: Annotated[PlatformService, Depends(get_platform_service)]):
    """Get temperature sensor readings."""
    logger.info("[API] GET /platform/environment/temperature")
    try:
        temp_data = await service.get_temperature_sensors()
        return {"data": temp_data}
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get temperature data | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get temperature data: {str(e)}") from e


@router.get(
    "/environment/fans",
    summary="Get Fan Status",
    description="Get cooling fan status and RPM information.",
    responses={
        200: {"description": "Fan data retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_fans(service: Annotated[PlatformService, Depends(get_platform_service)]):
    """Get fan status."""
    logger.info("[API] GET /platform/environment/fans")
    try:
        fan_data = await service.get_fan_status()
        return {"data": fan_data}
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get fan data | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get fan data: {str(e)}") from e


@router.get(
    "/environment/psu",
    summary="Get PSU Status",
    description="Get power supply unit (PSU) status and metrics.",
    responses={
        200: {"description": "PSU data retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_psu(service: Annotated[PlatformService, Depends(get_platform_service)]):
    """Get PSU status."""
    logger.info("[API] GET /platform/environment/psu")
    try:
        psu_data = await service.get_psu_status()
        return {"data": psu_data}
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get PSU data | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get PSU data: {str(e)}") from e


@router.get(
    "/environment/led",
    summary="Get LED Status",
    description="Get system LED status(FAN/PSU/System/POWER).",
    responses={
        200: {"description": "LED data retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_led(service: Annotated[PlatformService, Depends(get_platform_service)]):
    """Get LED status."""
    logger.info("[API] GET /platform/environment/led")
    try:
        led_data = await service.get_led_status()
        return {"data": led_data}
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get LED data | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get LED data: {str(e)}") from e


router.get(
    "/environment/voltage",
    summary="Get Voltage Status",
    description="Get voltage sensor status and readings.",
    responses={
        200: {"description": "Voltage data retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)


async def get_voltage(service: Annotated[PlatformService, Depends(get_platform_service)]):
    """Get voltage sensor status."""
    logger.info("[API] GET /platform/environment/voltage")
    try:
        voltage_data = await service.get_voltage_status()
        return {"data": voltage_data}
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get voltage data | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get voltage data: {str(e)}") from e


# @router.get(
#     "/transceivers",
#     summary="Get All Transceivers",
#     description="""
#     Get information about all transceivers (SFP/QSFP modules).

#     Returns details for all installed optics including vendor, part number, and status.
#     """,
#     responses={
#         200: {"description": "Transceiver data retrieved successfully"},
#         500: {"description": "Internal server error", "model": ErrorResponse},
#     },
# )
# async def get_transceivers(service: PlatformService = Depends(get_platform_service)):
#     """Get all transceiver information."""
#     logger.info("[API] GET /platform/transceivers")
#     try:
#         transceivers = await service.get_transceivers()
#         return {"data": transceivers}
#     except NVUEAPIError as e:
#         logger.warning(f"[API] NVUE API error | status={e.status_code}")
#         raise
#     except Exception as e:
#         logger.error(f"[API] Failed to get transceivers | error={type(e).__name__}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to get transceivers: {str(e)}") from e


# @router.get(
#     "/transceivers/{transceiver_id}",
#     summary="Get Specific Transceiver",
#     description="Get detailed information about a specific transceiver/port.",
#     responses={
#         200: {"description": "Transceiver data retrieved successfully"},
#         404: {"description": "Transceiver not found", "model": ErrorResponse},
#         500: {"description": "Internal server error", "model": ErrorResponse},
#     },
# )
# async def get_transceiver(
#     transceiver_id: str = Path(..., description="Transceiver/port identifier (e.g., 'swp1')"),
#     service: PlatformService = Depends(get_platform_service),
# ):
#     """Get specific transceiver information."""
#     logger.info(f"[API] GET /platform/transceivers/{transceiver_id}")
#     try:
#         transceiver = await service.get_transceiver(transceiver_id)
#         return {"data": transceiver}
#     except NVUEAPIError as e:
#         logger.warning(f"[API] NVUE API error | transceiver_id={transceiver_id} | status={e.status_code}")
#         raise
#     except Exception as e:
#         logger.error(
#             f"[API] Failed to get transceiver | transceiver_id={transceiver_id} | error={type(e).__name__}: {str(e)}"
#         )
#         raise HTTPException(
#             status_code=500, detail=f"Failed to get transceiver '{transceiver_id}': {str(e)}"
#         ) from e
