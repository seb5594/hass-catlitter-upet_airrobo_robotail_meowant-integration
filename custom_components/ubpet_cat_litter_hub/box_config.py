"""Pure helpers that read a box's ``allConfig`` payload. No Home Assistant imports."""

from __future__ import annotations

from typing import Any

REMINDER_NOTIFY_TYPE = 4
WEEKDAY_BITS: dict[str, int] = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 4,
    "thursday": 8,
    "friday": 16,
    "saturday": 32,
    "sunday": 64,
}
# Preset names double as translation keys, so the labels follow the Home Assistant language.
REMINDER_PRESETS: dict[str, int] = {"off": 0, "every_day": 127, "weekdays": 31, "weekend": 96}
CUSTOM_PRESET = "custom"


def empty_waste_bin_reminder_config(config: dict[str, Any]) -> dict[str, Any] | None:
    """The empty-bin reminder lives in ``notifyConfigList`` as notification type 4."""
    for item in config.get("notifyConfigList") or []:
        if (
            isinstance(item, dict)
            and item.get("type") == REMINDER_NOTIFY_TYPE
            and item.get("notifyConfigId") is not None
        ):
            return item
    return None


def first_period_config(config: dict[str, Any], list_key: str | None) -> dict[str, Any] | None:
    periods = config.get(list_key) if list_key else None
    if not isinstance(periods, list) or not periods or not isinstance(periods[0], dict):
        return None
    return periods[0]


def period_config_id(period: dict[str, Any]) -> int | None:
    for key in ("configId", "disturbTimeConfigId", "lightTimeConfigId"):
        if (value := period.get(key)) is not None:
            return value
    return None


def reminder_mask(reminder: dict[str, Any]) -> int:
    try:
        return int(reminder.get("period") or 0) & REMINDER_PRESETS["every_day"]
    except (TypeError, ValueError):
        return 0


def mask_days(mask: int) -> list[str]:
    return [day for day, bit in WEEKDAY_BITS.items() if mask & bit]


def mask_preset(mask: int) -> str:
    return next((name for name, value in REMINDER_PRESETS.items() if value == mask), CUSTOM_PRESET)


def effective_work_state(mode: str | None, state: str | None) -> str | None:
    """Some boxes sit in mode IDLE while reporting RUNNING; the official app treats that as idle.

    Without this, every start command stays disabled on such a box (CrazzyBerg/upet-hass#3).
    BLOCKED and PAUSED are never rewritten.
    """
    return "PENDING" if mode == "IDLE" and state == "RUNNING" else state


def box_value(box: dict[str, Any], group: str, field: str) -> Any:
    values = box.get(group)
    return values.get(field) if isinstance(values, dict) else None


def seconds_to_minutes(value: Any) -> float | None:
    try:
        return float(value) / 60
    except (TypeError, ValueError, OverflowError):
        return None
