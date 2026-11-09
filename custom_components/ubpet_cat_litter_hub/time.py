from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .box_config import empty_waste_bin_reminder_config, first_period_config
from .compat import description_is_frozen
from .const import DOMAIN
from .coordinator import UbpetDataUpdateCoordinator
from .entities import UbpetPeriodEntity, UbpetReminderEntity, setup_discovery, supported


@dataclass(frozen=description_is_frozen(TimeEntityDescription), kw_only=True)
class UbpetTimeDescription(TimeEntityDescription):
    config_list_key: str
    function_type: int
    boundary: str


TIME_ENTITIES = tuple(
    UbpetTimeDescription(
        key=f"{feature}_{boundary}",
        translation_key=f"{feature}_{boundary}",
        name=f"{label} {boundary}",
        icon=icon,
        entity_category=EntityCategory.CONFIG,
        config_list_key=source,
        function_type=function,
        boundary=boundary,
    )
    for feature, label, source, function, icon in (
        ("do_not_disturb", "Do not disturb", "disturbTimeConfigList", 1, "mdi:minus-circle-outline"),
        ("light_schedule", "Light schedule", "lightTimeConfigList", 0, "mdi:lightbulb"),
    )
    for boundary in ("start", "end")
)


def _clock_value(config, hour_key, minute_key):
    if not config:
        return None
    try:
        return time(*[int(config.get(key, 0)) for key in (hour_key, minute_key)])
    except (TypeError, ValueError, OverflowError):
        return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: UbpetDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    def build():
        entities: list[TimeEntity] = []
        for serial, item in coordinator.data.get("devices", {}).items():
            config = item.get("config", {})
            if empty_waste_bin_reminder_config(config):
                entities.append(UbpetEmptyWasteBinReminderTime(coordinator, coordinator.namespace, serial))
            for description in TIME_ENTITIES:
                if first_period_config(config, description.config_list_key) and supported(description.key, item):
                    entities.append(UbpetPeriodTime(coordinator, coordinator.namespace, serial, description))
        return entities

    setup_discovery(coordinator, entry, async_add_entities, build)


class UbpetPeriodTime(UbpetPeriodEntity, TimeEntity):
    entity_description: UbpetTimeDescription

    def __init__(
        self,
        coordinator: UbpetDataUpdateCoordinator,
        entry_id: str,
        serial: str,
        description: UbpetTimeDescription,
    ) -> None:
        super().__init__(coordinator)
        self._bind_box(entry_id, serial, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> time | None:
        side = self.entity_description.boundary
        return _clock_value(self._period_config, side + "TimeHour", side + "TimeMinute")

    async def async_set_value(self, value: time) -> None:
        boundary = self.entity_description.boundary
        await self._write_period(**{f"{boundary}_hour": value.hour, f"{boundary}_minute": value.minute})


EMPTY_WASTE_BIN_REMINDER_TIME = TimeEntityDescription(
    key="empty_waste_bin_reminder_time",
    name="Empty waste bin reminder time",
    icon="mdi:bell-ring-outline",
    translation_key="empty_waste_bin_reminder_time",
    entity_category=EntityCategory.CONFIG,
)


class UbpetEmptyWasteBinReminderTime(UbpetReminderEntity, TimeEntity):
    entity_description = EMPTY_WASTE_BIN_REMINDER_TIME

    def __init__(self, coordinator: UbpetDataUpdateCoordinator, entry_id: str, serial: str) -> None:
        super().__init__(coordinator)
        self._bind_box(entry_id, serial, self.entity_description.key)

    @property
    def native_value(self) -> time | None:
        return _clock_value(self._reminder_config, "timeHour", "timeMinute")

    async def async_set_value(self, value: time) -> None:
        await self._write_reminder(time_hour=value.hour, time_minute=value.minute)
