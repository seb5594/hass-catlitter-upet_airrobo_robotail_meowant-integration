"""Checks that also run without installing Home Assistant."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(
        "pure_" + name, ROOT / "custom_components/ubpet_cat_litter_hub" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


history = load("history")
providers = load("providers")
privacy = load("privacy")
NOW = datetime(2026, 11, 2, 20, tzinfo=timezone.utc)


def record(identity, at=NOW, duration=60):
    return {
        "recordId": identity,
        "eventTime": int(at.timestamp() * 1000),
        "eventType": 3,
        "costTime": duration,
        "catInfoId": 7,
    }


def test_empty_stream_keeps_first_event_after_initialization():
    h = history.History()
    assert not h.ingest("a", "cat_records", [], NOW)
    assert len(h.ingest("a", "cat_records", [record(1)], NOW)) == 1


def test_storage_roundtrip_never_replays_existing_visits():
    import json

    h = history.History()
    h.ingest("a", "cat_records", [record(1)], NOW)
    restored = history.History(json.loads(json.dumps(h.state)))
    assert restored.ingest("a", "cat_records", [record(1)], NOW) == []
    assert restored.analytics(7, NOW)["visits_24h"] == 1


def test_window_expiry_does_not_create_total_increasing_counter():
    h = history.History()
    h.ingest("a", "cat_records", [record(1)], NOW)
    assert h.analytics(7, NOW + timedelta(hours=25))["visits_24h"] == 0


def test_truncated_window_is_reported_instead_of_claiming_completeness():
    h = history.History()
    h.ingest("a", "cat_records", [record(1)], NOW, limit=1)
    assert h.state["streams"]["a:cat_records"]["truncated"]
    assert not h.state["streams"]["a:cat_records"]["complete_24h"]


def test_duration_estimates_recalculate_when_threshold_changes():
    h = history.History()
    h.ingest("a", "cat_records", [record(1, duration=110)], NOW)
    assert h.analytics(7, NOW)["poo_visits_24h"] == 1
    h.set_threshold(7, 120)
    assert h.analytics(7, NOW)["pee_visits_24h"] == 1


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, "invalid", True])
def test_invalid_values_cannot_become_measurements(value):
    assert history.number(value) is None or value == -1
    with pytest.raises(ValueError):
        history.History().set_threshold(7, value)


def test_explicit_region_always_wins_over_location_hint():
    assert providers.suggest_region("DE") == "eu"
    assert providers.endpoint("upet", "na") == "https://apis.airrobo-home.com"
    with pytest.raises(ValueError):
        providers.endpoint("meowant", "eu")


def test_private_values_are_removed_from_nested_lists():
    assert privacy.redact({"devices": [{"app_key": "x", "serialNumber": "a", "wifiName": "b"}]}) == {
        "devices": [{"app_key": "REDACTED", "serialNumber": "REDACTED", "wifiName": "REDACTED"}]
    }
