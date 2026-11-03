"""Render integration brand PNGs from the editable SVG; requires resvg-py."""

from pathlib import Path

import resvg_py

root = Path(__file__).resolve().parents[1]
source = (root / "assets/cat-litter-hub.svg").read_text(encoding="utf-8")
for name, size in [("icon.png", 256), ("icon@2x.png", 512), ("logo.png", 256), ("logo@2x.png", 512)]:
    (root / "custom_components/ubpet_cat_litter_hub/brand" / name).write_bytes(
        resvg_py.svg_to_bytes(svg_string=source, width=size, height=size)
    )
print("Brandgrafiken erzeugt")
