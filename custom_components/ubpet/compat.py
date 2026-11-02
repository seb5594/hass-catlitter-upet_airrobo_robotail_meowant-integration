"""Small API bridges for older supported Home Assistant releases."""

from __future__ import annotations

import inspect

from homeassistant.helpers import device_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

try:
    from homeassistant.helpers.device_registry import DeviceInfo as DeviceInfo
except ImportError:
    from homeassistant.helpers.entity import DeviceInfo as DeviceInfo

SUPPORTS_ALWAYS_UPDATE = "always_update" in inspect.signature(DataUpdateCoordinator.__init__).parameters
SUPPORTS_EXPLICIT_ENTRY = "config_entry" in inspect.signature(DataUpdateCoordinator.__init__).parameters
_SUPPORTS_SERIAL = "serial_number" in inspect.signature(device_registry.DeviceRegistry.async_get_or_create).parameters


def description_is_frozen(base):
    return getattr(getattr(base, "__dataclass_params__", None), "frozen", True)


def serial_info(serial):
    return {"serial_number": serial} if _SUPPORTS_SERIAL else {}


def start_reauth(hass, entry):
    if method := getattr(entry, "async_start_reauth", None):
        method(hass)
    else:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                entry.domain, context={"source": "reauth", "entry_id": entry.entry_id}, data=dict(entry.data)
            )
        )
