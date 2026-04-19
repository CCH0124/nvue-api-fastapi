"""
System Service - Manage system resources and configuration.

This service handles system-level operations including:
- CPU information and usage
- Memory statistics
- Disk usage
- System configuration
"""

from typing import Any

from loguru import logger

from nvue_automation.services.base.resource_service import BaseResourceService


class SystemService(BaseResourceService):
    """
    System Resource Service.

    Provides access to system-level information including:
    - CPU usage and statistics
    - Memory utilization
    - Disk usage
    - Hostname, timezone, and system settings

    Design Pattern: Service Layer
    - Encapsulates system API complexity
    - Provides business-focused methods

    Example:
        >>> async with AsyncNVUEClient(settings) as client:
        ...     service = SystemService(client)
        ...     resources = await service.get_resource_summary()
        ...     print(f"CPU: {resources['cpu']['usage']}%")
    """

    @property
    def resource_path(self) -> str:
        """System API base path."""
        return "/system"

    # ==================== High-Level Business Methods ====================

    async def get_resource_summary(self) -> dict[str, Any]:
        """
        Get system resource summary (CPU, Memory, Disk).

        Facade method that aggregates all system resource information
        into a single response for dashboard/monitoring use cases.

        Returns:
            dict containing:
              - cpu: CPU usage and statistics
              - memory: Memory utilization
              - disk: Disk usage
              - hostname: System hostname
              - uptime: System uptime (if available)

        Example:
            >>> summary = await service.get_resource_summary()
            >>> print(f"CPU: {summary['cpu']['usage']}%")
            >>> print(f"Memory: {summary['memory']['utilization']}%")
            >>> print(f"Disk: {summary['disk']['utilization']}%")
        """
        logger.info("[SYSTEM] Fetching resource summary")

        # Fetch all resource data
        resources = {
            "cpu": await self.get_cpu_info(),
            "memory": await self.get_memory_info(),
            "disk": await self.get_disk_usage(),
        }

        # Add basic system info
        try:
            system_info = await self.get()
            resources.update(**system_info)
        except Exception as e:
            logger.warning(f"[SYSTEM] Could not fetch system info | error={str(e)}")
            resources["hostname"] = None
            resources["timezone"] = None

        logger.info("[SYSTEM] Resource summary retrieved")
        return resources

    # ==================== CPU Information ====================

    async def get_cpu_info(self) -> dict[str, Any]:
        """
        Get CPU information and usage statistics.

        Returns detailed CPU metrics including:
        - CPU model and architecture
        - Number of cores
        - Current usage percentage
        - Load averages

        Returns:
            dict[str, Any]: CPU information and statistics

        Example:
            >>> cpu = await service.get_cpu_info()
            >>> print(f"Cores: {cpu.get('cores')}")
            >>> print(f"Usage: {cpu.get('usage')}%")
        """
        logger.info("[SYSTEM] Fetching CPU information")
        cpu_data = await self.get("/cpu")

        # Log key metrics
        usage = cpu_data.get("usage")
        if usage:
            logger.debug(f"[SYSTEM] CPU usage: {usage}%")

        return cpu_data

    # ==================== Memory Information ====================

    async def get_memory_info(self) -> dict[str, Any]:
        """
        Get memory information and usage statistics.

        Returns detailed memory metrics including:
        - Total memory
        - Used memory
        - Free memory
        - Utilization percentage
        - Buffers and cache

        Returns:
            dict[str, Any]: Memory information and statistics

        Example:
            >>> memory = await service.get_memory_info()
            >>> print(f"Total: {memory.get('total')} MB")
            >>> print(f"Used: {memory.get('used')} MB")
            >>> print(f"Utilization: {memory.get('utilization')}%")
        """
        logger.info("[SYSTEM] Fetching memory information")
        memory_data = await self.get("/memory")

        # Log key metrics
        utilization = memory_data.get("utilization")
        if utilization:
            logger.debug(f"[SYSTEM] Memory utilization: {utilization}%")

        return memory_data

    # ==================== Disk Information ====================

    async def get_disk_usage(self) -> dict[str, Any]:
        """
        Get disk usage information.

        Returns detailed disk metrics including:
        - Total disk space
        - Used space
        - Available space
        - Utilization percentage

        Returns:
            dict[str, Any]: Disk usage information

        Example:
            >>> disk = await service.get_disk_usage()
            >>> print(f"Total: {disk.get('total')} GB")
            >>> print(f"Used: {disk.get('used')} GB")
            >>> print(f"Utilization: {disk.get('utilization')}%")
        """
        logger.info("[SYSTEM] Fetching disk usage")
        disk_data = await self.get("/disk/usage")

        # Log key metrics
        utilization = disk_data.get("utilization")
        if utilization:
            logger.debug(f"[SYSTEM] Disk utilization: {utilization}%")

        return disk_data

    # ==================== System Configuration ====================

    async def get_hostname(self) -> str | None:
        """
        Get system hostname.

        Returns:
            str | None: System hostname or None if not available

        Example:
            >>> hostname = await service.get_hostname()
            >>> print(f"Hostname: {hostname}")
        """
        logger.info("[SYSTEM] Fetching hostname")
        system_data = await self.get()
        return system_data.get("hostname")

    async def get_timezone(self) -> str | None:
        """
        Get system timezone setting.

        Returns:
            str | None: Timezone (e.g., 'UTC', 'America/New_York') or None

        Example:
            >>> tz = await service.get_timezone()
            >>> print(f"Timezone: {tz}")
        """
        system_data = await self.get()
        return system_data.get("timezone")

    async def get_system_info(self) -> dict[str, Any]:
        """
        Get general system information.

        Returns complete system configuration including:
        - Hostname
        - Timezone
        - Message of the day
        - Global system settings

        Returns:
            dict[str, Any]: System configuration

        Example:
            >>> info = await service.get_system_info()
            >>> print(f"Host: {info.get('hostname')}")
            >>> print(f"TZ: {info.get('timezone')}")
        """
        logger.info("[SYSTEM] Fetching system information")
        return await self.get()
