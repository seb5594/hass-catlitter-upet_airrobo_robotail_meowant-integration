"""Full setup through Home Assistant with a mocked vendor API: all platforms, enum states, adoption."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

pytest.importorskip("pytest_homeassistant_custom_component")
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from custom_components.ubpet_cat_litter_hub.const import CONF_LEGACY_ENTRY_ID, DOMAIN, LEGACY_DOMAIN  # noqa: E402
from custom_components.ubpet_cat_litter_hub.legacy import entry_data_from_legacy  # noqa: E402
from custom_components.ubpet_cat_litter_hub.providers import credentials, endpoint  # noqa: E402

NOW = datetime.now(timezone.utc)


def _ms(delta):
    return int((NOW - delta).timestamp() * 1000)


DASHBOARD = {
    "devices": {
        "SN1": {
            "device": {"deviceName": "Box", "serialNumber": "SN1", "deviceStatus": 1},
            "fresh": {"cat_records": True, "device_records": True},
            "config": {
                "sensorSwitch": 1,
                "lazyTime": 480,
                "controlBoardSwitch": 0,
                "litterType": 0,
                "boxFullAlertSwitch": 1,
                "lightSwitch": 1,
                "notifyConfigList": [
                    {"type": 4, "notifyConfigId": 9, "openSwitch": 1, "timeHour": 8, "timeMinute": 0, "period": 31},
                    {"type": 1, "openSwitch": 1},
                ],
                "taskConfigList": [{"openSwitch": 1, "timeHour": 7, "timeMinute": 30}],
                "boxFunctionVOList": [{"firmwareVersion": "1.0"}],
            },
            "box_use_times": {"boxUseTimes": 3, "boxFullMax": 30, "boxFullAlert": 25, "percentage": 10},
            "deodorant": {"remainingDays": 20, "alertSwitch": 1, "expired": False},
            "online": {"online": True},
            "cat_records": [
                {
                    "recordId": "v1",
                    "eventTime": _ms(timedelta(minutes=30)),
                    "eventType": 3,
                    "costTime": 40,
                    "catInfoId": 7,
                    "weight": 4.2,
                }
            ],
            "device_records": [{"recordId": "c1", "eventTime": _ms(timedelta(minutes=20)), "eventType": 31}],
            "capabilities": None,
        }
    },
    "cats": [{"catInfoId": 7, "nickname": "Micky", "weight": 4.2, "number": 1, "costTime": 40}],
    "cats_fresh": True,
    "user_id": 1,
}


@pytest.fixture(autouse=True)
def _custom_integrations(enable_custom_integrations):
    return None


def _entry_data():
    return {
        "account": "owner@example.test",
        "password": "pw",
        "device_id": "device",
        "base_url": endpoint("upet", "eu"),
        "area_code": "DE",
        "country": "DE",
        "provider": "upet",
        "region": "eu",
        **credentials("upet", "eu"),
        "app_key": "local-test-signing-key",
    }


async def _setup(hass, entry):
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.ubpet_cat_litter_hub.api.UbpetClient.get_dashboard",
            side_effect=lambda: deepcopy(DASHBOARD),
        ),
        patch("custom_components.ubpet_cat_litter_hub.api.UbpetClient.ensure_login"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


def _state(hass, platform, namespace, key, serial="SN1"):
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{namespace}_{serial}_{key}")
    assert entity_id, (platform, key)
    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    return state


async def test_all_platforms_load_and_enum_states_are_valid(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=_entry_data(), options={"mqtt_enabled": False}, version=2)
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    ns = entry.entry_id
    assert _state(hass, "sensor", ns, "box_status").state == "standby"
    assert _state(hass, "sensor", ns, "empty_waste_bin_reminder_days").state == "weekdays"
    assert _state(hass, "sensor", ns, "scheduled_cleans").state == "1"
    assert _state(hass, "sensor", ns, "visits_today").state in ("0", "1")  # depends on the clock's midnight
    assert _state(hass, "sensor", ns, "last_used_by").state in ("Micky", "unknown")
    assert _state(hass, "select", ns, "empty_waste_bin_reminder_days_select").state == "weekdays"
    assert _state(hass, "switch", ns, "foreign_object_detection").state == "on"
    # Per-weekday switches are opt-in: registered, but disabled until the user enables them.
    monday = er.async_get(hass).async_get_entity_id("switch", DOMAIN, f"{ns}_SN1_reminder_monday")
    assert er.async_get(hass).async_get(monday).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_adopted_entry_keeps_entity_ids_and_removes_old_entry(hass):
    legacy = MockConfigEntry(domain=LEGACY_DOMAIN, data=_entry_data(), title="UPET")
    legacy.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=legacy.entry_id, identifiers={(LEGACY_DOMAIN, "SN1")}
    )
    old = er.async_get(hass).async_get_or_create(
        "sensor",
        LEGACY_DOMAIN,
        f"{legacy.entry_id}_SN1_box_status",
        config_entry=legacy,
        device_id=device.id,
        suggested_object_id="my_litter_box_status",
    )
    entry = MockConfigEntry(
        domain=DOMAIN, data=entry_data_from_legacy(legacy), options={"mqtt_enabled": False}, version=2
    )
    await _setup(hass, entry)

    assert entry.data[CONF_LEGACY_ENTRY_ID] == legacy.entry_id
    assert hass.states.get(old.entity_id).state == "standby"  # same entity_id, now served by the new integration
    assert er.async_get(hass).async_get(old.entity_id).platform == DOMAIN
    assert dr.async_get(hass).async_get(device.id).identifiers >= {(DOMAIN, "SN1")}
    assert hass.config_entries.async_get_entry(legacy.entry_id) is None
    await hass.config_entries.async_unload(entry.entry_id)


async def test_cards_are_served_and_loaded_once(hass):
    from unittest.mock import AsyncMock, MagicMock

    from custom_components.ubpet_cat_litter_hub.frontend import CARDS_FILE, CARDS_URL, async_register_cards

    # Home Assistant before 2024.7 serves static files through the synchronous call instead.
    hass.http = MagicMock(async_register_static_paths=AsyncMock(), register_static_path=MagicMock())
    with patch("homeassistant.components.frontend.add_extra_js_url") as add_url:
        await async_register_cards(hass)
        await async_register_cards(hass)  # a second config entry must not register again
    add_url.assert_called_once()
    assert add_url.call_args.args[1].startswith(f"{CARDS_URL}?v=")
    assert hass.http.async_register_static_paths.await_count + hass.http.register_static_path.call_count == 1
    assert CARDS_FILE.is_file()
