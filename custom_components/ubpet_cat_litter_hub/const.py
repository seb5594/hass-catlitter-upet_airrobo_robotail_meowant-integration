"""Constants shared by the Cat Litter Hub integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "ubpet_cat_litter_hub"
# Domain of the original UPET integration and its forks; their entries can be adopted once.
LEGACY_DOMAIN = "ubpet"

# Config entry data.
CONF_PROVIDER = "provider"
CONF_REGION = "region"
CONF_COUNTRY = "country"
CONF_AREA_CODE = "area_code"
CONF_LEGACY_ENTRY_ID = "legacy_entry_id"
# Fields handed one-to-one to the REST client.
CLIENT_KEYS = ("account", "password", "app_key", "device_id", "base_url", "app_id", "product")


def entry_namespace(entry) -> str:
    """Prefix of all unique IDs. An adopted entry keeps the ID of the entry it replaced."""
    return entry.data.get(CONF_LEGACY_ENTRY_ID) or entry.entry_id


# Options.
OPT_SCAN_INTERVAL = "scan_interval"
OPT_RECORDS_PER_FETCH = "records_per_fetch"
OPT_MQTT_ENABLED = "mqtt_enabled"
DEFAULT_SCAN_INTERVAL = 180
DEFAULT_RECORDS_PER_FETCH = 100

# Event names stay as in the original integration so existing automations keep working.
EVENT_VISIT = "ubpet_visit"
EVENT_BOX_EVENT = "ubpet_box_event"
EVENT_PRESENCE = "ubpet_presence"

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
    getattr(Platform, "TIME", "time"),
    Platform.SELECT,
    Platform.BUTTON,
]
