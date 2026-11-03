"""Cat Litter Hub integration lifecycle and backwards-compatible migration."""

from __future__ import annotations

from homeassistant.const import EVENT_HOMEASSISTANT_STOP

from .api import UbpetClient
from .const import (
    CLIENT_KEYS,
    CONF_AREA_CODE,
    CONF_COUNTRY,
    CONF_PROVIDER,
    CONF_REGION,
    DOMAIN,
    OPT_MQTT_ENABLED,
    PLATFORMS,
)
from .coordinator import UbpetDataUpdateCoordinator
from .entities import migrate_cat_devices
from .frontend import async_register_cards
from .legacy import adopt_registry_entries, async_remove_adopted_entry
from .providers import account_unique_id, infer_provider, infer_region


async def async_setup_entry(hass, entry):
    client = UbpetClient(
        **{key: entry.data[key] for key in CLIENT_KEYS},
        area_code=entry.data.get(CONF_AREA_CODE, entry.data.get(CONF_COUNTRY, "")),
    )
    await async_register_cards(hass)
    coordinator = UbpetDataUpdateCoordinator(hass, client, entry=entry)
    try:
        adopt_registry_entries(hass, entry)
        await coordinator.async_config_entry_first_refresh()
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
        migrate_cat_devices(hass, entry)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        await coordinator.async_shutdown()
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        raise

    async def stop(_event):
        await coordinator.transport.stop()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop))
    entry.async_on_unload(entry.add_update_listener(_reload))
    if entry.options.get(OPT_MQTT_ENABLED, True):
        coordinator.transport.start()
    hass.async_create_task(async_remove_adopted_entry(hass, entry))
    return True


async def _reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
        return True
    return False


async def async_migrate_entry(hass, entry):
    if entry.version > 2:
        return False
    if entry.version < 2:
        data = dict(entry.data)
        data.setdefault(CONF_PROVIDER, infer_provider(data))
        data.setdefault(CONF_REGION, infer_region(data))
        # Preserve every connection field, entry ID and entity unique ID.
        hass.config_entries.async_update_entry(entry, data=data, version=2, unique_id=account_unique_id(data))
    return True


async def async_remove_config_entry_device(hass, entry, device_entry):
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is None or not coordinator.last_update_success:
        return False
    data = coordinator.data or {}
    active = set(data.get("devices", {})) | {
        coordinator.cat_identifier(str(cat["catInfoId"]))
        for cat in data.get("cats", [])
        if cat.get("catInfoId") is not None
    }
    return not any(domain == DOMAIN and identity in active for domain, identity in device_entry.identifiers)
