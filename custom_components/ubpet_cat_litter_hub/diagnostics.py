"""Download sanitized, useful support data without account and pet identifiers."""

from __future__ import annotations

from .const import DOMAIN
from .privacy import redact

REDACTED = "REDACTED"
_redact = redact


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    # Serial numbers can also occur as dictionary keys; turn that mapping into a list.
    safe_data = {**data, "devices": list(data.get("devices", {}).values())}
    return {
        "entry": redact({"data": dict(entry.data), "options": dict(entry.options)}),
        "last_update_success": coordinator.last_update_success,
        "mqtt_connected": coordinator.transport.connected,
        "session_backoff": coordinator.transport.yielding,
        "data": redact(safe_data),
    }
