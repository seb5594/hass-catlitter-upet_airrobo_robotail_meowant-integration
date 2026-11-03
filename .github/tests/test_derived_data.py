"""Provider registry, reminder weekdays and box/cat aggregates; runs without Home Assistant."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from test_history import ROOT, load

box_config = load("box_config")
history = load("history")
providers = load("providers")

NOW = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
DAY_START = datetime(2026, 11, 3, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("country", "zone", "region", "basis"),
    [
        ("DE", "Europe/Berlin", "eu", providers.BASIS_COUNTRY),
        ("CH", None, "eu", providers.BASIS_COUNTRY),
        ("US", "America/Chicago", "na", providers.BASIS_COUNTRY),
        ("BR", None, "na", providers.BASIS_COUNTRY),
        ("KR", None, "asia", providers.BASIS_COUNTRY),
        ("RU", "Europe/Moscow", "ru", providers.BASIS_COUNTRY),
        # Unlisted country: the time zone decides, and the result is flagged as a weaker guess.
        ("AU", "Australia/Sydney", "asia", providers.BASIS_TIMEZONE),
        ("EG", "Africa/Cairo", "eu", providers.BASIS_TIMEZONE),
        ("AE", "Asia/Dubai", "eu", providers.BASIS_COUNTRY),
        (None, "Asia/Tokyo", "asia", providers.BASIS_TIMEZONE),
        (None, None, "eu", providers.BASIS_DEFAULT),
        ("", "Mars/Olympus", "eu", providers.BASIS_DEFAULT),
    ],
)
def test_region_suggestion_reports_its_basis(country, zone, region, basis):
    assert providers.suggest_region_with_basis(country, zone) == (region, basis)


def test_every_provider_region_resolves_to_a_host_and_app_profile():
    for key, provider in providers.PROVIDERS.items():
        assert provider.regions, key
        for region in provider.regions:
            assert providers.endpoint(key, region).startswith("https://")
            assert {"app_id", "app_key", "product"} <= set(providers.credentials(key, region))


def test_overrides_are_applied_per_region_only():
    assert providers.credentials("upet", "na") == providers.APPS["airpet"]
    assert providers.credentials("upet", "eu") == providers.APPS["upet"]
    assert providers.endpoint("airpet_ubtrobot", "global") == "https://apis.ubtrobot.com"
    assert providers.endpoint("meowant", "na") == providers.REGIONS["na"]


def test_weekday_presets_and_custom_masks():
    assert box_config.mask_preset(0) == "off"
    assert box_config.mask_preset(127) == "every_day"
    assert box_config.mask_preset(31) == "weekdays"
    assert box_config.mask_preset(96) == "weekend"
    assert box_config.mask_preset(1 | 4) == box_config.CUSTOM_PRESET
    assert box_config.mask_days(1 | 4 | 64) == ["monday", "wednesday", "sunday"]
    assert box_config.reminder_mask({"period": "bad"}) == 0
    assert box_config.reminder_mask({"period": 255}) == 127  # bits outside the week are ignored


def test_period_and_reminder_lookups_tolerate_null_lists():
    assert box_config.empty_waste_bin_reminder_config({"notifyConfigList": None}) is None
    assert box_config.first_period_config({"lightTimeConfigList": None}, "lightTimeConfigList") is None
    assert box_config.period_config_id({"lightTimeConfigId": 5}) == 5
    assert box_config.period_config_id({}) is None


def _visit(identity, at, cat=7, duration=50, weight=4.2):
    return {
        "recordId": identity,
        "eventTime": int(at.timestamp() * 1000),
        "eventType": 3,
        "costTime": duration,
        "catInfoId": cat,
        "weight": weight,
    }


def _clean(identity, at):
    return {"recordId": identity, "eventTime": int(at.timestamp() * 1000), "eventType": 31}


def _ingested(visits=(), cleans=()):
    state = history.History()
    state.ingest("SN", "cat_records", [], NOW)  # first sight of a stream is silent (initial backfill)
    state.ingest("SN", "device_records", [], NOW)
    events = state.ingest("SN", "cat_records", list(visits), NOW) + state.ingest(
        "SN", "device_records", list(cleans), NOW
    )
    return state, events


def test_box_aggregates_count_today_in_local_day_and_since_reset():
    state, _ = _ingested(
        visits=[_visit("a", NOW - timedelta(hours=1)), _visit("b", NOW - timedelta(days=1))],
        cleans=[
            _clean("c1", NOW - timedelta(hours=2)),
            _clean("c2", NOW - timedelta(days=2)),
            _clean("c3", NOW - timedelta(hours=1)),
        ],
    )
    result = state.box_analytics("SN", NOW, DAY_START, bin_reset_at=NOW - timedelta(days=1))
    assert result["visits_today"] == 1
    assert result["cleans_today"] == 2
    assert result["last_clean"] == NOW - timedelta(hours=1)
    assert result["cleans_since_bin_reset"] == 2
    assert state.box_analytics("SN", NOW, DAY_START)["cleans_since_bin_reset"] is None  # reset time unknown


def test_cleanings_are_not_double_counted_when_records_repeat():
    state, _ = _ingested(cleans=[_clean("c1", NOW - timedelta(hours=2))])
    state.ingest("SN", "device_records", [_clean("c1", NOW - timedelta(hours=2))], NOW)
    assert len(state.state["box_cleanings"]["SN"]) == 1


def test_box_events_carry_a_readable_name_only_when_the_code_is_known():
    _, events = _ingested(
        visits=[_visit("a", NOW - timedelta(hours=1))], cleans=[_clean("c1", NOW - timedelta(hours=1))]
    )
    assert {e["event_name"] for e in events} == {"cat_visit", "clean_finished"}
    state = history.History()
    state.ingest("SN", "device_records", [], NOW)
    unknown = state.ingest(
        "SN", "device_records", [{"recordId": "x", "eventTime": int(NOW.timestamp() * 1000), "eventType": 99}], NOW
    )
    assert "event_name" not in unknown[0]


def test_cat_analytics_report_today_and_last_measured_weight():
    state, _ = _ingested(
        visits=[
            _visit("a", NOW - timedelta(days=2), weight=4.0),
            _visit("b", NOW - timedelta(hours=3), weight=4.3),
            _visit("c", NOW - timedelta(hours=1), weight=None),
        ]
    )
    result = state.analytics(7, NOW, DAY_START)
    assert result["visits_today"] == 2
    assert result["last_visit_weight"] == 4.3  # the newest visit that actually carried a weight
    assert state.analytics(7, NOW)["visits_today"] is None


def test_component_translations_and_registry_files_are_valid_json():
    import json

    for name in ("providers.json", "mobile_apps.json", "strings.json"):
        json.loads((ROOT / "custom_components/ubpet_cat_litter_hub" / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("mode", "state", "expected"),
    [
        ("IDLE", "RUNNING", "PENDING"),  # reported by CrazzyBerg/upet-hass#4 on a real box
        ("IDLE", "PENDING", "PENDING"),
        ("IDLE", "BLOCKED", "BLOCKED"),
        ("CLEANING", "RUNNING", "RUNNING"),
        ("CLEANING", "PAUSED", "PAUSED"),
        (None, None, None),
    ],
)
def test_idle_mode_with_running_state_counts_as_idle(mode, state, expected):
    assert box_config.effective_work_state(mode, state) == expected
