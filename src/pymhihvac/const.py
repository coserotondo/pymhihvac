"""Constants used in pymhihvac package."""

from enum import StrEnum
import logging

_LOGGER = logging.getLogger(__name__)

try:
    # Attempt to import Home Assistant constants.
    # Adjust the import path to match where your custom component's constants are defined.
    # Assuming your custom component's const.py defines HA_HVAC_MODE, HA_FAN_MODE, HA_SWING_MODE
    from homeassistant.components.climate import (
        FAN_DIFFUSE,
        FAN_HIGH,
        FAN_LOW,
        FAN_MEDIUM,
        HVACMode,
    )
    from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE

    MHI_STATE_UNAVAILABLE = STATE_UNAVAILABLE
    MHI_HVAC_MODE_OFF = HVACMode.OFF
    MHI_HVAC_MODE_COOL = HVACMode.COOL
    MHI_HVAC_MODE_DRY = HVACMode.DRY
    MHI_HVAC_MODE_FAN_ONLY = HVACMode.FAN_ONLY
    MHI_HVAC_MODE_HEAT = HVACMode.HEAT
    MHI_FAN_DIFFUSE = FAN_DIFFUSE
    MHI_FAN_HIGH = FAN_HIGH
    MHI_FAN_LOW = FAN_LOW
    MHI_FAN_MEDIUM = FAN_MEDIUM
    MHI_STATE_OFF = STATE_OFF
    MHI_STATE_ON = STATE_ON

except ImportError:
    _LOGGER.warning("Home Assistant constants not found. Using default mappings")

    MHI_STATE_UNAVAILABLE = "unavailable"
    MHI_HVAC_MODE_OFF = "off"
    MHI_HVAC_MODE_COOL = "cool"
    MHI_HVAC_MODE_DRY = "dry"
    MHI_HVAC_MODE_FAN_ONLY = "fan_only"
    MHI_HVAC_MODE_HEAT = "heat"
    MHI_FAN_DIFFUSE = "diffuse"
    MHI_FAN_HIGH = "high"
    MHI_FAN_LOW = "low"
    MHI_FAN_MEDIUM = "medium"
    MHI_STATE_OFF = "off"
    MHI_STATE_ON = "on"

MHI_STATE_LOCKED = "locked"
MHI_STATE_LOCKED_ONOFF = "locked_onoff"
MHI_STATE_LOCKED_MODE = "locked_mode"
MHI_STATE_LOCKED_TEMP = "locked_temp"
MHI_STATE_LOCKED_ONOFF_MODE = "locked_onoff_mode"
MHI_STATE_LOCKED_ONOFF_TEMP = "locked_onoff_temp"
MHI_STATE_LOCKED_MODE_TEMP = "locked_mode_temp"
MHI_STATE_UNLOCKED = "unlocked"
MHI_STATE_CLEAN = "clean"
MHI_STATE_DIRTY = "dirty"


class MHIHVACMode(StrEnum):
    """Subset of HVACMode for climate devices."""

    OFF = MHI_HVAC_MODE_OFF
    COOL = MHI_HVAC_MODE_COOL
    DRY = MHI_HVAC_MODE_DRY
    FAN_ONLY = MHI_HVAC_MODE_FAN_ONLY
    HEAT = MHI_HVAC_MODE_HEAT


class MHIHVACSetMode(StrEnum):
    """Subset of HVACMode for climate devices."""

    COOL = MHI_HVAC_MODE_COOL
    DRY = MHI_HVAC_MODE_DRY
    FAN_ONLY = MHI_HVAC_MODE_FAN_ONLY
    HEAT = MHI_HVAC_MODE_HEAT


class MHIModeAPI(StrEnum):
    """Mode for MHI HVAC devices."""

    COOL = "2"
    DRY = "3"
    FAN_ONLY = "4"
    HEAT = "5"


class MHIFanMode(StrEnum):
    """FAN mode for climate devices."""

    LOW = MHI_FAN_LOW
    MEDIUM = MHI_FAN_MEDIUM
    HIGH = MHI_FAN_HIGH
    DIFFUSE = MHI_FAN_DIFFUSE


class MHIFanAPI(StrEnum):
    """Fan mode for MHI HVAC devices."""

    LOW = "1"
    MEDIUM = "2"
    HIGH = "3"
    DIFFUSE = "4"


class MHISwingMode(StrEnum):
    """SWING mode for climate devices."""

    AUTO = "auto"
    STOP1 = "stop1"
    STOP2 = "stop2"
    STOP3 = "stop3"
    STOP4 = "stop4"


class MHILouverAPI(StrEnum):
    """Louver mode for MHI HVAC devices."""

    AUTO = "1"
    STOP1 = "2"
    STOP2 = "3"
    STOP3 = "4"
    STOP4 = "5"


class MHIOnOffMode(StrEnum):
    """OnOff mode for climate devices."""

    OFF = MHI_STATE_OFF
    ON = MHI_STATE_ON


class MHIOnOffAPI(StrEnum):
    """OnOff mode for MHI HVAC devices."""

    OFF = "1"
    ON = "2"


class MHILockMode(StrEnum):
    """Lock mode for MHI HVAC devices."""

    UNLOCKED = MHI_STATE_UNLOCKED
    LOCKED = MHI_STATE_LOCKED
    LOCKED_ONOFF = MHI_STATE_LOCKED_ONOFF
    LOCKED_MODE = MHI_STATE_LOCKED_MODE
    LOCKED_TEMP = MHI_STATE_LOCKED_TEMP
    LOCKED_ONOFF_MODE = MHI_STATE_LOCKED_ONOFF_MODE
    LOCKED_ONOFF_TEMP = MHI_STATE_LOCKED_ONOFF_TEMP
    LOCKED_MODE_TEMP = MHI_STATE_LOCKED_MODE_TEMP


class MHILockAPI(StrEnum):
    """Lock mode for MHI HVAC devices."""

    UNLOCKED = "111"
    LOCKED = "222"
    LOCKED_ONOFF = "211"
    LOCKED_MODE = "121"
    LOCKED_TEMP = "112"
    LOCKED_ONOFF_MODE = "221"
    LOCKED_ONOFF_TEMP = "212"
    LOCKED_MODE_TEMP = "122"


class MHIFilterSignMode(StrEnum):
    """FilterSign mode for MHI HVAC devices."""

    CLEAN = MHI_STATE_CLEAN
    DIRTY = MHI_STATE_DIRTY


class MHIFilterSignAPI(StrEnum):
    """FilterSign mode for MHI HVAC devices."""

    CLEAN = "0"
    DIRTY = "1"


MHI_HVAC_MODES = [cls.value for cls in MHIHVACMode]
MHI_HVAC_SET_MODES = [cls.value for cls in MHIHVACSetMode]
MHI_FAN_MODES = [cls.value for cls in MHIFanMode]
MHI_SWING_MODES = [cls.value for cls in MHISwingMode]
MHI_ONOFF_MODES = [cls.value for cls in MHIOnOffMode]
MHI_LOCK_MODES = [cls.value for cls in MHILockMode]
MHI_FILTER_SIGN_MODES = [cls.value for cls in MHIFilterSignMode]

DEFAULT_FAN_MODE = MHIFanMode.LOW
DEFAULT_HVAC_MODE = MHIHVACMode.OFF
DEFAULT_ONOFF_MODE = MHIOnOffMode.OFF
DEFAULT_SWING_MODE = MHISwingMode.AUTO

MIN_TEMP = 18
MAX_TEMP = 30

RAW_DATA_REQUEST_KEY_MAPPING: dict[str, dict[str, str]] = {
    "all": {"payload_key": "GetReqAllGroupData", "value_key": "GroupData"},
    "block": {"payload_key": "GetReqGroupData", "value_key": "FloorNo"},
}

RAW_DATA_RESPONSE_KEY_MAPPING: dict[str, dict[str, str]] = {
    "all": {"payload_key": "GetResAllGroupData", "value_key": "GroupData"},
    "block": {"payload_key": "GetResGroupData", "value_key": "FloorData"},
}

DEFAULT_RAW_DATA_REQUEST_METHOD = "all"
DEFAULT_RAW_DATA_REQUEST_INDEX = ["1"]
