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
    box_value,
    effective_work_state,
    empty_waste_bin_reminder_config,
    mask_days,
    mask_preset,
    reminder_mask,
    seconds_to_minutes,
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


def _metric(key, name, icon, value, **metadata):
    return UbpetSensorDescription(
        key=key, translation_key=key, name=name, icon=icon, value_fn=value, **metadata,
    )


def _read(group, field, convert=None):
    def extract(box):
        value = box_value(box, group, field)
        return value if convert is None else convert(value)

    return extract


_MEASUREMENT = SensorStateClass.MEASUREMENT
_DIAGNOSTIC = EntityCategory.DIAGNOSTIC
_TIMESTAMP = SensorDeviceClass.TIMESTAMP

DEVICE_SENSORS = (
    _metric("box_status", "Box status", "mdi:list-status", lambda box: _box_status(box),
            device_class=SensorDeviceClass.ENUM, options=BOX_STATUSES),
    _metric("empty_waste_bin_reminder_days", "Empty waste bin reminder days", "mdi:calendar-week",
            _reminder_days_preset, entity_category=_DIAGNOSTIC, device_class=SensorDeviceClass.ENUM,
            options=[*REMINDER_PRESETS, CUSTOM_PRESET]),
    _metric("box_use_times", "Box use times", "mdi:counter", _read("box_use_times", "boxUseTimes"),
            state_class=_MEASUREMENT),
    _metric("waste_bin_level", "Waste bin level", "mdi:delete-outline", _read("box_use_times", "percentage"),
            native_unit_of_measurement=PERCENTAGE, state_class=_MEASUREMENT),
    _metric("waste_bin_last_reset", "Waste bin last reset", "mdi:history",
            _read("box_use_times", "boxUseTimesResetTime", lambda value: _reset_time(value)),
            entity_category=_DIAGNOSTIC, device_class=_TIMESTAMP),
    _metric("box_full_max", "Box full max", "mdi:delete", _read("box_use_times", "boxFullMax"),
            entity_category=_DIAGNOSTIC, state_class=_MEASUREMENT),
    _metric("box_full_alert", "Box full alert", "mdi:alert-outline", _read("box_use_times", "boxFullAlert"),
            entity_category=_DIAGNOSTIC, state_class=_MEASUREMENT),
    _metric("deodorant_remaining_days", "Deodorant remaining days", "mdi:air-filter", _read("deodorant", "remainingDays"),
            native_unit_of_measurement="d", state_class=_MEASUREMENT),
    _metric("auto_clean_delay_current", "Auto clean delay", "mdi:broom", _read("config", "lazyTime", seconds_to_minutes),
            native_unit_of_measurement=UnitOfTime.MINUTES, state_class=_MEASUREMENT),
    _metric("firmware_version", "Firmware version", "mdi:chip", lambda box: _firmware_version(box.get("config") or {}),
            entity_category=_DIAGNOSTIC),
    _metric("wifi_name", "Wi-Fi name", "mdi:wifi", _read("config", "wifiName"), entity_category=_DIAGNOSTIC),
    *(
        _metric(key, label, icon, _read("mqtt_state", field), entity_category=_DIAGNOSTIC)
        for key, label, icon, field in (
            ("mqtt_work_mode", "MQTT work mode", "mdi:robot-vacuum", "w_mode_app_name"),
            ("mqtt_work_state", "MQTT work state", "mdi:state-machine", "w_state_app_name"),
            ("mqtt_work_cause", "MQTT work cause", "mdi:alert-circle-outline", "w_cause"),
        )
    ),
    *(
        _metric(key, label, icon, _read("runtime_state", field), device_class=_TIMESTAMP,
                entity_category=_DIAGNOSTIC, entity_registry_enabled_default=False)
        for key, label, icon, field in (
            ("last_rest_update", "Last REST update", "mdi:cloud-check-outline", "last_rest_update_at"),
            ("last_mqtt_update", "Last MQTT update", "mdi:message-check-outline", "last_mqtt_update_at"),
        )
    ),
)

CAT_SENSORS = (
    _metric("cat_weight", "Weight", "mdi:scale", lambda cat: cat.get("weight"),
            native_unit_of_measurement=UnitOfMass.KILOGRAMS, device_class=SensorDeviceClass.WEIGHT,
            state_class=_MEASUREMENT),
    _metric("cat_visits", "Visits (legacy)", "mdi:cat", lambda cat: cat.get("number"),
            state_class=_MEASUREMENT),
    _metric("cat_cost_time", "Average usage duration (legacy)", "mdi:timer-outline", lambda cat: cat.get("costTime"),
            native_unit_of_measurement=UnitOfTime.SECONDS, device_class=SensorDeviceClass.DURATION,
            state_class=_MEASUREMENT),
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
        self._bind_box(entry_id, serial, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        if self.entity_description.key == "last_rest_update":
            return self.coordinator.last_rest_update_at
        if self.entity_description.key == "last_mqtt_update":
            return self.coordinator.last_mqtt_update_at(self._serial)
        return self.entity_description.value_fn(item) if (item := self._device_item) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if item := self._device_item:
            return dict(self._extra_status_attributes(item), serial_number=self._serial)
        return None

    def _extra_status_attributes(self, item: dict[str, Any]) -> dict[str, Any]:
        if self.entity_description.key == "last_visit":
            visit = item.get("last_visit") or {}
            details = {
                "cat_name": box_value(item, "box_analytics", "last_used_by"),
                "weight_kg": visit.get("weight"),
                "duration_seconds": visit.get("duration_seconds"),
            }
            return {key: value for key, value in details.items() if value is not None}
        if self.entity_description.key == "box_status":
            return {
                "device_status_code": item.get("device", {}).get("deviceStatus"),
                "mqtt_work_state": box_value(item, "mqtt_state", "w_state_app_name"),
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
        self._bind_cat(entry_id, cat_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        cat = self._cat_data
        return None if cat is None else self.entity_description.value_fn(cat)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        profile = self._cat_data
        if profile is None:
            return None

        streams = self.coordinator.history.state["streams"]
        cat_streams = (stream for key, stream in streams.items() if key.endswith(":cat_records"))
        attributes = {
            "history_source": "observed_vendor_records",
            "history_complete_24h": bool(streams) and all(
                stream.get("complete_24h", False) for stream in cat_streams
            ),
        }
        for attribute, app_field in (("cat_info_id", "catInfoId"), ("nickname", "nickname"), ("picture", "icon")):
            attributes[attribute] = profile.get(app_field)

        if self.entity_description.key in {"cat_last_pee", "cat_last_poo", "cat_pee_visits_24h", "cat_poo_visits_24h"}:
            attributes["classification"] = "duration_estimate"
            attributes["threshold_seconds"] = self.coordinator.cat_poo_duration_threshold(self._cat_id)
        return attributes



def _firmware_version(config: dict[str, Any]) -> str | None:
    modules = config.get("boxFunctionVOList") or ()
    releases = {
        part["firmwareVersion"] for part in modules
        if isinstance(part, dict) and isinstance(part.get("firmwareVersion"), str) and part["firmwareVersion"]
    }
    return ", ".join(sorted(releases)) or None


def _reset_time(value: Any) -> datetime | None:
    try:
        epoch_ms = int(value)
        return datetime.fromtimestamp(epoch_ms / 1000, UTC) if epoch_ms > 0 else None
    except (OSError, OverflowError, TypeError, ValueError):
        return None


def _box_status(item: dict[str, Any]) -> str | None:
    mode = box_value(item, "mqtt_state", "w_mode_app_name")
    state = box_value(item, "mqtt_state", "w_state_app_name")
    live = {"PENDING": "standby", "RUNNING": "running", "PAUSED": "paused"}
    if (effective := effective_work_state(mode, state)) in live:
        return live[effective]
    try:
        rest_code = int(box_value(item, "device", "deviceStatus"))
    except (TypeError, ValueError, OverflowError):
        return None
    return "standby" if rest_code == 1 else "paused" if rest_code == 3 else "running"
