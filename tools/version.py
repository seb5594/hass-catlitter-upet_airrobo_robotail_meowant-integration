"""Nächsten Berliner Tagesbuild bestimmen; nur die Versionsquelle ändern."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--date", help="Kalendertag JJJJ-MM-TT; Standard: Europe/Berlin")
parser.add_argument("--build", type=int, help="Explizite Tages-Buildnummer ab 1")
args = parser.parse_args()
day = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else datetime.now(ZoneInfo("Europe/Berlin")).date()
prefix = day.strftime("%Y.%m.%d")
path = ROOT / "custom_components/ubpet/manifest.json"
manifest = json.loads(path.read_text(encoding="utf-8"))
tags = subprocess.check_output(["git", "tag", "--list", f"v{prefix}.*"], cwd=ROOT, text=True).splitlines()
pattern = re.compile(re.escape(prefix) + r"\.(\d+)")
previous = [int(m[1]) for tag in [manifest["version"], *tags] if (m := pattern.fullmatch(tag.removeprefix("v")))]
build = args.build if args.build is not None else max(previous, default=0) + 1
if build < 1:
    parser.error("Die Buildnummer muss mindestens 1 sein")
version = f"{prefix}.{build}"
if f"v{version}" in tags:
    parser.error("Für diese Version existiert bereits ein Git-Tag")
manifest["version"] = version
path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(version)
