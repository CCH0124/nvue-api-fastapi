"""
Platform Service - Manage platform hardware resources.

This service handles all platform-related operations including:
- Hardware platform information (manufacturer, model, serial)
- ASIC and inventory details
- Environment monitoring (temperature, fans, PSU)
- Transceiver/optics information
"""

from typing import Any

from loguru import logger

from nvue_automation.services.base.resource_service import BaseResourceService


class PlatformService(BaseResourceService):
    """
    Platform Resource Service.

    Provides access to platform hardware information including:
    - Basic platform info (manufacturer, model, serial number)
    - Hardware inventory (ASIC, components)
    - Environment sensors (temperature, fans, PSU, voltage)
    - Transceiver/optics details

    Design Pattern: Service Layer + Facade
    - Encapsulates platform API complexity
    - Provides high-level business methods

    Example:
        >>> async with AsyncNVUEClient(settings) as client:
        ...     service = PlatformService(client)
        ...     info = await service.get_platform_summary()
        ...     print(info['manufacturer'], info['model'])
    """

    @property
    def resource_path(self) -> str:
        """Platform API base path."""
        return "/platform"

    async def get_platform(self) -> dict[str, Any]:
        """
        Get basic platform information.

        Returns:
            dict[str, Any]: Basic platform information
        """
        logger.info("[PLATFORM] Fetching basic platform information")
        return await self.get()

    async def get_platform_summary(self) -> dict[str, Any]:
        """
        Get platform hardware summary information.

        This is a facade method that provides the most commonly needed
        platform information in a single call.

        Returns:
            dict containing:
              - manufacturer: Hardware manufacturer
              - model: Device model
              - serial_number: Device serial number
              - hardware_version: Hardware revision
              - asic: ASIC type/model
              - software_version: Installed software version

        Example:
            >>> summary = await service.get_platform_summary()
            >>> print(f"{summary['manufacturer']} {summary['model']}")
        """
        logger.info("[PLATFORM] Fetching platform summary")

        # Get base platform info
        platform_data = await self.get()

        # Extract key information
        summary = {
            "manufacturer": platform_data.get("manufacturer"),
            "model": platform_data.get("model"),
            "serial_number": platform_data.get("serial-number"),
            "hardware_version": platform_data.get("hardware-version"),
            "asic": platform_data.get("asic-model"),
            "cpu_architecture": platform_data.get("cpu"),
            "product_name": platform_data.get("product-name"),
        }

        logger.info(f"[PLATFORM] Summary retrieved | manufacturer={summary['manufacturer']} | model={summary['model']}")

        return summary

    async def get_inventory(self) -> dict[str, Any]:
        """
        Get complete hardware inventory including all components.

        Returns detailed inventory of all platform components including:
        - ASIC information
        - CPU details
        - Memory modules
        - Storage devices
        - Network adapters

        Returns:
            dict[str, Any]: Complete inventory data

        Example:
            >>> inventory = await service.get_inventory()
            >>> for item_id, details in inventory.items():
            ...     print(f"{item_id}: {details['description']}")
        """
        logger.info("[PLATFORM] Fetching hardware inventory")
        return await self.get("/inventory")

    async def get_inventory_item(self, item_id: str) -> dict[str, Any]:
        """
        Get specific inventory item details.

        Args:
            item_id: Inventory item identifier (e.g., 'asic', 'cpu', 'eeprom')

        Returns:
            dict[str, Any]: Inventory item details

        Example:
            >>> asic_info = await service.get_inventory_item("asic")
            >>> print(asic_info['model'])
        """
        logger.info(f"[PLATFORM] Fetching inventory item | item_id={item_id}")
        return await self.get_item(item_id, sub_path="/inventory")

    async def get_asic_info(self) -> dict[str, Any]:
        """
        Get ASIC (Application-Specific Integrated Circuit) information.

        Returns chip-level details about the switching ASIC including:
        - ASIC model/type
        - Capabilities
        - Port count and configuration

        Returns:
            dict[str, Any]: ASIC information

        Example:
            >>> asic = await service.get_asic_info()
            >>> print(f"ASIC: {asic.get('model')}")
        """
        logger.info("[PLATFORM] Fetching ASIC information")
        try:
            # Try to get ASIC from inventory
            inventory = await self.get_inventory()

            # Find ASIC entry in inventory
            for item_id, item_data in inventory.items():
                if "asic" in item_id.lower():
                    logger.info(f"[PLATFORM] ASIC found in inventory | id={item_id}")
                    return {
                        "id": item_id,
                        "details": item_data,
                    }

            # Fallback: get from platform base info
            platform_data = await self.get()
            asic_model = platform_data.get("asic-model")

            return {
                "model": asic_model,
                "source": "platform-base-info",
            }

        except Exception as e:
            logger.warning(f"[PLATFORM] Could not retrieve ASIC info | error={str(e)}")
            return {}

    # ==================== Environment Monitoring ====================

    async def get_temperature_sensors(self) -> dict[str, Any]:
        """
        Get all temperature sensor readings.

        Returns:
            dict[str, Any]: Temperature sensor data with current readings

        Example:
            >>> temps = await service.get_temperature_sensors()
            >>> for sensor_id, data in temps.items():
            ...     print(f"{sensor_id}: {data['current']}°C")
        """
        logger.info("[PLATFORM] Fetching temperature sensors")
        return await self.get("/environment/temperature")

    async def get_fan_status(self) -> dict[str, Any]:
        """
        Get cooling fan status and RPM.

        Returns:
            dict[str, Any]: Fan information including speed and state

        Example:
            >>> fans = await service.get_fan_status()
            >>> for fan_id, data in fans.items():
            ...     print(f"{fan_id}: {data['speed']} RPM")
        """
        logger.info("[PLATFORM] Fetching fan status")
        return await self.get("/environment/fan")

    async def get_psu_status(self) -> dict[str, Any]:
        """
        Get power supply unit (PSU) status.

        Returns:
            dict[str, Any]: PSU information including state and power metrics

        Example:
            >>> psus = await service.get_psu_status()
            >>> for psu_id, data in psus.items():
            ...     print(f"{psu_id}: {data['state']}")
        """
        logger.info("[PLATFORM] Fetching PSU status")
        return await self.get("/environment/psu")

    async def get_led_status(self) -> dict[str, Any]:
        """
        Get status of platform LEDs.

        Returns:
            dict[str, Any]: LED status information

        Example:
            >>> leds = await service.get_led_status()
            >>> for led_id, data in leds.items():
            ...     print(f"{led_id}: {data['state']}")
        """
        logger.info("[PLATFORM] Fetching LED status")
        return await self.get("/environment/led")

    async def get_voltage_status(self) -> dict[str, Any]:
        """
        Get voltage sensor readings.

        Returns:
            dict[str, Any]: Voltage sensor data with current readings

        Example:
            >>> voltages = await service.get_voltage_status()
            >>> for sensor_id, data in voltages.items():
            ...     print(f"{sensor_id}: {data['current']} V")
        """
        logger.info("[PLATFORM] Fetching voltage sensors")
        return await self.get("/environment/voltage")

    async def get_environment_summary(self) -> dict[str, Any]:
        """
        Get complete environment monitoring summary.

        Facade method that aggregates temperature, fan, and PSU data.

        Returns:
            dict containing:
              - temperature: All temperature sensors
              - fans: All fan status
              - psu: All PSU status

        Example:
            >>> env = await service.get_environment_summary()
            >>> print(f"Fans: {len(env['fans'])}, Temps: {len(env['temperature'])}")
        """
        logger.info("[PLATFORM] Fetching environment summary")

        # Fetch all environment data concurrently would be ideal,
        # but for now we'll do sequential calls
        environment = {
            "temperature": await self.get_temperature_sensors(),
            "fans": await self.get_fan_status(),
            "psu": await self.get_psu_status(),
            "voltage": await self.get_voltage_status(),
        }

        logger.info("[PLATFORM] Environment summary retrieved")
        return environment

    async def get_transceivers(self) -> dict[str, Any]:
        """
        NVUE 5.9 not supported.
        Get all transceiver (SFP/QSFP) information.

        Returns:
            dict[str, Any]: Transceiver details for all ports

        Example:
            >>> transceivers = await service.get_transceivers()
            >>> for port, data in transceivers.items():
            ...     print(f"{port}: {data.get('type')}")
        """
        logger.info("[PLATFORM] Fetching transceivers")
        return await self.get("/transceiver")

    async def get_transceiver(self, transceiver_id: str) -> dict[str, Any]:
        """
        NVUE 5.9 not supported.
        Get specific transceiver information.

        Args:
            transceiver_id: Transceiver/port identifier (e.g., 'swp1')

        Returns:
            dict[str, Any]: Transceiver details

        Example:
            >>> sfp = await service.get_transceiver("swp1")
            >>> print(sfp.get("vendor"), sfp.get("part-number"))
        """
        logger.info(f"[PLATFORM] Fetching transceiver | id={transceiver_id}")
        return await self.get_item(transceiver_id, sub_path="/transceiver")

    # ==================== Software/Firmware ====================

    async def get_software_installed(self) -> dict[str, Any]:
        """
        Get installed software packages.

        Returns:
            dict[str, Any]: Installed software information
        """
        logger.info("[PLATFORM] Fetching installed software")
        return await self.get("/software/installed")

    async def get_firmware_versions(self) -> dict[str, Any]:
        """
        Get firmware versions for platform components.

        Returns:
            dict[str, Any]: Firmware version information
        """
        logger.info("[PLATFORM] Fetching firmware versions")
        return await self.get("/firmware")
