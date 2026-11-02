"""Account namespaces and explicit cloud regions, independent of Home Assistant."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

APPS = json.loads(Path(__file__).with_name("mobile_apps.json").read_text(encoding="utf-8"))
REGIONS = {
    "eu": "https://apis-eu.airrobo-home.com",
    "na": "https://apis.airrobo-home.com",
    "asia": "https://apis-jp.airrobo-home.com",
    "ru": "https://apis-ru.airrobo-home.com",
}


@dataclass(frozen=True, slots=True)
class Provider:
    label: str
    app: str
    regions: tuple[str, ...]
    fixed_host: str | None = None


PROVIDERS = {
    "upet": Provider("UPET / UBPet", "upet", tuple(REGIONS)),
    "airpet": Provider("AIR PET / AIRROBO", "airpet", tuple(REGIONS)),
    "robotail": Provider("Robotail", "robotail", tuple(REGIONS)),
    "meowant": Provider("Meowant", "meowant", ("na",), REGIONS["na"]),
    "airpet_ubtrobot": Provider("AIR PET (ubtrobot.com, experimental)", "airpet", ("eu", "na", "global", "cn")),
}
UBT_HOSTS = {
    "eu": "https://apis-eu.ubtrobot.com",
    "na": "https://apis-na.ubtrobot.com",
    "global": "https://apis.ubtrobot.com",
    "cn": "https://airpet.ubtrobot.com",
}


def endpoint(provider: str, region: str) -> str:
    profile = PROVIDERS[provider]
    if region not in profile.regions:
        raise ValueError("Unsupported provider/region combination")
    if provider == "airpet_ubtrobot":
        return UBT_HOSTS[region]
    return profile.fixed_host or REGIONS[region]


def credentials(provider: str, region: str) -> dict[str, str]:
    endpoint(provider, region)
    app = "airpet" if provider == "upet" and region == "na" else PROVIDERS[provider].app
    return dict(APPS[app])


def suggest_region(country: str | None, time_zone: str | None = None) -> str:
    country = (country or "").upper()
    if country == "RU":
        return "ru"
    if country in {"US", "CA", "MX", "BR", "PR", "CR", "PA", "GT", "DO"}:
        return "na"
    if country in {"JP", "KR"}:
        return "asia"
    if not country:
        if (time_zone or "").startswith("America/"):
            return "na"
        if time_zone in {"Asia/Tokyo", "Asia/Seoul"}:
            return "asia"
        if time_zone == "Europe/Moscow":
            return "ru"
    return "eu"


def account_unique_id(data: dict) -> str:
    # The actual cloud tenant defines account identity, not its marketing label.
    return ":".join((data["base_url"].rstrip("/").lower(), data["app_id"], data["account"].strip().casefold()))


def infer_provider(data: dict) -> str:
    for name in ("robotail", "meowant", "airpet", "upet"):
        if data.get("app_id") == APPS[PROVIDERS[name].app]["app_id"]:
            return name
    return "upet"


def infer_region(data: dict) -> str:
    for name, url in REGIONS.items():
        if data.get("base_url", "").rstrip("/") == url:
            return name
    return suggest_region(data.get("country") or data.get("area_code"))
