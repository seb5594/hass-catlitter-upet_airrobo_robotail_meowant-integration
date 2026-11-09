from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .box_config import seconds_to_minutes
from .compat import translated_error
from .const import DOMAIN
from .coordinator import UbpetDataUpdateCoordinator
from .entities import UbpetCatEntity, UbpetDeviceEntity, setup_discovery
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
            entities.append(UbpetAutoCleanDelayNumber(coordinator, coordinator.namespace, serial))
        for cat in coordinator.data.get("cats", []):
            if cat.get("catInfoId") is not None:
                entities.append(UbpetCatThresholdNumber(coordinator, coordinator.namespace, str(cat["catInfoId"])))
        for serial, item in coordinator.data.get("devices", {}).items():
            if item.get("box_use_times", {}).get("boxFullMax"):
                entities.append(UbpetWasteThresholdNumber(coordinator, coordinator.namespace, serial))
        return entities

    setup_discovery(coordinator, entry, async_add_entities, build)


class UbpetAutoCleanDelayNumber(UbpetDeviceEntity, NumberEntity):
    _attr_mode = NumberMode.SLIDER
    entity_description = AUTO_CLEAN_DELAY

    def __init__(self, coordinator: UbpetDataUpdateCoordinator, entry_id: str, serial: str) -> None:
        super().__init__(coordinator)
        self._bind_box(entry_id, serial, self.entity_description.key)

    @property
    def native_value(self) -> int | float | None:
        return seconds_to_minutes(self._box_config.get("lazyTime"))

    async def async_set_native_value(self, value: float) -> None:
        minutes = int(round(value))
        enabled = self._box_config.get("sensorSwitch")
        if enabled not in (0, 1):
            raise translated_error("auto_clean_unknown", "Auto clean state is unknown; wait for a successful update")
        await async_write(
            self.hass,
            self.coordinator.client.set_auto_clean_delay,
            self._serial,
            minutes,
            enabled == 1,
        )
        self.coordinator.schedule_refresh(15)


class UbpetCatThresholdNumber(UbpetCatEntity, NumberEntity):
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
        self._bind_cat(entry_id, cat_id, "poo_duration_threshold")

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

    @property
    def native_max_value(self):
        return self.coordinator.data["devices"][self._serial]["box_use_times"].get("boxFullMax", 100)

    @property
    def native_value(self):
        return self.coordinator.data["devices"][self._serial]["box_use_times"].get("boxFullAlert")

    async def async_set_native_value(self, value):
        if not 1 <= value <= self.native_max_value or value != int(value):
            raise translated_error("threshold_exceeds_capacity", "Threshold exceeds reported capacity")
        await async_write(self.hass, self.coordinator.client.set_box_full_alert, self._serial, int(value))
        self.coordinator.schedule_refresh(15)
