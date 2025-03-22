# pymhihvac

![PyPI](https://img.shields.io/pypi/v/pymhihvac)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A Python library for controlling Mitsubishi Heavy Industries (MHI) HVAC systems via their local API.

## Features

- **Full HVAC Control**:
  - Power on/off
  - Set temperature (18-30°C)
  - Adjust fan speeds (Low/Medium/High/Diffuse)
  - Control swing modes (Auto/Stop1-4)
  - Set HVAC modes (Cool/Dry/Fan/Heat)
- **Status Monitoring**:
  - Current temperature
  - Filter status
  - Remote control lock state
- **Virtual Groups**: Manage multiple units as a single entity
- **Async Support**: Built on `aiohttp` for efficient communication

## Installation

```bash
pip install pymhihvac
```
## Quick Start

```python
import asyncio
from pymhihvac import MHIHVACSystemController

async def main():
    # Initialize controller
    controller = MHIHVACSystemController(
        host="192.168.1.100",  # HVAC system IP
        username="admin",
        password="password"
    )
    
    # Login to API
    await controller.async_login()
    
    # Fetch all devices
    devices = await controller.async_update_data()
    
    # Control first device
    device = devices[0]
    print(f"Controlling: {device.group_name} ({device.group_no})")
    
    # Turn on cooling at 22°C
    await controller.async_set_hvac_mode(device, "cool")
    await controller.async_set_target_temperature(device, 22.0)

asyncio.run(main())
```
## Virtual Groups Configuration

Create virtual groups in a YAML configuration:
```yaml
virtual_groups:
  living_room:
    name: "Living Room Group"
    units: ["1", "2"]  # Group numbers from physical units
  entire_floor:
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

Method

Description

`async_login()`

Establish API session

`async_update_data()`

Fetch current device states

`async_set_hvac_mode(device, mode)`

Set HVAC mode

`async_set_target_temperature(device, temp)`

Set target temperature

`async_set_fan_mode(device, mode)`

Set fan speed

`async_set_swing_mode(device, mode)`

Set swing position

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

Home Assistant

MHI API Value

**HVAC Modes**

`off`

-

`cool`

`2`

`dry`

`3`

`fan_only`

`4`

`heat`

`5`

**Fan Modes**

`low`

`1`

`medium`

`2`

`high`

`3`

`diffuse`

`4`

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

MIT License - See  [LICENSE](https://license/)  for details.

----------

**Disclaimer**: This project is not affiliated with or endorsed by Mitsubishi Heavy Industries. Use at your own risk. Always ensure proper HVAC system configuration before deployment.