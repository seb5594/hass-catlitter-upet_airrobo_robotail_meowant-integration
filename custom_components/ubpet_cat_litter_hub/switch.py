from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .box_config import WEEKDAY_BITS, empty_waste_bin_reminder_config, first_period_config, reminder_mask
from .compat import description_is_frozen, translated_error
from .const import DOMAIN
from .coordinator import UbpetDataUpdateCoordinator
from .entities import UbpetDeviceEntity, UbpetPeriodEntity, UbpetReminderEntity, setup_discovery, supported
from .writes import async_write


@dataclass(frozen=description_is_frozen(SwitchEntityDescription), kw_only=True)
class UbpetSwitchDescription(SwitchEntityDescription):
    config_list_key: str | None = None
    function_type: int | None = None


DEODORANT_ALERT = UbpetSwitchDescription(
    key="deodorant_alert",
    name="Deodorant alert",
    icon="mdi:air-filter",
    translation_key="deodorant_alert",
    entity_category=EntityCategory.CONFIG,
)

AUTO_CLEAN = UbpetSwitchDescription(
    key="auto_clean",
    name="Auto clean",
    icon="mdi:broom",
    translation_key="auto_clean",
    entity_category=EntityCategory.CONFIG,
)

EMPTY_WASTE_BIN_REMINDER = UbpetSwitchDescription(
    key="empty_waste_bin_reminder",
    name="Empty waste bin reminder",
    icon="mdi:bell-ring-outline",
    translation_key="empty_waste_bin_reminder",
    entity_category=EntityCategory.CONFIG,
)

PERIOD_SWITCHES: tuple[UbpetSwitchDescription, ...] = (
    UbpetSwitchDescription(
        key="do_not_disturb",
        name="Do not disturb",
        icon="mdi:minus-circle-outline",
        translation_key="do_not_disturb",
        entity_category=EntityCategory.CONFIG,
        config_list_key="disturbTimeConfigList",
        function_type=1,
    ),
    UbpetSwitchDescription(
        key="light_schedule",
        name="Light schedule",
        icon="mdi:lightbulb",
        translation_key="light_schedule",
        entity_category=EntityCategory.CONFIG,
        config_list_key="lightTimeConfigList",
        function_type=0,
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: UbpetDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    def build():
        entities: list[SwitchEntity] = []
        for serial, item in coordinator.data.get("devices", {}).items():
            entities.append(UbpetAutoCleanSwitch(coordinator, coordinator.namespace, serial))
            entities.append(UbpetDeodorantAlertSwitch(coordinator, coordinator.namespace, serial))
            config = item.get("config", {})
            if empty_waste_bin_reminder_config(config):
                entities.append(UbpetEmptyWasteBinReminderSwitch(coordinator, coordinator.namespace, serial))
                entities.extend(
                    UbpetReminderWeekdaySwitch(coordinator, coordinator.namespace, serial, day) for day in WEEKDAY_BITS
                )
            for description in PERIOD_SWITCHES:
                if first_period_config(config, description.config_list_key) and supported(description.key, item):
                    entities.append(UbpetPeriodSwitch(coordinator, coordinator.namespace, serial, description))
            entities.extend(
                UbpetFunctionSwitch(coordinator, coordinator.namespace, serial, function)
                for function in FUNCTION_SWITCHES
                if function.read(config) is not None
            )
        return entities

    setup_discovery(coordinator, entry, async_add_entities, build)


class UbpetBaseSwitch(UbpetDeviceEntity, SwitchEntity):
    def __init__(self, coordinator: UbpetDataUpdateCoordinator, entry_id: str, serial: str, key: str) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self._attr_unique_id = f"{entry_id}_{serial}_{key}"


class UbpetDeodorantAlertSwitch(UbpetBaseSwitch):
    entity_description = DEODORANT_ALERT

    def __init__(self, coordinator: UbpetDataUpdateCoordinator, entry_id: str, serial: str) -> None:
        super().__init__(coordinator, entry_id, serial, DEODORANT_ALERT.key)

    @property
    def is_on(self) -> bool | None:
        item = self._device_item
        if not item:
            return None
        value = item.get("deodorant", {}).get("alertSwitch")
        return None if value is None else value == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_deodorant_alert(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_deodorant_alert(False)

    async def _set_deodorant_alert(self, enabled: bool) -> None:
        await async_write(self.hass, self.coordinator.client.set_deodorant_alert, self._serial, enabled)
        self.coordinator.schedule_refresh(15)


class UbpetAutoCleanSwitch(UbpetBaseSwitch):
    entity_description = AUTO_CLEAN

    def __init__(self, coordinator: UbpetDataUpdateCoordinator, entry_id: str, serial: str) -> None:
        super().__init__(coordinator, entry_id, serial, AUTO_CLEAN.key)

    @property
    def is_on(self) -> bool | None:
        item = self._device_item
        if not item:
            return None
        value = item.get("config", {}).get("sensorSwitch")
        return None if value is None else value == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_auto_clean(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_auto_clean(False)

    async def _set_auto_clean(self, enabled: bool) -> None:
        item = self._device_item or {}
        lazy_time = item.get("config", {}).get("lazyTime")
        if lazy_time is None:
            raise translated_error("auto_clean_unknown", "Auto clean state is unknown; wait for a successful update")
        await async_write(
            self.hass,
            self.coordinator.client.set_auto_clean_enabled,
            self._serial,
            enabled,
            lazy_time,
        )
        self.coordinator.schedule_refresh(15)


class UbpetEmptyWasteBinReminderSwitch(UbpetReminderEntity, UbpetBaseSwitch):
    entity_description = EMPTY_WASTE_BIN_REMINDER

    def __init__(self, coordinator: UbpetDataUpdateCoordinator, entry_id: str, serial: str) -> None:
        super().__init__(coordinator, entry_id, serial, EMPTY_WASTE_BIN_REMINDER.key)

    @property
    def is_on(self) -> bool | None:
        value = (self._reminder_config or {}).get("openSwitch")
        return None if value is None else value == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._write_reminder(open_switch=1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._write_reminder(open_switch=0)


class UbpetReminderWeekdaySwitch(UbpetReminderEntity, UbpetBaseSwitch):
    """One switch per weekday; together they cover every combination the app offers."""

    def __init__(self, coordinator: UbpetDataUpdateCoordinator, entry_id: str, serial: str, day: str) -> None:
        key = f"reminder_{day}"
        super().__init__(coordinator, entry_id, serial, key)
        self._bit = WEEKDAY_BITS[day]
        self.entity_description = UbpetSwitchDescription(
            key=key,
            name=day.capitalize(),
            translation_key=key,
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        )

    @property
    def is_on(self) -> bool | None:
        reminder = self._reminder_config
        return None if reminder is None else bool(reminder_mask(reminder) & self._bit)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._write_days(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._write_days(False)

    async def _write_days(self, enabled: bool) -> None:
        reminder = self._reminder_config
        if reminder is None:
            return
        mask = reminder_mask(reminder)
        await self._write_reminder(option_int=mask | self._bit if enabled else mask & ~self._bit)


class UbpetPeriodSwitch(UbpetPeriodEntity, UbpetBaseSwitch):
    entity_description: UbpetSwitchDescription

    def __init__(
        self,
        coordinator: UbpetDataUpdateCoordinator,
        entry_id: str,
        serial: str,
        description: UbpetSwitchDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, serial, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        value = (self._period_config or {}).get("openSwitch")
        return None if value is None else value == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._write_period(open_switch=1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._write_period(open_switch=0)


@dataclass(frozen=True)
class FunctionSwitch:
    """A box setting that is switched through the ``switch/update`` endpoint."""

    key: str
    function_type: int
    read: Callable[[dict[str, Any]], bool | None]  # allConfig -> state, None when the box lacks the setting


def _flag(field: str) -> Callable[[dict[str, Any]], bool | None]:
    return lambda config: None if config.get(field) is None else config[field] == 1


def _notify_flag(notify_type: int) -> Callable[[dict[str, Any]], bool | None]:
    def read(config: dict[str, Any]) -> bool | None:
        entry = next(
            (e for e in config.get("notifyConfigList") or [] if isinstance(e, dict) and e.get("type") == notify_type),
            None,
        )
        return None if entry is None else entry.get("openSwitch") == 1

    return read


FUNCTION_SWITCHES = (
    FunctionSwitch("child_lock", 0, _flag("controlBoardSwitch")),
    FunctionSwitch("foreign_object_detection", 1, _notify_flag(1)),
    FunctionSwitch("shake_mode", 6, _flag("litterType")),
    FunctionSwitch("box_full_alert", 7, _flag("boxFullAlertSwitch")),
)


class UbpetFunctionSwitch(UbpetBaseSwitch):
    def __init__(self, coordinator, entry_id, serial, function: FunctionSwitch):
        super().__init__(coordinator, entry_id, serial, function.key)
        self._function = function
        self.entity_description = UbpetSwitchDescription(
            key=function.key,
            name=function.key.replace("_", " ").capitalize(),
            translation_key=function.key,
            entity_category=EntityCategory.CONFIG,
        )

    @property
    def is_on(self):
        return self._function.read(self._box_config)

    async def async_turn_on(self, **kwargs):
        await self._set(True)

    async def async_turn_off(self, **kwargs):
        await self._set(False)

    async def _set(self, enabled):
        await async_write(
            self.hass, self.coordinator.client.set_function_switch, self._serial, self._function.function_type, enabled
        )
        self.coordinator.schedule_refresh(15)
