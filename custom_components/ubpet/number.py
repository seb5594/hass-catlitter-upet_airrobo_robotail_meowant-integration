from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .compat import DeviceInfo, serial_info
from .const import DOMAIN
from .coordinator import UbpetDataUpdateCoordinator
from .entities import CatAvailability, DeviceAvailability, setup_discovery
from .writes import async_write

AUTO_CLEAN_DELAY = NumberEntityDescription(
    key="auto_clean_delay",
    name="Auto clean delay",
    icon="mdi:broom",
    translation_key="auto_clean_delay",
    native_min_value=1,
    native_max_value=60,
    native_step=1,
    native_unit_of_measurement=UnitOfTime.MINUTES,
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: UbpetDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    def build():
        entities: list[NumberEntity] = []
        for serial in coordinator.data.get("devices", {}):
            entities.append(UbpetAutoCleanDelayNumber(coordinator, entry.entry_id, serial))
        for cat in coordinator.data.get("cats", []):
            if cat.get("catInfoId") is not None:
                entities.append(UbpetCatThresholdNumber(coordinator, entry.entry_id, str(cat["catInfoId"])))
        for serial, item in coordinator.data.get("devices", {}).items():
            if item.get("box_use_times", {}).get("boxFullMax"):
                entities.append(UbpetWasteThresholdNumber(coordinator, entry.entry_id, serial))
        return entities

    setup_discovery(coordinator, entry, async_add_entities, build)


class UbpetAutoCleanDelayNumber(DeviceAvailability, CoordinatorEntity[UbpetDataUpdateCoordinator], NumberEntity):
    _attr_mode = NumberMode.SLIDER
    entity_description = AUTO_CLEAN_DELAY

    def __init__(self, coordinator: UbpetDataUpdateCoordinator, entry_id: str, serial: str) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self._attr_unique_id = f"{entry_id}_{serial}_auto_clean_delay"

    @property
    def device_info(self) -> DeviceInfo:
        item = self.coordinator.data.get("devices", {}).get(self._serial, {})
        device = item.get("device", {})
        return DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            manufacturer=self.coordinator.provider_label,
            name=device.get("deviceName") or self._serial,
            **serial_info(self._serial),
        )

    @property
    def native_value(self) -> int | float | None:
        item = self.coordinator.data.get("devices", {}).get(self._serial)
        if not item:
            return None
        return _seconds_to_minutes(item.get("config", {}).get("lazyTime"))

    async def async_set_native_value(self, value: float) -> None:
        minutes = int(round(value))
        enabled = self.coordinator.data.get("devices", {}).get(self._serial, {}).get("config", {}).get("sensorSwitch")
        if enabled not in (0, 1):
            raise HomeAssistantError("Auto clean state is unknown; wait for a successful update")
        await async_write(
            self.hass,
            self.coordinator.client.set_auto_clean_delay,
            self._serial,
            minutes,
            enabled == 1,
        )
        self.coordinator.schedule_refresh(15)


def _seconds_to_minutes(value: Any) -> int | float | None:
    if value is None:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    minutes = seconds / 60
    return int(minutes) if minutes.is_integer() else minutes


class UbpetCatThresholdNumber(CatAvailability, CoordinatorEntity[UbpetDataUpdateCoordinator], NumberEntity):
    _attr_mode = NumberMode.BOX
    entity_description = NumberEntityDescription(
        key="cat_poo_duration_threshold",
        name="Poo duration threshold (estimate)",
        translation_key="cat_poo_duration_threshold",
        icon="mdi:timer-cog-outline",
        entity_category=EntityCategory.CONFIG,
        native_min_value=10,
        native_max_value=150,
        native_step=1,
        native_unit_of_measurement="s",
    )

    def __init__(self, coordinator, entry_id, cat_id):
        super().__init__(coordinator)
        self._cat_id = cat_id
        self._attr_unique_id = f"{entry_id}_cat_{cat_id}_poo_duration_threshold"

    @property
    def _cat_data(self):
        return next(
            (cat for cat in (self.coordinator.data or {}).get("cats", []) if str(cat.get("catInfoId")) == self._cat_id),
            None,
        )

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.cat_identifier(self._cat_id))},
            manufacturer=self.coordinator.provider_label,
            name=(self._cat_data or {}).get("nickname") or f"Cat {self._cat_id}",
        )

    @property
    def native_value(self):
        return self.coordinator.cat_poo_duration_threshold(self._cat_id)

    async def async_set_native_value(self, value):
        await self.coordinator.async_set_cat_poo_duration_threshold(self._cat_id, value)


class UbpetWasteThresholdNumber(UbpetAutoCleanDelayNumber):
    _attr_mode = NumberMode.BOX
    entity_description = NumberEntityDescription(
        key="box_full_alert_threshold",
        name="Waste bin full after",
        translation_key="box_full_alert_threshold",
        icon="mdi:delete-alert",
        entity_category=EntityCategory.CONFIG,
        native_min_value=1,
        native_max_value=100,
        native_step=1,
    )

    def __init__(self, coordinator, entry_id, serial):
        super().__init__(coordinator, entry_id, serial)
        self._attr_unique_id = f"{entry_id}_{serial}_box_full_alert_threshold"

    @property
    def native_max_value(self):
        return self.coordinator.data["devices"][self._serial]["box_use_times"].get("boxFullMax", 100)

    @property
    def native_value(self):
        return self.coordinator.data["devices"][self._serial]["box_use_times"].get("boxFullAlert")

    async def async_set_native_value(self, value):
        if not 1 <= value <= self.native_max_value or value != int(value):
            raise ValueError("Threshold exceeds reported capacity")
        await async_write(self.hass, self.coordinator.client.set_box_full_alert, self._serial, int(value))
        self.coordinator.schedule_refresh(15)
