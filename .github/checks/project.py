"""Projektregeln: konsistente Metadaten, Übersetzungen und Python-Stil."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
component = ROOT / "custom_components/ubpet"
manifest = json.loads((component / "manifest.json").read_text(encoding="utf-8"))
assert re.fullmatch(r"\d{4}\.\d{2}\.\d{2}\.[1-9]\d*", manifest["version"]), "Version: JJJJ.MM.TT.Build"
assert manifest["domain"] == "ubpet", "Domain für bestehende Einträge beibehalten"
assert manifest["requirements"] == ["paho-mqtt==2.1.0"]
english = json.loads((component / "strings.json").read_text(encoding="utf-8"))
german = json.loads((component / "translations/de.json").read_text(encoding="utf-8"))


def keys(value, prefix=""):
    return {prefix + key for key in value} | {
        child for key, item in value.items() if isinstance(item, dict) for child in keys(item, prefix + key + ".")
    }


assert keys(english) == keys(german), "Deutsche Übersetzungen sind unvollständig"
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
print("Metadaten, deutsche Texte und Stil geprüft")
