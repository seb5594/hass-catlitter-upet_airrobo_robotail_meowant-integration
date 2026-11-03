"""The Lovelace cards look entities up by (platform, translation key); those pairs must really exist."""

from __future__ import annotations

import json
import re

from test_history import ROOT

COMPONENT = ROOT / "custom_components/ubpet_cat_litter_hub"
JS = (COMPONENT / "frontend/ubpet-cards.js").read_text(encoding="utf-8")
STRINGS = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))["entity"]


def _referenced_pairs():
    pairs = set(re.findall(r'entity\("(\w+)", "(\w+)"\)', JS))
    pairs |= set(re.findall(r'\["(sensor|binary_sensor|switch|button)", "(\w+)"', JS))
    # Action table: key -> ["<button key>", icon, ...]
    pairs |= {("button", key) for key in re.findall(r'^\s+\w+: \["(\w+)", "mdi:', JS, flags=re.M)}
    # Chips are looked up through a literal map in the editor and through arrays in the renderer.
    pairs |= {
        ("binary_sensor", key)
        for key in re.findall(r'"(cover_open|drum_stuck|drum_not_in_place|scale_fault|camera_fault)"', JS)
    }
    return pairs


def test_cards_only_reference_existing_entity_keys():
    pairs = _referenced_pairs()
    assert len(pairs) > 25, "pattern found too few references; the test would be vacuous"
    missing = sorted(pair for pair in pairs if pair[1] not in STRINGS.get(pair[0], {}))
    assert not missing, missing


def test_device_models_match_the_backend_constants():
    const = (COMPONENT / "const.py").read_text(encoding="utf-8")
    for name in ("MODEL_BOX", "MODEL_CAT"):
        value = re.search(rf'{name} = "([^"]+)"', const).group(1)
        assert f'{name} = "{value}"' in JS


def test_cards_are_offered_in_the_card_picker():
    assert 'type: "ubpet-litter-box-card"' in JS and 'type: "ubpet-cat-card"' in JS
