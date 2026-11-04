"""Adoption of entries created by the original ``ubpet`` integration, tested with real registries."""

from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

pytest.importorskip("pytest_homeassistant_custom_component")
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from custom_components.ubpet_cat_litter_hub.const import CONF_LEGACY_ENTRY_ID, DOMAIN, LEGACY_DOMAIN  # noqa: E402
from custom_components.ubpet_cat_litter_hub.legacy import (  # noqa: E402
    adopt_registry_entries,
    adoptable_entries,
    async_remove_adopted_entry,
    entry_data_from_legacy,
)
from custom_components.ubpet_cat_litter_hub.providers import credentials, endpoint  # noqa: E402

SERIAL = "SN123"
LEGACY_DATA = {
    "account": "owner@example.test",
    "password": "pw",
    "device_id": "device",
    "base_url": endpoint("upet", "eu"),
    "area_code": "DE",
    "country": "DE",
    **credentials("upet", "eu"),
}


@pytest.fixture(autouse=True)
def _custom_integrations(enable_custom_integrations):
    return None


def _legacy_entry(hass, state=ConfigEntryState.NOT_LOADED):
    entry = MockConfigEntry(domain=LEGACY_DOMAIN, data=LEGACY_DATA, title="UPET", state=state)
    entry.add_to_hass(hass)
    return entry


def _register_legacy_rows(hass, legacy):
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=legacy.entry_id,
        identifiers={(LEGACY_DOMAIN, SERIAL), (LEGACY_DOMAIN, f"cat_{legacy.entry_id}_7")},
    )
    entity = er.async_get(hass).async_get_or_create(
        "sensor",
        LEGACY_DOMAIN,
        f"{legacy.entry_id}_{SERIAL}_box_status",
        config_entry=legacy,
        device_id=device.id,
        suggested_object_id="litter_box_status",
    )
    # What Home Assistant shows for an entity whose integration is gone.
    hass.states.async_set(entity.entity_id, "unavailable", {"restored": True})
    return device, entity


def _new_entry(hass, legacy):
    entry = MockConfigEntry(domain=DOMAIN, data=entry_data_from_legacy(legacy), title="UPET")
    entry.add_to_hass(hass)
    return entry


async def test_entry_data_keeps_connection_and_marks_origin(hass):
    legacy = _legacy_entry(hass)
    data = entry_data_from_legacy(legacy)
    assert data[CONF_LEGACY_ENTRY_ID] == legacy.entry_id
    assert data["provider"] == "upet" and data["region"] == "eu"
    assert data["password"] == "pw" and data["device_id"] == "device"
    assert adoptable_entries(hass) == [legacy]
    _new_entry(hass, legacy)
    assert adoptable_entries(hass) == []


async def test_registry_rows_move_with_ids_unchanged(hass):
    legacy = _legacy_entry(hass)
    device, entity = _register_legacy_rows(hass, legacy)
    entry = _new_entry(hass, legacy)

    adopt_registry_entries(hass, entry)

    moved = er.async_get(hass).async_get(entity.entity_id)
    assert moved.platform == DOMAIN
    assert moved.config_entry_id == entry.entry_id
    assert moved.unique_id == entity.unique_id  # entity IDs, history and customisations survive
    assert moved.device_id == device.id
    moved_device = dr.async_get(hass).async_get(device.id)
    assert moved_device.identifiers == {(DOMAIN, SERIAL), (DOMAIN, f"cat_{legacy.entry_id}_7")}
    if hasattr(moved_device, "config_entry_id"):
        assert moved_device.config_entry_id == entry.entry_id
    else:
        assert moved_device.config_entries == {entry.entry_id}


async def test_adoption_is_idempotent(hass):
    legacy = _legacy_entry(hass)
    _, entity = _register_legacy_rows(hass, legacy)
    entry = _new_entry(hass, legacy)
    adopt_registry_entries(hass, entry)
    adopt_registry_entries(hass, entry)
    assert er.async_get(hass).async_get(entity.entity_id).config_entry_id == entry.entry_id


async def test_emptied_legacy_entry_is_removed_but_never_with_leftovers(hass):
    legacy = _legacy_entry(hass)
    _register_legacy_rows(hass, legacy)
    entry = _new_entry(hass, legacy)

    await async_remove_adopted_entry(hass, entry)  # rows not moved yet: must keep everything
    assert hass.config_entries.async_get_entry(legacy.entry_id) is not None

    adopt_registry_entries(hass, entry)
    await async_remove_adopted_entry(hass, entry)
    assert hass.config_entries.async_get_entry(legacy.entry_id) is None
    assert er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)  # moved rows survive the removal


async def test_flow_offers_adoption_and_creates_entry(hass):
    legacy = _legacy_entry(hass)
    with patch("custom_components.ubpet_cat_litter_hub.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert result["type"] == "menu" and "migrate" in result["menu_options"]
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "migrate"})
        assert result["step_id"] == "migrate"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    assert result["data"][CONF_LEGACY_ENTRY_ID] == legacy.entry_id
    assert result["data"]["account"] == LEGACY_DATA["account"]


async def test_flow_refuses_while_old_integration_is_still_running(hass):
    _legacy_entry(hass, state=ConfigEntryState.LOADED)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "migrate"})
    assert result["type"] == "abort" and result["reason"] == "legacy_still_installed"


async def test_flow_without_old_entries_starts_with_provider_choice(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == "form" and result["step_id"] == "provider"
