"""Provides data structures and functions for representing and parsing HVAC device data.

This module defines the MHIHVACDeviceData class for storing HVAC device
information, and the parse_raw_data function for creating these objects
from raw API data, including handling virtual groups of units.
"""

from dataclasses import dataclass, field
import logging
from typing import Any

from .const import (
    MHIFanAPI,
    MHIFanMode,
    MHIFilterSignAPI,
    MHIHVACMode,
    MHILockAPI,
    MHILockMode,
    MHILouverAPI,
    MHIModeAPI,
    MHIOnOffAPI,
    MHISwingMode,
)
from .mappings import (
    API_TO_HA_FAN_MODE,
    API_TO_HA_HVAC_MODE,
    API_TO_HA_LOCK_MODE,
    API_TO_HA_SWING_MODE,
)
from .utils import calculate_average, find_most_frequent

_LOGGER = logging.getLogger(__name__)


@dataclass
class MHIHVACDeviceData:
    """Represents the HVAC device data.

    This class stores the data for an HVAC device, including its
    status, settings, and group information. It handles both
    individual units and virtual groups of units.
    """

    raw_data: dict[str, Any] | None = None
    group_no: str | None = None
    group_name: str | None = None
    unit_group_nos: list[str] | None = None
    all_units: list["MHIHVACDeviceData"] | None = None
    is_virtual: bool = False
    all_real_unit_group_nos: list[str] | None = None
    on_off: MHIOnOffAPI | None = None
    mode: MHIModeAPI | None = None
    set_temp: float | None = None
    room_temp: float | None = None
    lock: MHILockAPI | None = None
    fan: MHIFanAPI | None = None
    louver: MHILouverAPI | None = None
    filter_sign: MHIFilterSignAPI | None = None
    units: list["MHIHVACDeviceData"] = field(default_factory=list, init=False)
    _all_real_unit_group_nos_internal: list[str] | None = field(
        default=None, init=False
    )

    def __post_init__(self) -> None:
        """Initialize the MHIHVACDeviceData object after default __init__.

        This method performs additional initialization steps after the default
        dataclass __init__ method. It initializes the units list and sets
        attributes based on whether the device is a virtual group or a real unit.
        """
        self.units: list[
            MHIHVACDeviceData
        ] = []  # Initialize units list with type annotation
        self._all_real_unit_group_nos_internal = (
            self.all_real_unit_group_nos
        )  # Store all_real_unit_group_nos

        if not self.is_virtual and self.raw_data:
            if self.group_name is None:
                self.group_name = self.raw_data.get("GroupName")
            if self.group_no is None:
                self.group_no = self.raw_data.get("GroupNo")
            raw_on_off = self.raw_data.get("OnOff")
            self.on_off = MHIOnOffAPI(raw_on_off) if raw_on_off is not None else None
            raw_mode = self.raw_data.get("Mode")
            self.mode = MHIModeAPI(raw_mode) if raw_mode is not None else None
            self.set_temp = self.raw_data.get("SetTemp")
            self.room_temp = self.raw_data.get("RoomTemp")
            raw_lock = self.raw_data.get("Lock")
            self.lock = MHILockAPI(raw_lock) if raw_lock is not None else None
            raw_fan = self.raw_data.get("Fan")
            self.fan = MHIFanAPI(raw_fan) if raw_fan is not None else None
            raw_louver = self.raw_data.get("Louver")
            self.louver = MHILouverAPI(raw_louver) if raw_louver is not None else None
            raw_filter_sign = self.raw_data.get("FilterSign")
            self.filter_sign = (
                MHIFilterSignAPI(raw_filter_sign)
                if raw_filter_sign is not None
                else None
            )
        elif self.is_virtual and self.all_units and self.unit_group_nos:
            self.units = [
                unit for unit in self.all_units if unit.group_no in self.unit_group_nos
            ]

    @property
    def hvac_mode(self) -> MHIHVACMode | None:
        """Returns the Home Assistant HVAC mode (aggregated for virtual groups)."""
        if self.is_virtual:
            active_modes = [
                unit.hvac_mode for unit in self.units if unit.on_off != MHIOnOffAPI.OFF
            ]
            return find_most_frequent(active_modes) if active_modes else MHIHVACMode.OFF
        # Real unit
        if self.on_off == MHIOnOffAPI.OFF:
            return MHIHVACMode.OFF
        return None if self.mode is None else API_TO_HA_HVAC_MODE.get(self.mode, None)

    @property
    def hvac_set_mode(self) -> MHIHVACMode | None:
        """Returns the Home Assistant HVAC set mode (aggregated for virtual groups)."""
        if self.is_virtual:
            set_modes = [
                unit.mode
                for unit in self.units  # if unit.on_off != MHIOnOffAPI.OFF
            ]
            active_mode = find_most_frequent(set_modes)
            return API_TO_HA_HVAC_MODE.get(active_mode, None) if set_modes else None
        # Real unit
        return None if self.mode is None else API_TO_HA_HVAC_MODE.get(self.mode, None)

    @property
    def fan_mode(self) -> MHIFanMode | None:
        """Returns the Home Assistant fan mode (aggregated for virtual groups)."""
        if self.is_virtual:
            fan_modes = [unit.fan_mode for unit in self.units]
            return find_most_frequent(fan_modes) if fan_modes else None
        # Real unit
        return None if self.fan is None else API_TO_HA_FAN_MODE.get(self.fan, None)

    @property
    def swing_mode(
        self,
    ) -> (
        MHISwingMode | None
    ):  # swing_mode might return a string according to API_TO_HA_SWING_MODE values
        """Returns the Home Assistant swing mode (aggregated for virtual groups)."""
        if self.is_virtual:
            swing_modes = [unit.swing_mode for unit in self.units]
            return find_most_frequent(swing_modes) if swing_modes else None
        # Real unit
        if self.louver is None:  # Add explicit None check for self.mode
            return None
        return API_TO_HA_SWING_MODE.get(self.louver, None)

    @property
    def target_temperature(self) -> float | None:
        """Returns the target temperature (averaged for virtual groups)."""
        if self.is_virtual:
            units_temps = [
                unit.target_temperature
                for unit in self.units
                if unit.target_temperature is not None
            ]
            return calculate_average(units_temps)
        # Real unit
        return float(self.set_temp) if self.set_temp is not None else None

    @property
    def current_temperature(self) -> float | None:
        """Returns the current temperature (averaged for virtual groups)."""
        if self.is_virtual:
            current_temps = [
                unit.current_temperature
                for unit in self.units
                if unit.current_temperature is not None
            ]
            return calculate_average(current_temps)
        # Real unit
        return float(self.room_temp) if self.room_temp is not None else None

    @property
    def rc_lock(self) -> bool:
        """Returns True if remote control is locked (True if any unit is locked in virtual group)."""
        if self.is_virtual:
            return any(unit.rc_lock for unit in self.units)
        # Real unit
        return self.lock == MHILockAPI.UNLOCKED

    @property
    def rc_lock_extended(self) -> MHILockMode | list[MHILockMode] | None:
        """Returns the lock state(s) if remote control is locked.

        For virtual groups, returns a list of MHILockMode values for each unit.
        For a real unit, returns a single MHILockMode value.
        """
        if self.is_virtual:
            if lock_modes := [
                unit.lock for unit in self.units if unit.lock is not None
            ]:
                # Map and filter out any None values from the mapping
                mapped_modes = [API_TO_HA_LOCK_MODE.get(lock) for lock in lock_modes]
                return list(
                    dict.fromkeys(mode for mode in mapped_modes if mode is not None)
                )
        # For a real unit, return the mapped mode or None if not found.
        return None if self.lock is None else API_TO_HA_LOCK_MODE.get(self.lock, None)

    @property
    def is_filter_sign(self) -> bool:
        """Returns True if filter needs attention (True if any unit needs attention in virtual group)."""
        if self.is_virtual:
            return any(unit.is_filter_sign for unit in self.units)
        # Real unit
        return self.filter_sign == MHIFilterSignAPI.DIRTY

    @property
    def is_all_devices_group(self) -> bool | None:
        """Returns True if this virtual group contains all real HVAC units."""
        if not self.is_virtual:
            return False  # Real units are never "all devices" groups
        if self._all_real_unit_group_nos_internal is None:
            return False  # Cannot determine if we don't have the list of all real unit group numbers
        if self.unit_group_nos:
            return set(self.unit_group_nos) == set(
                self._all_real_unit_group_nos_internal
            )  # Compare sets of group numbers
        return None

    # @property
    # def valid_hvac_modes(self) -> list[str] | None:
    #     """Return the valid HVAC modes for the device.

    #     This property returns the list of valid HVAC modes, which is
    #     stored internally after initialization.
    #     """
    #     return self._valid_hvac_modes

    def __repr__(self) -> str:
        """Return a string representation of the HVAC device data.

        This representation includes the group type (virtual or unit),
        the group name, and the group number.
        """
        group_type = "VirtualGroup" if self.is_virtual else "Unit"
        return f"<HVACDeviceData {group_type} {self.group_name} ({self.group_no})>"


def parse_raw_data(
    raw_data_list: list[dict[str, Any]],
    virtual_group_config: dict[str, Any] | None = None,
) -> list[MHIHVACDeviceData]:
    """Parse raw data from the API and returns a list of MHIHVACDeviceData objects.

    This function processes raw data representing HVAC devices and virtual groups,
    creating MHIHVACDeviceData objects for each. It handles both individual units
    and virtual groups, linking units to their respective groups.

    Args:
        raw_data_list: A list of dictionaries containing raw data for individual HVAC units.
        virtual_group_config: A dictionary containing configuration for virtual groups,
            where keys are group numbers and values are dictionaries with group settings
            (e.g., unit assignments, names). Defaults to None if no virtual groups are defined.
        hvac_modes_config: A list of valid HVAC modes. Defaults to None.

    Returns:
        A list of MHIHVACDeviceData objects representing all parsed HVAC devices
        (both individual units and virtual groups).

    """
    all_devices: list[MHIHVACDeviceData] = []  # Initialize as empty list with type hint
    real_unit_devices: list[
        MHIHVACDeviceData
    ] = []  # Initialize as empty list with type hint
    # Parse real units first
    for item in raw_data_list:
        unit_device = MHIHVACDeviceData(raw_data=item)
        real_unit_devices.append(unit_device)
        all_devices.append(unit_device)

    # Get group numbers of all real units, filtering out None values
    all_real_unit_group_nos: list[str] = [
        unit.group_no for unit in real_unit_devices if unit.group_no is not None
    ]  # Filter out None values and cast to str, cast removed

    # Parse virtual groups
    if virtual_group_config:
        virtual_groups_created_units = (
            set()
        )  # To track units in created virtual groups for duplicate check

        for group_no, group_cfg in virtual_group_config.items():
            unit_group_nos = group_cfg.get("units")
            if unit_group_nos == "all":  # 1) "all_units" keyword
                resolved_unit_group_nos = all_real_unit_group_nos[:]
            elif isinstance(unit_group_nos, list):
                # 2) Be sure the units in virtual_group_config exists, otherwise ignore the non existent units
                resolved_unit_group_nos = []
                for unit_no in unit_group_nos:
                    if unit_no in all_real_unit_group_nos:
                        resolved_unit_group_nos.append(unit_no)
                    else:
                        _LOGGER.warning(
                            "Virtual group '%s' unit '%s' not found and ignored",
                            group_cfg.get("name", group_no),
                            unit_no,
                        )
            else:
                _LOGGER.warning(
                    "Virtual group '%s' has invalid 'units' configuration. Skipping group",
                    group_cfg.get("name", group_no),
                )
                continue  # Skip to the next group config

            # 3) The virtual group has to have a minimum of 2 existent units
            resolved_unit_group_nos_not_none: list[str] = [
                unit_no for unit_no in resolved_unit_group_nos if unit_no is not None
            ]  # Ensure no None in resolved_unit_group_nos for length check
            if len(resolved_unit_group_nos_not_none) < 2:
                _LOGGER.warning(
                    "Virtual group '%s' has less than 2 valid units. Skipping group",
                    group_cfg.get("name", group_no),
                )
                continue  # Skip to the next group config

            # 4) Cannot have groups with exact the same units (no duplicate groups)
            current_group_units_set = frozenset(resolved_unit_group_nos_not_none)
            if current_group_units_set in virtual_groups_created_units:
                _LOGGER.warning(
                    "Virtual group '%s' has duplicate unit configuration as another virtual group. Skipping group",
                    group_cfg.get("name", group_no),
                )
                continue  # Skip duplicate groups
            virtual_groups_created_units.add(current_group_units_set)

            virtual_group_device = MHIHVACDeviceData(
                group_no=group_no,
                group_name=group_cfg.get("name", f"Group {group_no}"),
                unit_group_nos=resolved_unit_group_nos_not_none,
                all_units=real_unit_devices,
                is_virtual=True,
                all_real_unit_group_nos=resolved_unit_group_nos_not_none,  # Use the filtered list here as well
            )
            all_devices.append(virtual_group_device)

    return all_devices
