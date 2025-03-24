# pymhihvac

![PyPI](https://img.shields.io/pypi/v/pymhihvac)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A Python library for controlling Mitsubishi Heavy Industries (MHI) HVAC systems via their local API using a SC-SL4 central control unit. Built especially for Home Assistant, enable the creation of climate, sensor and binary sensor entities. It can also be used standalone.

## Features

- **Full HVAC Control**:
  - Power on/off
  - Set temperature (18-30°C)
  - Adjust fan speeds (Low/Medium/High/Diffuse)
  - Control swing modes (Auto/Stop1-4)
  - Set HVAC modes (Cool/Dry/Fan/Heat/Fan Only)
- **Status Monitoring**:
  - Current room temperature
  - Filter status
  - Remote control lock state
- **Management**
  - Filter reset
- **Virtual Groups**: Manage multiple units as a single entity
- **Async Support**: Built on `aiohttp` for efficient communication

## Installation

```bash
pip install pymhihvac
```
## Quick Start

```python
import asyncio
from pymhihvac.controller import MHIHVACSystemController
from pymhihvac.device import MHIHVACDeviceData

async def main():
    # Initialize controller
    controller = MHIHVACSystemController(
        host="192.168.1.100",  # HVAC system IP
        username="admin",
        password="password"
    )

    # Login to API
    await controller.async_login()

    # Fetch raw_data devices
    raw_data = await controller.async_update_data(
      method="all",               # "all" (Default) = all valid units, "block" = "units in configured blocks"
      include_index="['1','2']",  # (Optional) The index of the blocks to include
      include_groups="['1','2']", # (Optional) The 'GroupNo' of the units to include
    )

    # Fetch all devices and virtual groups from API raw_data
    devices_data: list[
        MHIHVACDeviceData
    ] = parse_raw_data(
        raw_data_list,
        virtual_group_config,
    )

    # Control first device
    device = devices[0]
    print(f"Controlling: {device.group_name} ({device.group_no})")

    # Turn on cooling at 22°C
    await controller.async_set_hvac_mode(device, "cool")
    await controller.async_set_target_temperature(device, 22.0)

asyncio.run(main())
```
## Configuration (Example)

Optionally you can create a YAML to store configuration and use `yaml.load(...)` to build a dictionary:
```yaml
configuration:
  data_fetching:
    method: "all"
    include_index: ["1", "2"]
    include_groups: ["1", "2"]
  virtual_groups:
    129:
      name: "Living Room Group"
      units: ["1", "2"]  # Group numbers from physical units
    130:
      name: "Entire Floor"
      units: "all"       # Include all available units


```
## API Reference

### Core Classes

#### `MHIHVACSystemController`

Main interface for HVAC communication:

```python
controller = MHIHVACSystemController(
    host: str,          # HVAC system IP/hostname
    username: str,      # API username
    password: str,      # API password
    session: ClientSession = None  # Optional aiohttp session
)
```
Key Methods:

|Method|Description|
|--|--|
|`async_login()`|Establish API session|
|`async_update_data()`|Fetch current device states|
|`async_set_hvac_mode(device, mode)`|Set HVAC mode with auto On/Off|
|`async_set_hvac_set_mode(device, mode)`|Set HVAC mode|
|`async_turn_hvac_on (device)`|Turn HVAC on|
|`async_turn_hvac_off(device)`|Turn HVAC off|
|`async_set_target_temperature(device, temp)`|Set target temperature|
|`async_set_fan_mode(device, mode)`|Set fan speed|
|`async_set_swing_mode(device, mode)`|Set swing position|
|`async_set_rc_lock(device,mode)`|Set the RC lock mode|
|`async_filter_reset()`|Reset the Filter Signal|
|`set_device_property(device,properties,values)`|Set any properties|
|`async_close_session()`|Close the session if not passed to the controller|

#### `MHIHVACDeviceData`
```python
Dataclass representing HVAC unit/group:
@dataclass
class MHIHVACDeviceData:
    group_no: str | None          # Physical group number
    group_name: str | None        # Display name
    is_virtual: bool              # True for virtual groups
    current_temperature: float | None
    target_temperature: float | None
    hvac_mode: str | None         # Current operation mode
    fan_mode: str | None          # Current fan speed
    swing_mode: str | None        # Current swing position
    is_filter_sign: bool          # Filter needs maintenance
    rc_lock: bool                 # Remote control locked
```
### Mode Mappings
**HVAC Modes:**
|Home Assistant |MHI API Value|
|:--:|:--:|
|`off`|-|
|`cool`|`2`|
|`dry`|`3`|
|`fan_only`|`4`|
|`heat`|`5`|

**Fan Modes:**
|Home Assistant |MHI API Value|
|:--:|:--:|
|`low`|`1`|
|`medium`|`2`|
|`high`|`3`|
|`diffuse`|`4`|

**Swing Modes:**
|Home Assistant |MHI API Value|
|:--:|:--:|
|`auto`|`1`|
|`stop1`|`2`|
|`stop2`|`3`|
|`stop3`|`4`|
|`stop4`|`5`|

**Filter Sign:**
|Home Assistant |MHI API Value|
|:--:|:--:|
|`clean`|`0`|
|`dirty`|`1`|

**RC Lock:**
|Home Assistant |MHI API Value|
|:--:|:--:|
|`locked`|`222`|
|`unlocked`|`111`|


## Requirements

-   Python 3.9+

-   aiohttp >= 3.8.0

-   voluptuous >= 0.13.0


## Contributing

1.  Fork the repository

2.  Create a feature branch (`git checkout -b feature/your-feature`)

3.  Commit changes (`git commit -am 'Add awesome feature'`)

4.  Push to branch (`git push origin feature/your-feature`)

5.  Open a Pull Request


## License

[MIT](https://choosealicense.com/licenses/mit/)

----------

**Disclaimer**: This project is not affiliated with or endorsed by Mitsubishi Heavy Industries. Use at your own risk. Always ensure proper HVAC system configuration before deployment.
