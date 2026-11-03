"""One-time adoption of entries created by the original ``ubpet`` integration and its forks.

Home Assistant treats a new domain as a new integration. To keep entity IDs, history, device
assignments and stored visits, the new entry reuses the old entry's ID as namespace for all
unique IDs and then moves the old registry rows over. Every step is idempotent.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_LEGACY_ENTRY_ID, CONF_PROVIDER, CONF_REGION, DOMAIN, LEGACY_DOMAIN
from .providers import infer_provider, infer_region

_LOGGER = logging.getLogger(__name__)


def adoptable_entries(hass: HomeAssistant) -> list[ConfigEntry]:
    """Entries of the old domain that no current entry has taken over yet."""
    adopted = {entry.data.get(CONF_LEGACY_ENTRY_ID) for entry in hass.config_entries.async_entries(DOMAIN)}
    return [entry for entry in hass.config_entries.async_entries(LEGACY_DOMAIN) if entry.entry_id not in adopted]


def entry_data_from_legacy(legacy: ConfigEntry) -> dict:
    data = dict(legacy.data)
    data.setdefault(CONF_PROVIDER, infer_provider(data))
    data.setdefault(CONF_REGION, infer_region(data))
    data[CONF_LEGACY_ENTRY_ID] = legacy.entry_id
    return data


def adopt_registry_entries(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Move devices and entities of the adopted entry over to ``entry``.

    The order matters: core deletes entities of a device as soon as the entry they belong to is
    detached from it, so the old entry is only released after all entities have moved.
    """
    legacy_id = entry.data.get(CONF_LEGACY_ENTRY_ID)
    if not legacy_id:
        return
    devices = dr.async_get(hass)
    legacy_devices = dr.async_entries_for_config_entry(devices, legacy_id)
    for device in legacy_devices:
        identifiers = {(DOMAIN if domain == LEGACY_DOMAIN else domain, key) for domain, key in device.identifiers}
        devices.async_update_device(device.id, new_identifiers=identifiers, add_config_entry_id=entry.entry_id)
    _adopt_entities(hass, entry, legacy_id)
    for device in legacy_devices:
        devices.async_update_device(device.id, remove_config_entry_id=legacy_id)
    _copy_options(hass, entry, legacy_id)


def _adopt_entities(hass: HomeAssistant, entry: ConfigEntry, legacy_id: str) -> None:
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, legacy_id):
        # Core refuses to move entities that have a state; the placeholder of an orphan is not one.
        if (state := hass.states.get(entity.entity_id)) is not None and state.attributes.get("restored"):
            hass.states.async_remove(entity.entity_id)
        try:
            registry.async_update_entity_platform(entity.entity_id, DOMAIN, new_config_entry_id=entry.entry_id)
        except ValueError:
            _LOGGER.warning("Could not adopt %s from the previous integration", entity.entity_id)


def _copy_options(hass: HomeAssistant, entry: ConfigEntry, legacy_id: str) -> None:
    legacy = hass.config_entries.async_get_entry(legacy_id)
    if legacy is not None and legacy.options and not entry.options:
        hass.config_entries.async_update_entry(entry, options=dict(legacy.options))


async def async_remove_adopted_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the emptied old entry so it stops showing up as a failed integration."""
    legacy_id = entry.data.get(CONF_LEGACY_ENTRY_ID, "")
    legacy = hass.config_entries.async_get_entry(legacy_id)
    if legacy is None or legacy.domain != LEGACY_DOMAIN:
        return
    leftovers = er.async_entries_for_config_entry(er.async_get(hass), legacy_id)
    if leftovers or dr.async_entries_for_config_entry(dr.async_get(hass), legacy_id):
        return  # Never delete an entry that still owns registry rows: removal would delete them too.
    await hass.config_entries.async_remove(legacy_id)
