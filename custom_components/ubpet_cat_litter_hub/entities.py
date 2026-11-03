"""Entity discovery and device identity shared across all platforms."""

from __future__ import annotations

from functools import partial
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .box_config import empty_waste_bin_reminder_config, first_period_config, period_config_id
from .compat import DeviceInfo, serial_info
from .const import DOMAIN, entry_namespace
from .writes import async_write


class DeviceAvailability:
    _attr_has_entity_name = True

    @property
    def available(self):
        return super().available and self._serial in (self.coordinator.data or {}).get("devices", {})


class CatAvailability:
    _attr_has_entity_name = True

    @property
    def available(self):
        return super().available and self._cat_data is not None


class UbpetDeviceEntity(DeviceAvailability, CoordinatorEntity):
    """Base of every entity that belongs to one litter box. Subclasses set ``_serial``."""

    @property
    def _device_item(self) -> dict[str, Any] | None:
        return self.coordinator.data.get("devices", {}).get(self._serial)

    @property
    def _box_config(self) -> dict[str, Any]:
        return (self._device_item or {}).get("config", {})

    @property
    def device_info(self) -> DeviceInfo:
        device = (self._device_item or {}).get("device", {})
        return DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            manufacturer=self.coordinator.provider_label,
            name=device.get("deviceName") or self._serial,
            **serial_info(self._serial),
        )


class UbpetCatEntity(CatAvailability, CoordinatorEntity):
    """Base of every entity that belongs to one cat. Subclasses set ``_cat_id``."""

    @property
    def _cat_data(self) -> dict[str, Any] | None:
        for cat in self.coordinator.data.get("cats", []):
            if str(cat.get("catInfoId")) == self._cat_id:
                return cat
        return None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.cat_identifier(self._cat_id))},
            manufacturer=self.coordinator.provider_label,
            name=(self._cat_data or {}).get("nickname") or f"Cat {self._cat_id}",
        )


class UbpetReminderEntity(UbpetDeviceEntity):
    """Switch, time and weekday entities of the empty-bin reminder share this write path."""

    @property
    def _reminder_config(self) -> dict[str, Any] | None:
        return empty_waste_bin_reminder_config(self._box_config)

    async def _write_reminder(self, **changes: Any) -> None:
        reminder = self._reminder_config
        if not reminder:
            return
        fields = {
            "open_switch": reminder.get("openSwitch", 1),
            "time_hour": reminder.get("timeHour", 0),
            "time_minute": reminder.get("timeMinute", 0),
            "option_int": reminder.get("period", 0),
            **changes,
        }
        await async_write(
            self.hass,
            partial(
                self.coordinator.client.set_time_point,
                self._serial,
                config_id=reminder["notifyConfigId"],
                function_type=1,
                **fields,
            ),
        )
        self.coordinator.schedule_refresh(15)


class UbpetPeriodEntity(UbpetDeviceEntity):
    """Do-not-disturb and light schedule: a start/end period with an on/off flag."""

    @property
    def _period_config(self) -> dict[str, Any] | None:
        return first_period_config(self._box_config, self.entity_description.config_list_key)

    async def _write_period(self, **changes: Any) -> None:
        period = self._period_config
        config_id = period_config_id(period) if period else None
        if config_id is None:
            return
        fields = {
            "open_switch": period.get("openSwitch", 1),
            "start_hour": period.get("startTimeHour", 0),
            "start_minute": period.get("startTimeMinute", 0),
            "end_hour": period.get("endTimeHour", 0),
            "end_minute": period.get("endTimeMinute", 0),
            **changes,
        }
        await async_write(
            self.hass,
            partial(
                self.coordinator.client.set_time_period,
                self._serial,
                config_id=config_id,
                function_type=self.entity_description.function_type,
                **fields,
            ),
        )
        self.coordinator.schedule_refresh(15)


def setup_discovery(coordinator, entry, adder, build):
    seen = set()
    previous = None

    @callback
    def discover():
        nonlocal previous
        data = coordinator.data or {}
        # Cheap fingerprint: entities depend on what the last REST refresh delivered and on which push
        # fields exist; hashing the whole config on every push would be wasted work.
        signature = (
            coordinator.last_rest_update_at,
            tuple(sorted((sn, len(item.get("mqtt_state", {}))) for sn, item in data.get("devices", {}).items())),
            tuple(sorted(str(cat.get("catInfoId")) for cat in data.get("cats", []))),
        )
        if signature == previous:
            return
        previous = signature
        new = []
        for entity in build():
            if entity.unique_id not in seen:
                seen.add(entity.unique_id)
                new.append(entity)
        if new:
            adder(new)

    discover()
    entry.async_on_unload(coordinator.async_add_listener(discover))


def migrate_cat_devices(hass, entry):
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        identifiers = set(device.identifiers)
        old = {
            (domain, key)
            for domain, key in identifiers
            if domain == DOMAIN and key.startswith("cat_") and key.count("_") == 1
        }
        if old and device.config_entries == {entry.entry_id}:
            identifiers.difference_update(old)
            identifiers.update((DOMAIN, f"cat_{entry_namespace(entry)}_{key[4:]}") for _, key in old)
            registry.async_update_device(device.id, new_identifiers=identifiers)


def supports_camera(item):
    caps = item.get("capabilities")
    if isinstance(caps, dict):
        return "cat_face_upload" in repr(caps.get("values"))
    return item.get("config", {}).get("cameraSwitch") is not None


def supported(key, item):
    if key in {"camera_switch", "camera_fault"}:
        return supports_camera(item)
    if key == "scheduled_cleans":
        return item.get("config", {}).get("taskConfigList") is not None
    if key in {"light", "light_schedule", "light_schedule_start", "light_schedule_end"}:
        return item.get("config", {}).get("lightSwitch") is not None
    return True


def keep_or_supported(coordinator, serial, key, platform):
    if supported(key, coordinator.data["devices"][serial]):
        return True
    registry = er.async_get(coordinator.hass)
    return registry.async_get_entity_id(platform, DOMAIN, f"{coordinator.namespace}_{serial}_{key}") is not None
