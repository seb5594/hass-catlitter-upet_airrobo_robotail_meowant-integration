from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .box_config import box_value
from .compat import description_is_frozen
from .const import DOMAIN
from .coordinator import UbpetDataUpdateCoordinator
from .entities import UbpetDeviceEntity, keep_or_supported, setup_discovery
from .history import waste_full


@dataclass(frozen=description_is_frozen(BinarySensorEntityDescription), kw_only=True)
class UbpetBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


def _read_status(group, field, *, as_switch=False):
    def extract(box):
        value = box_value(box, group, field)
        return value == 1 if as_switch and value is not None else value

    return extract


BINARY_SENSORS = tuple(
    UbpetBinarySensorDescription(
        key=key, translation_key=key, name=name, icon=icon,
        entity_category=EntityCategory.DIAGNOSTIC, value_fn=_read_status(group, field, as_switch=flag),
    )
    for key, name, icon, group, field, flag in (
        ("online", "Online", "mdi:wifi", "online", "online", False),
        ("deodorant_expired", "Deodorant expired", "mdi:air-filter", "deodorant", "expired", False),
        ("sensor_switch", "Sensor enabled", "mdi:motion-sensor", "config", "sensorSwitch", True),
        ("camera_switch", "Camera enabled", "mdi:camera", "config", "cameraSwitch", True),
        ("control_board_switch", "Child lock", "mdi:lock", "config", "controlBoardSwitch", True),
    )
)


def _state_test(item, field, test):
    value = item.get("mqtt_state", {}).get(field)
    return test(value) if value is not None else None


BINARY_SENSORS += tuple(
    UbpetBinarySensorDescription(
        key=key,
        name=name,
        translation_key=key,
        device_class=kind,
        entity_category=category,
        value_fn=lambda item, field=field, test=test: _state_test(item, field, test),
    )
    for key, name, field, test, kind, category in (
        ("cat_inside", "Cat inside", "cat_inside", bool, BinarySensorDeviceClass.OCCUPANCY, None),
        ("cat_nearby", "Cat nearby", "foreign_state", lambda v: v == 1, BinarySensorDeviceClass.OCCUPANCY, None),
        ("cover_open", "Cover open", "lid_state", lambda v: v == 1, BinarySensorDeviceClass.PROBLEM, None),
        (
            "drum_not_in_place",
            "Drum not in place",
            "box_state",
            lambda v: v == 1,
            BinarySensorDeviceClass.PROBLEM,
            None,
        ),
        ("drum_stuck", "Drum stuck", "motor_state", lambda v: v in (1, 2, 3, 4), BinarySensorDeviceClass.PROBLEM, None),
        (
            "scale_fault",
            "Scale fault",
            "weigh_sensor",
            lambda v: v == 1,
            BinarySensorDeviceClass.PROBLEM,
            EntityCategory.DIAGNOSTIC,
        ),
        (
            "camera_fault",
            "Camera fault",
            "camera_state",
            lambda v: v == 1,
            BinarySensorDeviceClass.PROBLEM,
            EntityCategory.DIAGNOSTIC,
        ),
        ("light", "Light", "led_state", lambda v: v > 0, BinarySensorDeviceClass.LIGHT, None),
        (
            "firmware_updating",
            "Firmware updating",
            "update_state",
            lambda v: v == 1,
            BinarySensorDeviceClass.UPDATE,
            EntityCategory.DIAGNOSTIC,
        ),
    )
)
BINARY_SENSORS += (
    UbpetBinarySensorDescription(
        key="mqtt_connected",
        name="MQTT connected",
        translation_key="mqtt_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda item: None,
    ),
    UbpetBinarySensorDescription(
        key="waste_bin_full",
        name="Waste bin threshold reached",
        translation_key="waste_bin_full",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=waste_full,
    ),
    UbpetBinarySensorDescription(
        key="history_truncated",
        name="History fetch limit reached",
        translation_key="history_truncated",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda item: item.get("history_truncated"),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: UbpetDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    def build():
        entities = [
            UbpetDeviceBinarySensor(coordinator, coordinator.namespace, serial, description)
            for serial in coordinator.data.get("devices", {})
            for description in BINARY_SENSORS
            if keep_or_supported(coordinator, serial, description.key, "binary_sensor")
        ]
        return entities

    setup_discovery(coordinator, entry, async_add_entities, build)


class UbpetDeviceBinarySensor(UbpetDeviceEntity, BinarySensorEntity):
    entity_description: UbpetBinarySensorDescription

    def __init__(
        self,
        coordinator: UbpetDataUpdateCoordinator,
        entry_id: str,
        serial: str,
        description: UbpetBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self._bind_box(entry_id, serial, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        if self.entity_description.key == "mqtt_connected":
            return self.coordinator.transport.connected
        value = self.entity_description.value_fn(self._device_item) if self._device_item else None
        return None if value is None else bool(value)
