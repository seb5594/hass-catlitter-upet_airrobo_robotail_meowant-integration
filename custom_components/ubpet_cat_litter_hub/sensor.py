from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .box_config import (
    CUSTOM_PRESET,
    REMINDER_PRESETS,
    effective_work_state,
    empty_waste_bin_reminder_config,
    mask_days,
    mask_preset,
    reminder_mask,
)
from .compat import description_is_frozen
from .const import DOMAIN
from .coordinator import UbpetDataUpdateCoordinator
from .entities import UbpetCatEntity, UbpetDeviceEntity, keep_or_supported, setup_discovery
from .history import remaining_uses, timestamp

UTC = timezone.utc


@dataclass(frozen=description_is_frozen(SensorEntityDescription), kw_only=True)
class UbpetSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


BOX_STATUSES = ["standby", "running", "paused"]


def _reminder_days_preset(item: dict[str, Any]) -> str | None:
    reminder = empty_waste_bin_reminder_config(item["config"])
    return None if reminder is None else mask_preset(reminder_mask(reminder))


def _pet_position(item: dict[str, Any]) -> str | None:
    inside = item.get("mqtt_state", {}).get("cat_inside")
    return None if inside is None else ("inside" if inside else "away")


DEVICE_SENSORS: tuple[UbpetSensorDescription, ...] = (
    UbpetSensorDescription(
        key="box_status",
        name="Box status",
        icon="mdi:list-status",
        translation_key="box_status",
        device_class=SensorDeviceClass.ENUM,
        options=BOX_STATUSES,
        value_fn=lambda item: _box_status(item),
    ),
    UbpetSensorDescription(
        key="empty_waste_bin_reminder_days",
        name="Empty waste bin reminder days",
        icon="mdi:calendar-week",
        translation_key="empty_waste_bin_reminder_days",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=[*REMINDER_PRESETS, CUSTOM_PRESET],
        value_fn=_reminder_days_preset,
    ),
    UbpetSensorDescription(
        key="box_use_times",
        name="Box use times",
        icon="mdi:counter",
        translation_key="box_use_times",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda item: item["box_use_times"].get("boxUseTimes"),
    ),
    UbpetSensorDescription(
        key="waste_bin_level",
        name="Waste bin level",
        icon="mdi:delete-outline",
        translation_key="waste_bin_level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda item: item["box_use_times"].get("percentage"),
    ),
    UbpetSensorDescription(
        key="waste_bin_last_reset",
        name="Waste bin last reset",
        icon="mdi:history",
        translation_key="waste_bin_last_reset",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda item: _milliseconds_to_datetime(item["box_use_times"].get("boxUseTimesResetTime")),
    ),
    UbpetSensorDescription(
        key="box_full_max",
        name="Box full max",
        icon="mdi:delete",
        translation_key="box_full_max",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda item: item["box_use_times"].get("boxFullMax"),
    ),
    UbpetSensorDescription(
        key="box_full_alert",
        name="Box full alert",
        icon="mdi:alert-outline",
        translation_key="box_full_alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda item: item["box_use_times"].get("boxFullAlert"),
    ),
    UbpetSensorDescription(
        key="deodorant_remaining_days",
        name="Deodorant remaining days",
        icon="mdi:air-filter",
        translation_key="deodorant_remaining_days",
        native_unit_of_measurement="d",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda item: item["deodorant"].get("remainingDays"),
    ),
    UbpetSensorDescription(
        key="auto_clean_delay_current",
        name="Auto clean delay",
        icon="mdi:broom",
        translation_key="auto_clean_delay_current",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda item: _seconds_to_minutes(item["config"].get("lazyTime")),
    ),
    UbpetSensorDescription(
        key="firmware_version",
        name="Firmware version",
        icon="mdi:chip",
        translation_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda item: _firmware_version(item["config"]),
    ),
    UbpetSensorDescription(
        key="wifi_name",
        name="Wi-Fi name",
        icon="mdi:wifi",
        translation_key="wifi_name",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda item: item["config"].get("wifiName"),
    ),
    UbpetSensorDescription(
        key="mqtt_work_mode",
        name="MQTT work mode",
        icon="mdi:robot-vacuum",
        translation_key="mqtt_work_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda item: _mqtt_state_value(item, "w_mode_app_name"),
    ),
    UbpetSensorDescription(
        key="mqtt_work_state",
        name="MQTT work state",
        icon="mdi:state-machine",
        translation_key="mqtt_work_state",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda item: _mqtt_state_value(item, "w_state_app_name"),
    ),
    UbpetSensorDescription(
        key="mqtt_work_cause",
        name="MQTT work cause",
        icon="mdi:alert-circle-outline",
        translation_key="mqtt_work_cause",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda item: _mqtt_state_value(item, "w_cause"),
    ),
    UbpetSensorDescription(
        key="last_rest_update",
        entity_registry_enabled_default=False,
        name="Last REST update",
        icon="mdi:cloud-check-outline",
        translation_key="last_rest_update",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda item: _runtime_state_value(item, "last_rest_update_at"),
    ),
    UbpetSensorDescription(
        key="last_mqtt_update",
        entity_registry_enabled_default=False,
        name="Last MQTT update",
        icon="mdi:message-check-outline",
        translation_key="last_mqtt_update",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda item: _runtime_state_value(item, "last_mqtt_update_at"),
    ),
)

CAT_SENSORS: tuple[UbpetSensorDescription, ...] = (
    UbpetSensorDescription(
        key="cat_weight",
        name="Weight",
        icon="mdi:scale",
        translation_key="cat_weight",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda item: item.get("weight"),
    ),
    UbpetSensorDescription(
        key="cat_visits",
        name="Visits (legacy)",
        icon="mdi:cat",
        translation_key="cat_visits",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda item: item.get("number"),
    ),
    UbpetSensorDescription(
        key="cat_cost_time",
        name="Average usage duration (legacy)",
        icon="mdi:timer-outline",
        translation_key="cat_cost_time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda item: item.get("costTime"),
    ),
)


# Keep the multi-region fork's keys so existing entity registry entries survive.
CAT_SENSORS += tuple(
    UbpetSensorDescription(
        key=key,
        name=name,
        translation_key=key,
        icon=icon,
        native_unit_of_measurement=unit,
        device_class=kind,
        state_class=state,
        value_fn=lambda cat, field=field: cat.get("visit_analytics", {}).get(field),
    )
    for key, name, field, unit, kind, state, icon in (
        (
            "cat_last_visit_duration",
            "Last visit duration",
            "last_visit_duration_seconds",
            "s",
            SensorDeviceClass.DURATION,
            SensorStateClass.MEASUREMENT,
            "mdi:timer-outline",
        ),
        (
            "cat_pee_visits_24h",
            "Pee in 24 hours (estimated)",
            "pee_visits_24h",
            "visits",
            None,
            SensorStateClass.MEASUREMENT,
            "mdi:water-outline",
        ),
        (
            "cat_poo_visits_24h",
            "Poo in 24 hours (estimated)",
            "poo_visits_24h",
            "visits",
            None,
            SensorStateClass.MEASUREMENT,
            "mdi:emoticon-poop",
        ),
        (
            "cat_last_pee",
            "Last pee (estimated)",
            "last_pee",
            None,
            SensorDeviceClass.TIMESTAMP,
            None,
            "mdi:clock-outline",
        ),
        (
            "cat_last_poo",
            "Last poo (estimated)",
            "last_poo",
            None,
            SensorDeviceClass.TIMESTAMP,
            None,
            "mdi:clock-outline",
        ),
        ("cat_last_visit", "Last visit", "last_visit", None, SensorDeviceClass.TIMESTAMP, None, "mdi:cat"),
        (
            "cat_visits_24h",
            "Visits in 24 hours",
            "visits_24h",
            "visits",
            None,
            SensorStateClass.MEASUREMENT,
            "mdi:counter",
        ),
        (
            "cat_duration_24h",
            "Time in box in 24 hours",
            "duration_24h",
            "s",
            SensorDeviceClass.DURATION,
            SensorStateClass.MEASUREMENT,
            "mdi:timer-outline",
        ),
        (
            "cat_average_duration_24h",
            "Average visit duration in 24 hours",
            "average_duration_24h",
            "s",
            SensorDeviceClass.DURATION,
            SensorStateClass.MEASUREMENT,
            "mdi:timer-outline",
        ),
        (
            "cat_maximum_duration_24h",
            "Longest visit in 24 hours",
            "maximum_duration_24h",
            "s",
            SensorDeviceClass.DURATION,
            SensorStateClass.MEASUREMENT,
            "mdi:timer-outline",
        ),
        (
            "cat_weight_change",
            "Weight change since previous visit",
            "weight_change",
            "kg",
            None,
            SensorStateClass.MEASUREMENT,
            "mdi:scale",
        ),
    )
)
DEVICE_SENSORS += (
    UbpetSensorDescription(
        key="remaining_bin_uses",
        name="Uses until bin capacity",
        translation_key="remaining_bin_uses",
        icon="mdi:delete-clock",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=remaining_uses,
    ),
    UbpetSensorDescription(
        key="last_visit",
        name="Last visit",
        translation_key="last_visit",
        icon="mdi:cat",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda item: timestamp((item.get("last_visit") or {}).get("at")),
    ),
    UbpetSensorDescription(
        key="mqtt_pet_position",
        name="Pet position",
        translation_key="mqtt_pet_position",
        icon="mdi:cat",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=["inside", "away"],
        value_fn=_pet_position,
    ),
)


def _box_analytic(field: str) -> Callable[[dict[str, Any]], Any]:
    return lambda item: (item.get("box_analytics") or {}).get(field)


def _scheduled_cleans(item: dict[str, Any]) -> int | None:
    tasks = item["config"].get("taskConfigList")
    return None if tasks is None else sum(1 for task in tasks if task.get("openSwitch") == 1)


DEVICE_SENSORS += (
    UbpetSensorDescription(
        key="visits_today",
        name="Visits today",
        translation_key="visits_today",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_box_analytic("visits_today"),
    ),
    UbpetSensorDescription(
        key="cleans_today",
        name="Cleans today",
        translation_key="cleans_today",
        icon="mdi:broom",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_box_analytic("cleans_today"),
    ),
    UbpetSensorDescription(
        key="last_clean",
        name="Last clean",
        translation_key="last_clean",
        icon="mdi:broom",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_box_analytic("last_clean"),
    ),
    UbpetSensorDescription(
        key="cleans_since_bin_reset",
        name="Cleans since waste bin reset",
        translation_key="cleans_since_bin_reset",
        icon="mdi:delete-restore",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_box_analytic("cleans_since_bin_reset"),
    ),
    UbpetSensorDescription(
        key="last_used_by",
        name="Last used by",
        translation_key="last_used_by",
        icon="mdi:cat",
        value_fn=_box_analytic("last_used_by"),
    ),
    UbpetSensorDescription(
        key="scheduled_cleans",
        name="Scheduled cleans",
        translation_key="scheduled_cleans",
        icon="mdi:calendar-clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_scheduled_cleans,
    ),
)
CAT_SENSORS += (
    UbpetSensorDescription(
        key="cat_visits_today",
        name="Visits today",
        translation_key="cat_visits_today",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda cat: cat.get("visit_analytics", {}).get("visits_today"),
    ),
    UbpetSensorDescription(
        key="cat_last_visit_weight",
        name="Weight at last visit",
        translation_key="cat_last_visit_weight",
        icon="mdi:scale",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda cat: cat.get("visit_analytics", {}).get("last_visit_weight"),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: UbpetDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    def build():
        entities: list[SensorEntity] = []
        for serial in coordinator.data.get("devices", {}):
            entities.extend(
                UbpetDeviceSensor(coordinator, coordinator.namespace, serial, description)
                for description in DEVICE_SENSORS
                if keep_or_supported(coordinator, serial, description.key, "sensor")
            )
        for cat in coordinator.data.get("cats", []):
            cat_id = cat.get("catInfoId")
            if cat_id is None:
                continue
            entities.extend(
                UbpetCatSensor(coordinator, coordinator.namespace, str(cat_id), description)
                for description in CAT_SENSORS
            )
        return entities

    setup_discovery(coordinator, entry, async_add_entities, build)


class UbpetDeviceSensor(UbpetDeviceEntity, SensorEntity):
    entity_description: UbpetSensorDescription

    def __init__(
        self, coordinator: UbpetDataUpdateCoordinator, entry_id: str, serial: str, description: UbpetSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{serial}_{description.key}"

    @property
    def native_value(self) -> Any:
        if self.entity_description.key == "last_rest_update":
            return self.coordinator.last_rest_update_at
        if self.entity_description.key == "last_mqtt_update":
            return self.coordinator.last_mqtt_update_at(self._serial)
        item = self.coordinator.data.get("devices", {}).get(self._serial)
        if not item:
            return None
        return self.entity_description.value_fn(item)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        item = self.coordinator.data.get("devices", {}).get(self._serial)
        if not item:
            return None
        return {
            "serial_number": self._serial,
            **self._extra_status_attributes(item),
        }

    def _extra_status_attributes(self, item: dict[str, Any]) -> dict[str, Any]:
        if self.entity_description.key == "box_status":
            return {
                "device_status_code": item.get("device", {}).get("deviceStatus"),
                "mqtt_work_state": _mqtt_state_value(item, "w_state_app_name"),
            }
        if self.entity_description.key.startswith("mqtt_"):
            mqtt_state = item.get("mqtt_state")
            return (
                {
                    key: value
                    for key, value in mqtt_state.items()
                    if key in {"w_mode", "w_state", "w_cause", "w_state_app_raw_name"}
                }
                if isinstance(mqtt_state, dict)
                else {}
            )
        if self.entity_description.key == "empty_waste_bin_reminder_days":
            reminder = empty_waste_bin_reminder_config(item["config"]) or {}
            return {"days": mask_days(reminder_mask(reminder))}
        if self.entity_description.key in {
            "last_rest_update",
            "last_mqtt_update",
        }:
            runtime_state = item.get("runtime_state")
            return runtime_state if isinstance(runtime_state, dict) else {}
        return {}


class UbpetCatSensor(UbpetCatEntity, SensorEntity):
    entity_description: UbpetSensorDescription

    def __init__(
        self, coordinator: UbpetDataUpdateCoordinator, entry_id: str, cat_id: str, description: UbpetSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self._cat_id = cat_id
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_cat_{cat_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        cat = self._cat_data
        if cat is None:
            return None
        return self.entity_description.value_fn(cat)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        cat = self._cat_data
        if cat is None:
            return None
        return {
            "cat_info_id": cat.get("catInfoId"),
            "nickname": cat.get("nickname"),
            "picture": cat.get("icon"),
            "history_source": "observed_vendor_records",
            "history_complete_24h": all(
                stream.get("complete_24h", False)
                for key, stream in self.coordinator.history.state["streams"].items()
                if key.endswith(":cat_records")
            )
            and bool(self.coordinator.history.state["streams"]),
            **(
                {
                    "classification": "duration_estimate",
                    "threshold_seconds": self.coordinator.cat_poo_duration_threshold(self._cat_id),
                }
                if self.entity_description.key
                in {"cat_last_pee", "cat_last_poo", "cat_pee_visits_24h", "cat_poo_visits_24h"}
                else {}
            ),
        }


def _firmware_version(config: dict[str, Any]) -> str | None:
    versions = sorted(
        {part.get("firmwareVersion") for part in (config.get("boxFunctionVOList") or []) if part.get("firmwareVersion")}
    )
    return ", ".join(versions) if versions else None


def _seconds_to_minutes(value: Any) -> int | float | None:
    if value is None:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    minutes = seconds / 60
    return int(minutes) if minutes.is_integer() else minutes


def _milliseconds_to_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        milliseconds = int(value)
    except (TypeError, ValueError):
        return None
    if milliseconds <= 0:
        return None
    return datetime.fromtimestamp(milliseconds / 1000, UTC)


def _box_status(item: dict[str, Any]) -> str | None:
    mqtt_status = _box_status_from_mqtt(item)
    if mqtt_status is not None:
        return mqtt_status
    device_status = item.get("device", {}).get("deviceStatus")
    if device_status is None:
        return None
    try:
        status = int(device_status)
    except (TypeError, ValueError):
        return None
    return {1: "standby", 3: "paused"}.get(status, "running")


def _box_status_from_mqtt(item: dict[str, Any]) -> str | None:
    state = effective_work_state(
        _mqtt_state_value(item, "w_mode_app_name"), _mqtt_state_value(item, "w_state_app_name")
    )
    return {"PENDING": "standby", "RUNNING": "running", "PAUSED": "paused"}.get(state)


def _mqtt_state_value(item: dict[str, Any], key: str) -> Any:
    mqtt_state = item.get("mqtt_state")
    if not isinstance(mqtt_state, dict):
        return None
    return mqtt_state.get(key)


def _runtime_state_value(item: dict[str, Any], key: str) -> Any:
    runtime_state = item.get("runtime_state")
    if not isinstance(runtime_state, dict):
        return None
    return runtime_state.get(key)
