"""Every REST client method the integration calls must exist; guards against dead-code removal mistakes."""

from __future__ import annotations

import re

from test_history import ROOT, load

api = load("api")
COMPONENT = ROOT / "custom_components/ubpet_cat_litter_hub"
CALL = re.compile(r"\b(?:client|api)\.((?:get|set|reset|send)_\w+)")


def test_called_client_methods_exist():
    called = {
        (path.name, name)
        for path in COMPONENT.glob("*.py")
        if path.name != "api.py"
        for name in CALL.findall(path.read_text(encoding="utf-8"))
    }
    assert called, "pattern found no client calls; the test would be vacuous"
    missing = sorted((file, name) for file, name in called if not hasattr(api.UbpetClient, name))
    assert not missing, missing
