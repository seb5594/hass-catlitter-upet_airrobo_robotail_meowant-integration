"""Check project metadata, translation parity, and Python style."""

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
component = ROOT / "custom_components/ubpet_cat_litter_hub"
manifest = json.loads((component / "manifest.json").read_text(encoding="utf-8"))
assert re.fullmatch(r"\d{4}\.\d{2}\.\d{2}\.[1-9]\d*", manifest["version"]), "Version: JJJJ.MM.TT.Build"
assert manifest["domain"] == component.name == "ubpet_cat_litter_hub"
assert manifest["requirements"] == ["paho-mqtt>=2.1.0"]
apps = json.loads((component / "mobile_apps.json").read_text(encoding="utf-8"))
assert all(set(profile) == {"app_id", "product"} for profile in apps.values()), (
    "Release profiles must not bundle app signing keys"
)
english = json.loads((component / "strings.json").read_text(encoding="utf-8"))
assert english == json.loads((component / "translations/en.json").read_text(encoding="utf-8")), (
    "en.json != strings.json"
)


def flatten(value, prefix=""):
    for key, item in value.items():
        if isinstance(item, dict):
            yield from flatten(item, prefix + key + ".")
        else:
            yield prefix + key, item


def placeholders(text):
    return set(re.findall(r"\{\w+\}", text))


reference = dict(flatten(english))
for path in sorted((component / "translations").glob("*.json")):
    translated = dict(flatten(json.loads(path.read_text(encoding="utf-8"))))
    assert reference.keys() == translated.keys(), f"{path.name}: keys differ from strings.json"
    for key, text in translated.items():
        assert text.strip(), f"{path.name}: {key} is empty"
        assert placeholders(text) == placeholders(reference[key]), f"{path.name}: placeholders differ in {key}"
for path in component.glob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))
# The engine runs project checks before installing development requirements.
if importlib.util.find_spec("ruff") is None:
    subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "ruff==0.17.3"], check=True)
subprocess.run(
    [
        sys.executable,
        "-m",
        "ruff",
        "check",
        "--config",
        ".github/dev/pyproject.toml",
        "custom_components",
        ".github/tests",
        ".github/ha_tests",
        ".github/checks",
        "tools",
    ],
    check=True,
    cwd=ROOT,
)
print("Metadata, translations and style checked")
