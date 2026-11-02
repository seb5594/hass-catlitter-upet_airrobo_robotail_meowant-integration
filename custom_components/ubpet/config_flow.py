"""Set up independent provider accounts with explicit server selection."""

from __future__ import annotations

import uuid

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .api import UbpetApiError, UbpetClient
from .const import DOMAIN
from .providers import PROVIDERS, account_unique_id, credentials, endpoint, infer_provider, infer_region, suggest_region


def _validate(data: dict) -> list[dict]:
    client = UbpetClient(
        **{
            key: data[key]
            for key in ("account", "password", "app_key", "device_id", "base_url", "app_id", "product", "area_code")
        }
    )
    client.login()
    return client.get_devices()


class UbpetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self):
        self._provider = "upet"
        self._existing = None

    async def async_step_user(self, user_input=None):
        if user_input:
            self._provider = user_input["provider"]
            return await self.async_step_account()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("provider", default=self._provider): selector.SelectSelector(
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
        country = old.get("country") or self.hass.config.country
        proposed = old.get("region") or suggest_region(country, self.hass.config.time_zone)
        region = proposed if proposed in profile.regions else profile.regions[0]
        if user_input:
            try:
                country = str(user_input["country"]).strip().upper()
                if len(country) != 2 or not country.isascii() or not country.isalpha():
                    raise ValueError("Country is required")
                account = str(user_input[CONF_USERNAME]).strip()
                password = user_input[CONF_PASSWORD]
                if not account or not password:
                    raise ValueError("Account and password are required")
                selected_region = user_input["region"]
                app = credentials(self._provider, selected_region)
                # Keep custom app credentials of migrated entries in their original tenant.
                if old and self._provider == infer_provider(old) and selected_region == infer_region(old):
                    app = {key: old.get(key, value) for key, value in app.items()}
                data = {
                    **app,
                    "provider": self._provider,
                    "region": selected_region,
                    "country": country,
                    "area_code": country,
                    "account": account,
                    "password": password,
                    "base_url": endpoint(self._provider, selected_region),
                    "device_id": old.get("device_id") or uuid.uuid4().hex,
                }
                identity = account_unique_id(data)
                for entry in self._async_current_entries():
                    if (
                        entry.entry_id != (self._existing.entry_id if self._existing else None)
                        and account_unique_id(dict(entry.data)) == identity
                    ):
                        return self.async_abort(reason="already_configured")
                devices = await self.hass.async_add_executor_job(_validate, data)
                if self._existing:
                    coordinator = self.hass.data.get(DOMAIN, {}).get(self._existing.entry_id)
                    known = set((coordinator.data or {}).get("devices", {})) if coordinator else set()
                    reported = {d.get("serialNumber") for d in devices}
                    if known - reported:
                        errors["base"] = "missing_devices"
                    elif account.casefold() != old["account"].strip().casefold():
                        errors["base"] = "account_changed"
                    else:
                        self.hass.config_entries.async_update_entry(self._existing, data=data, unique_id=identity)
                        await self.hass.config_entries.async_reload(self._existing.entry_id)
                        return self.async_abort(
                            reason="reauth_successful"
                            if self.context.get("source") == "reauth"
                            else "reconfigure_successful"
                        )
                else:
                    await self.async_set_unique_id(identity)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"{profile.label} | {selected_region.upper()} | {account}", data=data
                    )
            except (ValueError, KeyError):
                errors["base"] = "invalid_input"
            except UbpetApiError as err:
                errors["base"] = "invalid_auth" if err.status in (200, 400, 401, 403) else "cannot_connect"
            except OSError:
                errors["base"] = "cannot_connect"
        values = user_input or old
        fields = {
            vol.Required("region", default=values.get("region", region)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(profile.regions), translation_key="region", mode=selector.SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Required(
                "country", **({"default": values.get("country", country)} if values.get("country", country) else {})
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
            description_placeholders={"provider": profile.label},
        )

    async def async_step_reconfigure(self, user_input=None):
        self._existing = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        self._provider = self._existing.data.get("provider", infer_provider(dict(self._existing.data)))
        return await self.async_step_account(user_input)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reconfigure()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return UbpetOptionsFlow(config_entry)


class UbpetOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("scan_interval", default=self._entry.options.get("scan_interval", 180)): vol.All(
                        vol.Coerce(int), vol.Range(min=60, max=3600)
                    ),
                    vol.Required(
                        "records_per_fetch", default=self._entry.options.get("records_per_fetch", 100)
                    ): vol.All(vol.Coerce(int), vol.Range(min=20, max=200)),
                    vol.Required("mqtt_enabled", default=self._entry.options.get("mqtt_enabled", True)): bool,
                }
            ),
        )
