"""
Base Resource Service - Abstract base class for all NVUE resource services.

This module implements the Template Method pattern to provide common functionality
for all resource services while allowing customization through inheritance.
"""

from abc import ABC
from abc import abstractmethod
from typing import Any

from loguru import logger

from nvue_automation.core.client import AsyncNVUEClient
from nvue_automation.core.exceptions import NVUEAPIError


class BaseResourceService(ABC):
    """
    Abstract base class for NVUE resource services.

    This class provides common functionality for resource services including:
    - Standard GET operations
    - Consistent error handling
    - Logging patterns

    Design Pattern: Template Method Pattern
    - Define the skeleton of resource operations
    - Let subclasses override specific behavior

    Example:
        >>> class PlatformService(BaseResourceService):
        ...     @property
        ...     def resource_path(self) -> str:
        ...         return "/platform"
        ...
        ...     async def get_hardware_info(self) -> dict:
        ...         return await self.get()
    """

    def __init__(self, client: AsyncNVUEClient):
        """
        Initialize the resource service.

        Args:
            client: AsyncNVUEClient instance for API communication
        """
        self.client = client
        self._log_prefix = self.__class__.__name__.replace("Service", "").upper()

    @property
    @abstractmethod
    def resource_path(self) -> str:
        """
        Return the base NVUE API path for this resource.

        Must be implemented by subclasses.

        Returns:
            str: NVUE API path (e.g., '/platform', '/system/cpu')
        """
        pass

    async def get(self, sub_path: str = "") -> dict[str, Any]:
        """
        Get resource information from NVUE API.

        This is a template method that provides consistent logging and error handling
        for all resource GET operations.

        Args:
            sub_path: Optional sub-path to append to resource_path (e.g., '/inventory')

        Returns:
            dict[str, Any]: Resource data from NVUE API

        Raises:
            NVUEAPIError: If API request fails

        Example:
            >>> # Get base resource
            >>> data = await service.get()
            >>> # Get sub-resource
            >>> inventory = await service.get("/inventory")
        """
        path = f"{self.resource_path}{sub_path}"
        logger.info(f"[{self._log_prefix}] Fetching resource | path={path}")

        try:
            resp = await self.client.request("GET", path)
            data = resp.json()

            # Log success with data summary
            data_size = len(str(data))
            logger.debug(f"[{self._log_prefix}] Resource fetched | path={path} | size={data_size} bytes")

            return data

        except NVUEAPIError as e:
            logger.error(
                f"[{self._log_prefix}] Failed to fetch resource | path={path} | "
                f"status={e.status_code} | detail={e.detail}"
            )
            raise
        except Exception as e:
            logger.error(f"[{self._log_prefix}] Unexpected error | path={path} | error={type(e).__name__}: {str(e)}")
            raise

    async def get_item(self, item_id: str, sub_path: str = "") -> dict[str, Any]:
        """
        Get a specific resource item by ID.

        Args:
            item_id: Resource item identifier
            sub_path: Optional prefix path before item_id

        Returns:
            dict[str, Any]: Resource item data

        Example:
            >>> # Get specific inventory item
            >>> asic = await service.get_item("asic1", sub_path="/inventory")
        """
        path = f"{sub_path}/{item_id}" if sub_path else f"/{item_id}"
        return await self.get(path)
