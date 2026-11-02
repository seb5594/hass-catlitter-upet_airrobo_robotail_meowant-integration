"""Translate vendor setting failures into actionable Home Assistant errors."""

from homeassistant.exceptions import HomeAssistantError

from .api import UbpetApiError


async def async_write(hass, method, *args):
    try:
        return await hass.async_add_executor_job(method, *args)
    except UbpetApiError as err:
        if err.status == 403 or (
            isinstance(err.payload, dict)
            and err.payload.get("code") == 500
            and any(word in str(err.payload.get("message", "")).casefold() for word in ("permission", "权限"))
        ):
            raise HomeAssistantError("This setting requires permission from the device owner") from err
        raise HomeAssistantError(str(err)) from err
    except OSError as err:
        raise HomeAssistantError("Could not reach the vendor while changing this setting") from err
