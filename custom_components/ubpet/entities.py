"""Entity discovery and device identity shared across all platforms."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


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


def setup_discovery(coordinator, entry, adder, build):
    seen = set()
    previous = None

    @callback
    def discover():
        nonlocal previous
        data = coordinator.data or {}
        signature = (
            tuple(
                sorted(
                    (
                        sn,
                        repr(item.get("config")),
                        repr(item.get("capabilities")),
                        tuple(sorted(item.get("box_use_times", {}))),
                        tuple(sorted(item.get("mqtt_state", {}))),
                    )
                    for sn, item in data.get("devices", {}).items()
                )
            ),
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
            identifiers.update((DOMAIN, f"cat_{entry.entry_id}_{key[4:]}") for _, key in old)
            registry.async_update_device(device.id, new_identifiers=identifiers)


def supports_camera(item):
    caps = item.get("capabilities")
    if isinstance(caps, dict):
        return "cat_face_upload" in repr(caps.get("values"))
    return item.get("config", {}).get("cameraSwitch") is not None


def supported(key, item):
    if key in {"camera_switch", "camera_fault"}:
        return supports_camera(item)
    if key in {"light", "light_schedule", "light_schedule_start", "light_schedule_end"}:
        return item.get("config", {}).get("lightSwitch") is not None
    return True


def keep_or_supported(coordinator, serial, key, platform):
    if supported(key, coordinator.data["devices"][serial]):
        return True
    registry = er.async_get(coordinator.hass)
    return registry.async_get_entity_id(platform, DOMAIN, f"{coordinator.entry.entry_id}_{serial}_{key}") is not None
