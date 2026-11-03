"""Set up independent provider accounts with explicit server selection."""

from __future__ import annotations

import uuid

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .api import UbpetApiError, UbpetClient
from .const import (
    CLIENT_KEYS,
    CONF_AREA_CODE,
    CONF_COUNTRY,
    CONF_LEGACY_ENTRY_ID,
    CONF_PROVIDER,
    CONF_REGION,
    DEFAULT_RECORDS_PER_FETCH,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    OPT_MQTT_ENABLED,
    OPT_RECORDS_PER_FETCH,
    OPT_SCAN_INTERVAL,
)
from .legacy import adoptable_entries, entry_data_from_legacy
from .providers import (
    BASIS_COUNTRY,
    BASIS_TIMEZONE,
    PROVIDERS,
    account_unique_id,
    credentials,
    endpoint,
    infer_provider,
    infer_region,
    suggest_region_with_basis,
)


def _validate(data: dict) -> list[dict]:
    client = UbpetClient(**{key: data[key] for key in (*CLIENT_KEYS, CONF_AREA_CODE)})
    client.login()
    return client.get_devices()


def _normalize_country(value) -> str:
    country = str(value).strip().upper()
    if len(country) != 2 or not country.isascii() or not country.isalpha():
        raise ValueError("Country is required")
    return country


class UbpetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self):
        self._provider = "upet"
        self._existing = None

    async def async_step_user(self, user_input=None):
        if adoptable_entries(self.hass):
            return self.async_show_menu(step_id="user", menu_options=["migrate", "provider"])
        return await self.async_step_provider()

    async def async_step_migrate(self, user_input=None):
        legacy = adoptable_entries(self.hass)[0]
        if legacy.state is ConfigEntryState.LOADED:
            return self.async_abort(reason="legacy_still_installed")
        if user_input is None:
            return self.async_show_form(
                step_id="migrate",
                description_placeholders={"title": legacy.title, "count": str(len(adoptable_entries(self.hass)))},
            )
        data = entry_data_from_legacy(legacy)
        await self.async_set_unique_id(account_unique_id(data))
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=legacy.title, data=data)

    async def async_step_provider(self, user_input=None):
        if user_input:
            self._provider = user_input[CONF_PROVIDER]
            return await self.async_step_account()
        return self.async_show_form(
            step_id="provider",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROVIDER, default=self._provider): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[{"value": key, "label": p.label} for key, p in PROVIDERS.items()],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_account(self, user_input=None):
        errors = {}
        old = dict(self._existing.data) if self._existing else {}
        profile = PROVIDERS[self._provider]
        country = old.get(CONF_COUNTRY) or self.hass.config.country
        suggestion, basis = suggest_region_with_basis(country, self.hass.config.time_zone)
        proposed = old.get(CONF_REGION) or suggestion
        region = proposed if proposed in profile.regions else profile.regions[0]
        if user_input:
            try:
                result, errors = await self._async_submit(user_input, old)
                if result:
                    return result
            except (ValueError, KeyError):
                errors["base"] = "invalid_input"
            except UbpetApiError as err:
                errors["base"] = "invalid_auth" if err.status in (200, 400, 401, 403) else "cannot_connect"
            except OSError:
                errors["base"] = "cannot_connect"
        values = user_input or old
        fields = {
            vol.Required(CONF_REGION, default=values.get(CONF_REGION, region)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(profile.regions),
                    translation_key=CONF_REGION,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_COUNTRY,
                **({"default": values.get(CONF_COUNTRY, country)} if values.get(CONF_COUNTRY, country) else {}),
            ): (selector.CountrySelector() if hasattr(selector, "CountrySelector") else selector.TextSelector()),
            vol.Required(CONF_USERNAME, default=values.get(CONF_USERNAME, old.get("account", ""))): str,
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        }
        return self.async_show_form(
            step_id="account",
            data_schema=vol.Schema(fields),
            errors=errors,
            description_placeholders={
                "provider": profile.label,
                "suggestion": _describe_suggestion(suggestion, basis, country, self.hass.config.time_zone),
            },
        )

    async def _async_submit(self, user_input, old):
        """Validate the account form. Returns ``(flow_result, errors)``; exactly one of them is set."""
        profile = PROVIDERS[self._provider]
        country = _normalize_country(user_input[CONF_COUNTRY])
        account = str(user_input[CONF_USERNAME]).strip()
        password = user_input[CONF_PASSWORD]
        if not account or not password:
            raise ValueError("Account and password are required")
        selected_region = user_input[CONF_REGION]
        app = credentials(self._provider, selected_region)
        # Keep custom app credentials of migrated entries in their original tenant.
        if old and self._provider == infer_provider(old) and selected_region == infer_region(old):
            app = {key: old.get(key, value) for key, value in app.items()}
        data = {
            **app,
            CONF_PROVIDER: self._provider,
            CONF_REGION: selected_region,
            CONF_COUNTRY: country,
            CONF_AREA_CODE: country,
            "account": account,
            "password": password,
            "base_url": endpoint(self._provider, selected_region),
            "device_id": old.get("device_id") or uuid.uuid4().hex,
            **({CONF_LEGACY_ENTRY_ID: old[CONF_LEGACY_ENTRY_ID]} if old.get(CONF_LEGACY_ENTRY_ID) else {}),
        }
        identity = account_unique_id(data)
        own_id = self._existing.entry_id if self._existing else None
        if any(
            entry.entry_id != own_id and account_unique_id(dict(entry.data)) == identity
            for entry in self._async_current_entries()
        ):
            return self.async_abort(reason="already_configured"), {}
        devices = await self.hass.async_add_executor_job(_validate, data)
        if not self._existing:
            await self.async_set_unique_id(identity)
            self._abort_if_unique_id_configured()
            title = f"{profile.label} | {selected_region.upper()} | {account}"
            return self.async_create_entry(title=title, data=data), {}
        if error := self._reconfigure_conflict(devices, account, old):
            return None, {"base": error}
        self.hass.config_entries.async_update_entry(self._existing, data=data, unique_id=identity)
        await self.hass.config_entries.async_reload(self._existing.entry_id)
        reason = "reauth_successful" if self.context.get("source") == "reauth" else "reconfigure_successful"
        return self.async_abort(reason=reason), {}

    def _reconfigure_conflict(self, devices, account, old) -> str | None:
        coordinator = self.hass.data.get(DOMAIN, {}).get(self._existing.entry_id)
        known = set((coordinator.data or {}).get("devices", {})) if coordinator else set()
        if known - {d.get("serialNumber") for d in devices}:
            return "missing_devices"
        if account.casefold() != old["account"].strip().casefold():
            return "account_changed"
        return None

    async def async_step_reconfigure(self, user_input=None):
        self._existing = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        self._provider = self._existing.data.get(CONF_PROVIDER, infer_provider(dict(self._existing.data)))
        return await self.async_step_account(user_input)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reconfigure()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return UbpetOptionsFlow(config_entry)


def _describe_suggestion(region: str, basis: str, country: str | None, time_zone: str | None) -> str:
    """Language-neutral hint such as ``EU · DE`` that tells how reliable the pre-selection is."""
    source = {BASIS_COUNTRY: country, BASIS_TIMEZONE: time_zone}.get(basis)
    return f"{region.upper()} · {source}" if source else region.upper()


class UbpetOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        options = self._entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(OPT_SCAN_INTERVAL, default=options.get(OPT_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): (
                        vol.All(vol.Coerce(int), vol.Range(min=60, max=3600))
                    ),
                    vol.Required(
                        OPT_RECORDS_PER_FETCH, default=options.get(OPT_RECORDS_PER_FETCH, DEFAULT_RECORDS_PER_FETCH)
                    ): vol.All(vol.Coerce(int), vol.Range(min=20, max=200)),
                    vol.Required(OPT_MQTT_ENABLED, default=options.get(OPT_MQTT_ENABLED, True)): bool,
                }
            ),
        )
