"""Translate vendor setting failures into actionable Home Assistant errors."""

from .api import UbpetApiError
from .compat import translated_error


async def async_write(hass, method, *args):
    try:
        return await hass.async_add_executor_job(method, *args)
    except UbpetApiError as err:
        if err.status == 403 or (
            isinstance(err.payload, dict)
            and err.payload.get("code") == 500
            and any(word in str(err.payload.get("message", "")).casefold() for word in ("permission", "权限"))
        ):
            raise translated_error(
                "permission_required", "This setting requires permission from the device owner"
            ) from err
        raise translated_error("api_error", str(err), detail=str(err)) from err
    except OSError as err:
        raise translated_error("vendor_unreachable", "Could not reach the vendor while changing this setting") from err
