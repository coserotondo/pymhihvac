"""Provides a controller class for interacting with MHI HVAC systems.

This module defines the MHIHVACSystemController, which acts as a high-level
interface for communicating with MHI HVAC systems via the API. It provides
methods for fetching data, setting properties on individual units or groups,
managing the API session, and handling login and authentication.
"""

from json import JSONDecodeError
import logging
from typing import Any

from aiohttp import ClientError, ClientSession
from voluptuous import In

from .api import (
    ApiCallFailedException,
    LoginFailedException,
    MHIHVACLocalAPI,
    NoSessionCookieException,
)
from .const import (
    MHIFanAPI,
    MHIFanMode,
    MHIHVACMode,
    MHILockAPI,
    MHILouverAPI,
    MHIModeAPI,
    MHIOnOffAPI,
    MHIOnOffMode,
    MHISwingMode,
)
from .device import MHIHVACDeviceData
from .mappings import (
    HA_TO_API_FAN_MODE,
    HA_TO_API_FILTER_RESET,
    HA_TO_API_HVAC_MODE,
    HA_TO_API_LOCK_MODE,
    HA_TO_API_ONOFF_MODE,
    HA_TO_API_SWING_MODE,
)
from .utils import (
    InvalidTemperatureException,
    build_payload,
    format_exception,
    validate_properties,
    validate_temperature,
)

_LOGGER = logging.getLogger(__name__)


class MHIHVACSystemController:
    """Controller class to interact with the HVAC system API."""

    HA_TO_API_PROPERTY_MAPPINGS: dict[str, tuple[str, dict[Any, Any] | None]] = {
        "hvac_mode": ("Mode", HA_TO_API_HVAC_MODE),
        "fan_mode": ("Fan", HA_TO_API_FAN_MODE),
        "swing_mode": ("Louver", HA_TO_API_SWING_MODE),
        "onoff_mode": ("OnOff", HA_TO_API_ONOFF_MODE),
        "target_temperature": ("SetTemp", None),
        "lock_mode": ("Lock", HA_TO_API_LOCK_MODE),
        "filter_reset": ("FilterReset", HA_TO_API_FILTER_RESET),
    }

    API_PROPERTY_VALIDATORS: dict[str, Any] = {
        "Mode": In(MHIModeAPI),
        "OnOff": In(MHIOnOffAPI),
        "Fan": In(MHIFanAPI),
        "Louver": In(MHILouverAPI),
        "SetTemp": validate_temperature,
        "Lock": In(MHILockAPI),
        "FilterReset": In(["0", "1", 0, 1]),
    }

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the controller with the API address."""
        self.api: MHIHVACLocalAPI = MHIHVACLocalAPI(host, username, password, session)
        self._session_cookie: str | None = None

    @property
    def session_cookie(self) -> str | None:
        """Return the cookie of the session."""
        return self._session_cookie

    async def async_update_data(
        self,
        method: str,
        include_index: list[str] | None = None,
        include_groups: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Fetch the latest data from the API."""
        try:
            return await self.api.async_get_raw_data(
                method=method,
                include_index=include_index,
                include_groups=include_groups,
            )
        except (
            ClientError,
            TimeoutError,
            JSONDecodeError,
            ApiCallFailedException,
            LoginFailedException,
            NoSessionCookieException,
        ) as e:
            _LOGGER.error("Error updating data from API: %s", format_exception(e))
            raise
            # return None

    async def _async_set_group_property(
        self, group_no: str, payload: dict[str, Any]
    ) -> bool:
        """Set a generic property or properties for a given group number."""
        try:
            _ = await self.api.async_set_group_property(group_no, payload)
        except (ApiCallFailedException, ClientError, TimeoutError) as e:
            _LOGGER.error(
                "Error setting property '%s' for group %s: %s",
                payload,
                group_no,
                format_exception(e),
            )
            return False
        else:
            return True

    async def _async_set_all_property(self, payload: dict[str, Any]) -> bool:
        """Set a property or properties for all devices."""
        try:
            _ = await self.api.async_set_all_property(payload)
        except (ApiCallFailedException, ClientError, TimeoutError) as e:
            _LOGGER.error(
                "Error setting property '%s' for all groups: %s",
                payload,
                format_exception(e),
            )
            return False
        else:
            return True

    async def _set_device_property(
        self,
        device_data: MHIHVACDeviceData,
        ha_property: str | tuple[str, ...] | list[str],
        value: Any | tuple[Any, ...] | list[Any],
    ) -> bool:
        """Set one or more device properties.

        - If ha_property is a string, value must be a single value.
        - If ha_property is a tuple (or list), then value must be an iterable
          with the same length, where each element corresponds to a key.

        It uses the PROPERTY_MAPPINGS to convert each HA value to the proper API payload.
        """
        props = build_payload(
            ha_property, value, self.HA_TO_API_PROPERTY_MAPPINGS, _LOGGER
        )
        if props is None:
            return False

        try:
            payload = validate_properties(props, self.API_PROPERTY_VALIDATORS)
        except (ValueError, InvalidTemperatureException):
            return False

        if device_data.is_virtual:
            if device_data.is_all_devices_group:
                _LOGGER.debug(
                    "Setting properties %s to ALL devices (Group No: %s, Group Name: %s)",
                    payload,
                    device_data.group_no,
                    device_data.group_name,
                )
                return await self._async_set_all_property(payload)
            _LOGGER.debug(
                "Setting properties %s to virtual group (Group No: %s, Group Name: %s) - looping units",
                payload,
                device_data.group_no,
                device_data.group_name,
            )
            success: bool = True
            for unit in device_data.units:
                if unit.group_no is None:
                    _LOGGER.error("Unit group number is None for unit: %s", unit)
                    success = False
                    continue
                if not await self._async_set_group_property(unit.group_no, payload):
                    success = False
                    _LOGGER.error(
                        "Failed to set properties for unit Group No: %s, Group Name: %s",
                        unit.group_no,
                        unit.group_name,
                    )
            return success
        if device_data.group_no is None:
            _LOGGER.error("Device group number is None for device: %s", device_data)
            return False
        _LOGGER.debug(
            "Setting properties %s to unit (Group No: %s, Group Name: %s)",
            payload,
            device_data.group_no,
            device_data.group_name,
        )
        return await self._async_set_group_property(device_data.group_no, payload)

    async def set_device_property(
        self,
        device_data: MHIHVACDeviceData,
        properties: str | tuple[str, ...] | list[str],
        values: Any | tuple[Any, ...] | list[Any],
    ) -> bool:
        """Set one or more properties on a device.

        This method sets one or more properties on a given device, handling
        both single properties and multiple properties simultaneously. It
        delegates the actual setting to the internal _set_device_property
        method.
        """

        return await self._set_device_property(device_data, properties, values)

    async def async_set_hvac_set_mode(
        self, device_data: MHIHVACDeviceData, hvac_mode: MHIHVACMode
    ) -> bool:
        """Set HVAC mode for a device (unit or group) without altering current OnOff mode."""
        return await self._set_device_property(device_data, "hvac_mode", hvac_mode)

    async def async_set_hvac_mode(
        self, device_data: MHIHVACDeviceData, hvac_mode: MHIHVACMode
    ) -> bool:
        """Set HVAC mode for a device (unit or group) with automatic OnOff mode."""
        if hvac_mode == MHIHVACMode.OFF:
            return await self._set_device_property(
                device_data, "onoff_mode", MHIOnOffMode.OFF
            )
        return await self._set_device_property(
            device_data, ("hvac_mode", "onoff_mode"), (hvac_mode, MHIOnOffMode.ON)
        )

    async def async_turn_hvac_on(
        self, device_data: MHIHVACDeviceData, hvac_mode: MHIHVACMode | None = None
    ) -> bool:
        """Turn HVAC on for a device (unit or group)."""
        if hvac_mode is not None:
            return await self.async_set_hvac_mode(device_data, hvac_mode)
        return await self._set_device_property(
            device_data, "onoff_mode", MHIOnOffMode.ON
        )

    async def async_turn_hvac_off(self, device_data: MHIHVACDeviceData) -> bool:
        """Turn HVAC off for a device (unit or group)."""
        return await self._set_device_property(
            device_data, "onoff_mode", MHIOnOffMode.OFF
        )

    async def async_set_fan_mode(
        self, device_data: MHIHVACDeviceData, fan_mode: MHIFanMode
    ) -> bool:
        """Set fan mode for a device (unit or group)."""
        return await self._set_device_property(device_data, "fan_mode", fan_mode)

    async def async_set_swing_mode(
        self, device_data: MHIHVACDeviceData, swing_mode: MHISwingMode
    ) -> bool:
        """Set swing mode for a device (unit or group)."""
        return await self._set_device_property(device_data, "swing_mode", swing_mode)

    async def async_set_preset_mode(
        self,
        device_data: MHIHVACDeviceData,
        hvac_mode: MHIHVACMode,
        fan_mode: MHIFanMode,
        swing_mode: MHISwingMode,
        target_temperature: Any,
        onoff_mode: MHIOnOffMode | None = None,
    ) -> bool:
        """Set preset mode for a device (unit or group)."""
        properties = [
            "hvac_mode",
            "fan_mode",
            "swing_mode",
            "target_temperature",
        ]
        values = [
            hvac_mode,
            fan_mode,
            swing_mode,
            target_temperature,
        ]
        if onoff_mode is not None:
            properties.append("onoff_mode")
            values.append(onoff_mode)
        return await self._set_device_property(device_data, properties, values)

    async def async_set_target_temperature(
        self, device_data: MHIHVACDeviceData, temperature: Any
    ) -> bool:
        """Set target temperature for a device (unit or group)."""
        return await self._set_device_property(
            device_data, "target_temperature", temperature
        )

    async def async_set_rc_lock(
        self, device_data: MHIHVACDeviceData, lock_mode: MHILockAPI
    ) -> bool:
        """Set RC lock for a device (unit or group)."""
        return await self._set_device_property(device_data, "lock_mode", lock_mode)

    async def async_filter_reset(self, device_data: MHIHVACDeviceData) -> bool:
        """Set filter sign for a device (unit or group)."""
        return await self._set_device_property(device_data, "filter_reset", True)

    async def async_close_session(self) -> None:
        """Close the API client session."""
        await self.api.close_session()

    async def async_login(self) -> str:
        """Login to the HVAC system."""
        try:
            self._session_cookie = await self.api.async_login()
        except (
            LoginFailedException,
            NoSessionCookieException,
            ClientError,
            TimeoutError,
        ) as e:
            _LOGGER.error("Initial login failed: %s", format_exception(e))
            raise
        else:
            assert self._session_cookie is not None
            return self._session_cookie
