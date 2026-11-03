"""Serve the Lovelace cards and load them in every frontend session; no manual resource entry needed."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
CARDS_FILE = Path(__file__).parent / "frontend" / "ubpet-cards.js"
CARDS_URL = f"/{DOMAIN}/ubpet-cards.js"
_REGISTERED = f"{DOMAIN}_cards_registered"


async def async_register_cards(hass: HomeAssistant) -> None:
    """Idempotent: the first config entry registers the file, later ones do nothing."""
    if hass.data.get(_REGISTERED) or getattr(hass, "http", None) is None:
        return
    try:
        from homeassistant.components.frontend import add_extra_js_url
    except ImportError:  # headless installations without the frontend
        return
    hass.data[_REGISTERED] = True
    await _async_serve(hass)
    version = (await async_get_integration(hass, DOMAIN)).version
    # The version in the URL makes browsers fetch the new file after every update.
    add_extra_js_url(hass, f"{CARDS_URL}?v={version}")
    _LOGGER.debug("Registered Lovelace cards at %s", CARDS_URL)


async def _async_serve(hass: HomeAssistant) -> None:
    try:
        from homeassistant.components.http import StaticPathConfig
    except ImportError:  # Home Assistant before 2024.7
        hass.http.register_static_path(CARDS_URL, str(CARDS_FILE), cache_headers=True)
        return
    await hass.http.async_register_static_paths([StaticPathConfig(CARDS_URL, str(CARDS_FILE), cache_headers=True)])
