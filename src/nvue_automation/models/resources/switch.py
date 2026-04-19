from pydantic import BaseModel
from pydantic import Field


class ASIC(BaseModel):
    """ASIC information."""

    hostname: str = Field(..., description="Device hostname")
    model: str = Field(..., description="ASIC model name", examples="Spectrum")
    vendor: str = Field(..., description="ASIC vendor(manufacturer)", examples="Nvidia")
    model_id: str = Field(..., description="ASIC model identifier", examples="MT52132")
    ports: str = Field(..., description="port-layout by the ASIC", examples="48 x RJ45 & 4 x 100G-QSFP28")
    core: str = Field(..., description="ASIC core name")
    time: str = Field(..., description="Timestamp of the ASIC information", examples="3/30/2026 4:43 pm")


class Platform(BaseModel):
    """Platform hardware summary information."""

    hostname: str = Field(..., description="Device hostname")
    model: str = Field(..., description="Platform model name", examples="SN5600")
    vendor: str = Field(..., description="Platform vendor", examples="Nvidia")
    date: str = Field(..., description="Timestamp of the platform information", examples="3/30/2026")
    revision: str = Field(..., description="Platform hardware revision", examples="A5")
    number: str = Field(..., description="Platform hardware number", examples="MSN2201-CB2RC")
    mac: str = Field(..., description="Base MAC address of the platform", examples="00:1A:2B:3C:4D:5E")
    series: str = Field(..., description="Platform series name", examples="MT2546202642")
    time: str = Field(..., description="Timestamp of the platform information", examples="3/30/2026 4:43 pm")


class CPU(BaseModel):
    """CPU information."""

    hostname: str = Field(..., description="Device hostname")
    model: str = Field(..., description="CPU model name", examples="Intel(R) Atom(TM) C3338R")
    arch: str = Field(..., description="CPU architecture", examples="x86_64")
    nos: int = Field(..., description="Number of CPU cores", examples=8)
    max_freq: str = Field(..., description="CPU speed", examples="2.5 GHz")
    time: str = Field(..., description="Timestamp of the CPU information", examples="3/30/2026 4:43 pm")


class Memory(BaseModel):
    """Memory information."""

    hostname: str = Field(..., description="Device hostname")
    vendor: str = Field(..., description="Memory vendor", examples="Micron")
    name: str = Field(..., description="Memory name/model", examples="DIMM0BANK 0")
    serial_number: str = Field(..., description="Memory serial number", examples="D1DB56DF")
    size: str = Field(..., description="Memory size", examples="16 GB")
    speed: str = Field(..., description="Memory speed", examples="2666 MT/s")
    type: str = Field(..., description="Memory type", examples="DDR4")
    time: str = Field(..., description="Timestamp of the memory information", examples="3/30/2026 4:43 pm")


class Disk(BaseModel):
    """Disk information."""

    hostname: str = Field(..., description="Device hostname")
    vendor: str = Field(..., description="Disk vendor", examples="ATA")
    size: str = Field(..., description="Disk size", examples="512 GB")
    rev: str = Field(..., description="Disk revision", examples="2.5+")
    model: str = Field(..., description="Disk model name", examples="SFPC020GM1EC2TO-I-5E-51P-STD")
    name: str = Field(..., description="Disk name", examples="nvme0n1")
    transport: str = Field(..., description="Disk transport type", examples="nvme")
    type: str = Field(..., description="Disk type", examples="disk")
    time: str = Field(..., description="Timestamp of the disk information", examples="3/30/2026 4:43 pm")


class OperationSystem(BaseModel):
    """Operating system information."""

    hostname: str = Field(..., description="Device hostname")
    version: str = Field(..., description="Operating system version", examples="5.13.1")
    version_id: str = Field(..., description="Operating system version ID", examples="5.13.1")
    vendor: str = Field(..., description="Operating system vendor", examples="Ubuntu")
    platform: str = Field(..., description="Operating system platform", examples="CL")
    time: str = Field(..., description="Timestamp of the OS information", examples="3/30/2026 4:43 pm")
