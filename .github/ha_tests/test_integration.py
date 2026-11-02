"""Tests use Home Assistant's real entity/coordinator classes and no vendor credentials."""

from __future__ import annotations

import inspect
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Run this module with the full runtime dependency set; pure codec tests remain standalone.
pytest.importorskip("homeassistant")
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.ubpet.api import UbpetApiError, UbpetClient
from custom_components.ubpet.button import MQTT_BUTTONS, UbpetMqttCommandButton
from custom_components.ubpet.config_flow import UbpetConfigFlow
from custom_components.ubpet.coordinator import UbpetDataUpdateCoordinator
from custom_components.ubpet.entities import setup_discovery
from custom_components.ubpet.history import History, presence, remaining_uses, timestamp
from custom_components.ubpet.mqtt import build_risp_frame, field_varint, summarize_risp_frame
from custom_components.ubpet.privacy import redact
from custom_components.ubpet.providers import account_unique_id, credentials, endpoint, suggest_region
from custom_components.ubpet.sensor import CAT_SENSORS, UbpetCatSensor

UTC = timezone.utc


NOW = datetime(2026, 11, 2, 20, tzinfo=UTC)


def visit(identity, minutes=0, cat=7, duration=57):
    return {
        "recordId": identity,
        "eventTime": int((NOW - timedelta(minutes=minutes)).timestamp() * 1000),
        "eventType": 3,
        "costTime": duration,
        "catInfoId": cat,
        "weight": 4.2,
    }


def client():
    return UbpetClient(
        account="test@example.test",
        password="test",
        app_key="test",
        device_id="test",
        base_url=endpoint("upet", "eu"),
        app_id="test",
        product="test",
    )


def entry(identity="account1"):
    return SimpleNamespace(
        entry_id=identity,
        options={},
        data={"provider": "upet"},
        pref_disable_polling=False,
        async_on_unload=MagicMock(),
        async_create_background_task=MagicMock(),
    )


@pytest.fixture
async def coordinator(tmp_path, request):
    shared = "hass" in request.fixturenames
    if shared:
        hass = request.getfixturevalue("hass")
    elif "config_dir" in inspect.signature(HomeAssistant).parameters:
        hass = HomeAssistant(str(tmp_path))
    else:
        hass = HomeAssistant()
        hass.config.config_dir = str(tmp_path)
    c = UbpetDataUpdateCoordinator(hass, client(), entry=entry())
    c._store.async_load = AsyncMock(return_value=None)
    c._store.async_save = AsyncMock()
    c._store.async_delay_save = MagicMock()
    yield c
    await c.async_shutdown()
    if not shared:
        await hass.async_stop()


@pytest.mark.parametrize(
    ("country", "zone", "expected"),
    [
        ("DE", "America/New_York", "eu"),
        ("US", None, "na"),
        ("RU", None, "ru"),
        ("JP", None, "asia"),
        (None, "Europe/Berlin", "eu"),
        (None, "America/Toronto", "na"),
    ],
)
def test_region_is_only_a_hint(country, zone, expected):
    assert suggest_region(country, zone) == expected
    assert endpoint("upet", "na") == "https://apis.airrobo-home.com"
    assert credentials("upet", "na")["app_id"] != credentials("upet", "eu")["app_id"]
    with pytest.raises(ValueError):
        endpoint("meowant", "eu")


def test_account_identity_includes_tenant_and_normalizes_email():
    base = {"account": " Test@Example.test ", "app_id": "one", "base_url": "https://example.test/"}
    assert account_unique_id(base) == account_unique_id({**base, "account": "test@example.test"})
    assert account_unique_id(base) != account_unique_id({**base, "app_id": "two"})
    assert account_unique_id(base) != account_unique_id({**base, "base_url": "https://another.test"})


def test_records_are_deduplicated_and_restart_does_not_replay():
    h = History()
    assert h.ingest("SN", "cat_records", [visit(1)], NOW) == []
    assert len(h.ingest("SN", "cat_records", [visit(1), visit(2, cat=8)], NOW)) == 1
    restored = History(deepcopy(h.state))
    assert restored.ingest("SN", "cat_records", [visit(1), visit(2, cat=8)], NOW) == []
    assert restored.analytics(7, NOW)["visits_24h"] == 1


def test_empty_initialized_stream_keeps_first_real_visit():
    h = History()
    h.ingest("SN", "cat_records", [], NOW)
    assert len(h.ingest("SN", "cat_records", [visit(1)], NOW)) == 1


def test_same_record_ids_on_different_devices_are_distinct():
    h = History()
    h.ingest("SN1", "cat_records", [visit(1, minutes=1)], NOW)
    h.ingest("SN2", "cat_records", [visit(1)], NOW)
    assert h.analytics(7, NOW)["visits_24h"] == 2


def test_legacy_history_and_threshold_migrate_without_double_count():
    h = History(
        {
            "cats": {
                "7": {
                    "poo_duration_threshold_seconds": 90,
                    "events": [{"record_id": "1", "at": NOW.isoformat(), "duration_seconds": 57}],
                }
            }
        }
    )
    h.ingest("SN", "cat_records", [visit(1)], NOW)
    assert h.threshold(7) == 90
    assert h.analytics(7, NOW)["visits_24h"] == 1


def test_rolling_window_and_heuristic_are_distinct():
    h = History()
    h.ingest("SN", "cat_records", [visit(1, minutes=1441), visit(2, duration=101), visit(3, minutes=1)], NOW)
    a = h.analytics(7, NOW)
    assert a["visits_24h"] == 2 and a["pee_visits_24h"] == 1 and a["poo_visits_24h"] == 1
    assert a["duration_24h"] == 158
    assert h.analytics(7, NOW + timedelta(days=2))["visits_24h"] == 0
    for value in (float("nan"), float("inf"), 9, 151):
        with pytest.raises(ValueError):
            h.set_threshold(7, value)


def test_invalid_or_future_records_do_not_poison_history():
    h = History()
    h.ingest("SN", "cat_records", [None, {}, visit(1, minutes=-10), visit(2, duration=-1)], NOW)
    assert h.analytics(7, NOW)["last_visit"] is None
    assert timestamp("2026-11-03 04:00:00") == NOW
    assert remaining_uses({"box_use_times": {"boxUseTimes": 87, "boxFullMax": 30}}) == 0
    assert remaining_uses({"box_use_times": {"boxUseTimes": 0, "boxFullMax": 0}}) is None


def test_older_backfill_cannot_replace_last_box_visit():
    h = History()
    h.ingest("SN", "cat_records", [visit(2)], NOW)
    h.ingest("SN", "cat_records", [visit(1, minutes=2)], NOW)
    assert h.state["box_visits"]["SN"]["at"] == NOW.isoformat()


def test_cover_maintenance_is_not_a_cat():
    current = {"lid_state": 1, "toilet_state": 1, "w_mode_app_name": "IDLE"}
    assert presence({}, current) == (None, True)
    current["lid_state"] = 0
    assert presence({}, current, True) == (None, True)
    current["toilet_state"] = 0
    assert presence({}, current, True) == (False, False)


def test_idle_normalization_preserves_blocked_state():
    for raw, expected in ((1, "PENDING"), (2, "BLOCKED"), (3, "PAUSED")):
        frame = build_risp_frame(dev=2, cmd=0x400, attr=6, seq=2, body=field_varint(2, raw))
        state = summarize_risp_frame(frame)
        assert state["w_state_app_name"] == expected
        assert state["w_state"] == raw


async def test_push_does_not_postpone_rest_fallback(coordinator):
    c = coordinator
    c.data = {"devices": {"SN": {"device": {}, "config": {}}}, "cats": []}
    with (
        patch.object(c, "_schedule_refresh") as refresh,
        patch.object(
            c, "_async_unsub_refresh" if hasattr(c, "_async_unsub_refresh") else "_unschedule_refresh"
        ) as unsubscribe,
    ):
        c.receive_push("SN", {"risp_cmd": 0x400, "w_mode_app_name": "IDLE", "toilet_state": 0, "timestamp": 1})
        refresh.assert_not_called()
        unsubscribe.assert_not_called()
    assert c.data["devices"]["SN"]["mqtt_state"]["cat_inside"] is False


async def test_real_coordinator_preserves_history_on_optional_failure(coordinator):
    c = coordinator
    payload = {
        "devices": {
            "SN": {
                "device": {},
                "cat_records": [visit(1)],
                "device_records": [],
                "fresh": {"cat_records": True, "device_records": True},
            }
        },
        "cats": [{"catInfoId": 7}],
    }
    payload["devices"]["SN"]["cat_records"][0]["eventTime"] = int(datetime.now(UTC).timestamp() * 1000)
    c.client.get_dashboard = MagicMock(return_value=deepcopy(payload))
    c.data = await c._async_update_data()
    assert c.data["cats"][0]["visit_analytics"]["visits_24h"] == 1
    before = deepcopy(c.history.state)
    payload["devices"]["SN"]["cat_records"] = []
    payload["devices"]["SN"]["fresh"]["cat_records"] = False
    c.client.get_dashboard.return_value = deepcopy(payload)
    c.data = await c._async_update_data()
    assert c.history.state["cats"] == before["cats"]


async def test_account_cat_devices_do_not_collide(coordinator):
    c = coordinator
    other = UbpetDataUpdateCoordinator(c.hass, client(), entry=entry("account2"))
    try:
        assert c.cat_identifier("7") != other.cat_identifier("7")
        c.data = {"devices": {}, "cats": [{"catInfoId": 7}]}
        entity = UbpetCatSensor(c, c.entry.entry_id, "7", CAT_SENSORS[0])
        assert entity.unique_id == "account1_cat_7_cat_weight"
        assert entity.available
        c.data["cats"] = []
        assert not entity.available
    finally:
        await other.async_shutdown()


async def test_dynamic_discovery_adds_new_entities_once(coordinator):
    c = coordinator
    c.data = {"devices": {}, "cats": []}
    added = []
    setup_discovery(
        c, c.entry, lambda items: added.extend(items), lambda: [SimpleNamespace(unique_id=k) for k in c.data["devices"]]
    )
    c.data["devices"]["one"] = {"config": {}}
    c.async_update_listeners()
    c.async_update_listeners()
    assert [e.unique_id for e in added] == ["one"]


async def test_commands_require_current_session_state_and_no_cat(coordinator):
    c = coordinator
    c.data = {
        "devices": {
            "SN": {"mqtt_state": {"w_state_app_name": "PENDING", "w_mode_app_name": "IDLE", "cat_inside": False}}
        }
    }
    c.transport.connected = True
    c.transport.connected_since = NOW
    button = UbpetMqttCommandButton(
        c, c.entry.entry_id, "SN", next(d for d in MQTT_BUTTONS if d.service_id == "start_clean_up")
    )
    assert not button.available
    c._last_mqtt_update_at_by_serial["SN"] = NOW
    assert button.available
    c.data["devices"]["SN"]["mqtt_state"]["cat_inside"] = True
    assert not button.available
    with pytest.raises(HomeAssistantError):
        await button.async_press()


async def test_session_takeover_immediately_blocks_rest_login(coordinator):
    c = coordinator
    c.transport._receive({"type_url": "type.googleapis.com/rosa.im.protobuf.ForceOfflineNotification"})
    assert c.transport.yielding
    with pytest.raises(UbpetApiError):
        c.client.ensure_login()


def test_diagnostics_recursively_redact_secrets_and_identifiers():
    original = {
        "APP_KEY": "secret",
        "mqttPassword": "secret",
        "cats": [{"nickname": "Micky", "catInfoId": 7}],
        "serialNumber": "SN",
        "wifiName": "home",
        "firmwareVersion": "v1",
    }
    value = redact(original)
    assert value["APP_KEY"] == value["mqttPassword"] == value["serialNumber"] == "REDACTED"
    assert value["cats"][0]["nickname"] == "REDACTED"
    assert value["firmwareVersion"] == "v1"
    assert original["wifiName"] == "home"


async def test_config_flow_preselects_region_but_does_not_login(coordinator):
    flow = UbpetConfigFlow()
    flow.hass = coordinator.hass
    flow.hass.config.country = "DE"
    form = await flow.async_step_user({"provider": "robotail"})
    assert form["step_id"] == "account"
    fields = {field.schema: field for field in form["data_schema"].schema}
    assert fields["region"].default() == "eu"


async def test_duplicate_account_is_rejected_before_network_login(coordinator):
    from custom_components.ubpet.providers import credentials

    existing = SimpleNamespace(
        entry_id="existing",
        data={"account": "test@example.test", "base_url": endpoint("upet", "eu"), **credentials("upet", "eu")},
    )
    flow = UbpetConfigFlow()
    flow.hass = coordinator.hass
    flow._async_current_entries = MagicMock(return_value=[existing])
    with patch("custom_components.ubpet.config_flow._validate") as validate:
        result = await flow.async_step_account(
            {"country": "DE", "region": "eu", "username": " TEST@example.test ", "password": "x"}
        )
    assert result["reason"] == "already_configured"
    validate.assert_not_called()


async def test_same_email_at_different_providers_creates_independent_entry(coordinator):
    existing = SimpleNamespace(
        entry_id="existing",
        data={"account": "test@example.test", "base_url": endpoint("upet", "eu"), **credentials("upet", "eu")},
    )
    flow = UbpetConfigFlow()
    flow.hass = coordinator.hass
    flow._provider = "robotail"
    flow._async_current_entries = MagicMock(return_value=[existing])
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    with patch("custom_components.ubpet.config_flow._validate", return_value=[]):
        result = await flow.async_step_account(
            {"country": "DE", "region": "eu", "username": "test@example.test", "password": " x "}
        )
    assert result["type"] == "create_entry"
    assert result["data"]["provider"] == "robotail"
    assert result["data"]["password"] == " x "  # spaces can be part of a password


async def test_migration_preserves_all_connection_fields_and_entry_id(coordinator):
    from custom_components.ubpet import async_migrate_entry

    data = {
        "account": "a",
        "password": "x",
        "base_url": endpoint("upet", "ru"),
        "area_code": "RU",
        "device_id": "stable",
        **credentials("upet", "eu"),
    }
    old = SimpleNamespace(version=1, entry_id="stable_entry", data=data)
    coordinator.hass.config_entries = MagicMock()
    assert await async_migrate_entry(coordinator.hass, old)
    kwargs = coordinator.hass.config_entries.async_update_entry.call_args.kwargs
    assert all(kwargs["data"][key] == value for key, value in data.items())
    assert kwargs["version"] == 2 and kwargs["data"]["region"] == "ru"
    assert old.entry_id == "stable_entry"


async def test_persistent_commands_reuse_connection_and_report_only_broker_ack(coordinator):
    c = coordinator
    t = c.transport
    t.connected = True
    t._contacts = {"42": "SN"}
    t._credentials = {"pubTopic": "topic", "uid": "1"}
    t._mqtt = MagicMock()
    t._mqtt.publish.return_value.rc = 0
    t._mqtt.publish.return_value.is_published.return_value = True
    with patch("custom_components.ubpet.transport.mqtt.Client") as constructor:
        for command in ("request_state", "start_clean_up"):
            result = await c.hass.async_add_executor_job(t.send, "SN", command)
            assert result["device_confirmation"] == "pending"
        constructor.assert_not_called()
    assert t._mqtt.publish.call_count == 2
    t._mqtt = None


async def test_delayed_executor_connect_does_not_restart_stopped_transport(coordinator):
    t = coordinator.transport
    t.api.get_im_credentials = MagicMock(
        return_value={"clientId": "id", "mqttUserName": "user", "mqttPassword": "password"}
    )
    t.api.get_im_friends = MagicMock(return_value=[])
    mock_client = MagicMock()
    mock_client.connect.side_effect = lambda *args, **kwargs: setattr(t, "_stopped", True)
    with patch("custom_components.ubpet.transport.mqtt.Client", return_value=mock_client):
        await coordinator.hass.async_add_executor_job(t._open)
    mock_client.loop_start.assert_not_called()
    mock_client.disconnect.assert_called_once()


def test_corrupt_risp_frames_are_rejected():
    frame = bytearray(build_risp_frame(dev=2, cmd=0x400, attr=6, seq=2, body=field_varint(2, 1)))
    frame[-1] ^= 1
    with pytest.raises(ValueError, match="checksum"):
        summarize_risp_frame(bytes(frame))


async def test_optional_endpoint_cache_keeps_values_and_stops_unsupported_polling(coordinator):
    api = coordinator.client
    endpoint_call = MagicMock(return_value={"count": 7})
    assert api._optional("counter", endpoint_call, default={}) == ({"count": 7}, True)
    endpoint_call.side_effect = UbpetApiError(404, {})
    assert api._optional("counter", endpoint_call, default={}) == ({"count": 7}, False)
    endpoint_call.reset_mock()
    assert api._optional("counter", endpoint_call, default={}) == ({"count": 7}, False)
    endpoint_call.assert_not_called()


async def test_shutdown_is_idempotent(coordinator):
    coordinator._history_loaded = True
    await coordinator.async_shutdown()
    await coordinator.async_shutdown()
    coordinator._store.async_save.assert_awaited_once()


async def test_every_platform_can_create_entities_from_null_tolerant_payload(coordinator):
    import importlib

    c = coordinator
    c.data = {
        "devices": {
            "SN": {
                "device": {"deviceName": "Box"},
                "config": {
                    "sensorSwitch": 1,
                    "cameraSwitch": 1,
                    "lightSwitch": 1,
                    "lazyTime": 120,
                    "notifyConfigList": None,
                    "lightTimeConfigList": None,
                    "disturbTimeConfigList": None,
                    "controlBoardSwitch": 0,
                    "litterType": 0,
                    "boxFullAlertSwitch": 1,
                },
                "box_use_times": {"boxFullMax": 30, "boxFullAlert": 25},
                "deodorant": {},
                "online": {},
            }
        },
        "cats": [{"catInfoId": 7, "nickname": "Cat"}],
    }
    c.hass.data.setdefault("ubpet", {})[c.entry.entry_id] = c
    added = []
    for name in ("sensor", "binary_sensor", "number", "switch", "time", "select", "button"):
        module = importlib.import_module("custom_components.ubpet." + name)
        await module.async_setup_entry(c.hass, c.entry, lambda entities: added.extend(entities))
    keys = {entity.unique_id for entity in added}
    assert len({(type(entity).__module__, entity.unique_id) for entity in added}) == len(added)
    assert "account1_cat_7_poo_duration_threshold" in keys
    assert "account1_SN_auto_clean" in keys
    assert "account1_SN_reset_deodorant" in keys
    for entity in added:
        assert entity.device_info["identifiers"]


async def test_wrong_password_is_not_retried_or_hidden_as_optional_error(coordinator):
    from custom_components.ubpet.api import UbpetAuthenticationError

    api = coordinator.client
    with patch.object(api, "_login_with_account_type", side_effect=UbpetApiError(200, {"code": 2002})) as login:
        for _ in range(3):
            with pytest.raises(UbpetAuthenticationError):
                api.ensure_login()
    login.assert_called_once()


async def test_delay_change_does_not_enable_auto_clean(coordinator):
    from custom_components.ubpet.number import UbpetAutoCleanDelayNumber

    c = coordinator
    c.data = {"devices": {"SN": {"config": {"sensorSwitch": 0, "lazyTime": 120}}}}
    entity = UbpetAutoCleanDelayNumber(c, c.entry.entry_id, "SN")
    entity.hass = c.hass
    c.client.set_auto_clean_delay = MagicMock()
    await entity.async_set_native_value(5)
    c.client.set_auto_clean_delay.assert_called_once_with("SN", 5, False)


async def test_old_state_is_refreshed_before_a_movement(coordinator):
    c = coordinator
    c.client.send_mqtt_service = MagicMock()

    async def reply(method, *args):
        c._state_waiters["SN"].set()
        return {}

    with patch.object(c.hass, "async_add_executor_job", side_effect=reply):
        await c.async_ensure_fresh_state("SN")
    assert c._state_waiters == {}
