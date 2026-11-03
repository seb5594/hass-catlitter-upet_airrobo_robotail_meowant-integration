"""Provider and region registry. All brand specifics live in the JSON files next to this module."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_DIRECTORY = Path(__file__).parent
APPS: dict[str, dict[str, str]] = json.loads((_DIRECTORY / "mobile_apps.json").read_text(encoding="utf-8"))
_REGISTRY = json.loads((_DIRECTORY / "providers.json").read_text(encoding="utf-8"))

REGIONS: dict[str, str] = {name: region["host"] for name, region in _REGISTRY["regions"].items()}
_COUNTRY_REGION = {
    country: name for name, region in _REGISTRY["regions"].items() for country in region.get("countries", ())
}
_TIMEZONE_RULES: list[tuple[str, str]] = [tuple(rule) for rule in _REGISTRY["timezone_rules"]]
DEFAULT_REGION: str = _REGISTRY["default_region"]

# Where a region suggestion came from; shown to the user so a guess is recognisable as one.
BASIS_COUNTRY = "country"
BASIS_TIMEZONE = "time_zone"
BASIS_DEFAULT = "default"


@dataclass(frozen=True, slots=True)
class Provider:
    label: str
    app: str
    regions: tuple[str, ...]
    # Overrides for individual regions; everything else falls back to the shared tables.
    hosts: dict[str, str] = field(default_factory=dict)
    region_apps: dict[str, str] = field(default_factory=dict)

    def endpoint(self, region: str) -> str:
        if region not in self.regions:
            raise ValueError("Unsupported provider/region combination")
        return self.hosts.get(region) or REGIONS[region]

    def app_for(self, region: str) -> str:
        return self.region_apps.get(region, self.app)


PROVIDERS: dict[str, Provider] = {
    key: Provider(
        label=entry["label"],
        app=entry["app"],
        regions=tuple(entry["regions"]),
        hosts=entry.get("hosts", {}),
        region_apps=entry.get("region_apps", {}),
    )
    for key, entry in _REGISTRY["providers"].items()
}
# Order in which an existing entry's app ID is matched back to a provider.
_INFERENCE_ORDER = ("robotail", "meowant", "airpet", "upet")


def endpoint(provider: str, region: str) -> str:
    return PROVIDERS[provider].endpoint(region)


def credentials(provider: str, region: str) -> dict[str, str]:
    profile = PROVIDERS[provider]
    profile.endpoint(region)
    return dict(APPS[profile.app_for(region)])


def suggest_region_with_basis(country: str | None, time_zone: str | None = None) -> tuple[str, str]:
    """Pre-select a region from the Home Assistant country, then its time zone. Never authoritative."""
    if region := _COUNTRY_REGION.get((country or "").upper()):
        return region, BASIS_COUNTRY
    for prefix, region in _TIMEZONE_RULES:
        if (time_zone or "").startswith(prefix):
            return region, BASIS_TIMEZONE
    return DEFAULT_REGION, BASIS_DEFAULT


def suggest_region(country: str | None, time_zone: str | None = None) -> str:
    return suggest_region_with_basis(country, time_zone)[0]


def account_unique_id(data: dict) -> str:
    # The actual cloud tenant defines account identity, not its marketing label.
    return ":".join((data["base_url"].rstrip("/").lower(), data["app_id"], data["account"].strip().casefold()))


def infer_provider(data: dict) -> str:
    for name in _INFERENCE_ORDER:
        if data.get("app_id") == APPS[PROVIDERS[name].app]["app_id"]:
            return name
    return "upet"


def infer_region(data: dict) -> str:
    base_url = data.get("base_url", "").rstrip("/")
    for name, host in REGIONS.items():
        if base_url == host:
            return name
    return suggest_region(data.get("country") or data.get("area_code"))
