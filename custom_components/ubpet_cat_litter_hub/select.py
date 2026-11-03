from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .box_config import REMINDER_PRESETS, empty_waste_bin_reminder_config, mask_preset, reminder_mask
from .const import DOMAIN
from .coordinator import UbpetDataUpdateCoordinator
from .entities import UbpetReminderEntity, setup_discovery

EMPTY_WASTE_BIN_REMINDER_DAYS = SelectEntityDescription(
    key="empty_waste_bin_reminder_days_select",
    name="Empty waste bin reminder days",
    icon="mdi:calendar-week",
    translation_key="empty_waste_bin_reminder_days_select",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: UbpetDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    def build():
        return [
            UbpetEmptyWasteBinReminderDaysSelect(coordinator, coordinator.namespace, serial)
            for serial, item in coordinator.data.get("devices", {}).items()
            if empty_waste_bin_reminder_config(item.get("config", {}))
        ]

    setup_discovery(coordinator, entry, async_add_entities, build)


class UbpetEmptyWasteBinReminderDaysSelect(UbpetReminderEntity, SelectEntity):
    """Preset weekdays for the empty-bin reminder; any other combination is set with the weekday switches."""

    entity_description = EMPTY_WASTE_BIN_REMINDER_DAYS
    _attr_options = list(REMINDER_PRESETS)

    def __init__(self, coordinator: UbpetDataUpdateCoordinator, namespace: str, serial: str) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self._attr_unique_id = f"{namespace}_{serial}_empty_waste_bin_reminder_days_select"

    @property
    def current_option(self) -> str | None:
        reminder = self._reminder_config
        if reminder is None:
            return None
        preset = mask_preset(reminder_mask(reminder))
        return preset if preset in REMINDER_PRESETS else None

    async def async_select_option(self, option: str) -> None:
        await self._write_reminder(option_int=REMINDER_PRESETS[option])
