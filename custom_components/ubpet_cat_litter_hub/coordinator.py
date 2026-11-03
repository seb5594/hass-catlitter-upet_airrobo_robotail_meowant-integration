"""Account coordinator: REST fallback, persistent push and durable visit history."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import UbpetApiError, UbpetAuthenticationError
from .compat import SUPPORTS_ALWAYS_UPDATE, SUPPORTS_EXPLICIT_ENTRY
from .const import (
    CONF_LEGACY_ENTRY_ID,
    DEFAULT_RECORDS_PER_FETCH,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_BOX_EVENT,
    EVENT_PRESENCE,
    EVENT_VISIT,
    LEGACY_DOMAIN,
    OPT_RECORDS_PER_FETCH,
    OPT_SCAN_INTERVAL,
    entry_namespace,
)
from .history import History, presence, timestamp
from .providers import PROVIDERS
from .transport import AccountTransport

UTC = timezone.utc


_LOGGER = logging.getLogger(__name__)


class UbpetDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, client, *, entry):
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            **({"config_entry": entry} if SUPPORTS_EXPLICIT_ENTRY else {}),
            update_interval=timedelta(seconds=entry.options.get(OPT_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
            **({"always_update": False} if SUPPORTS_ALWAYS_UPDATE else {}),
        )
        if self.config_entry is None:
            self.config_entry = entry
            entry.async_on_unload(self.async_shutdown)
        self.client = client
        self.entry = entry
        self.client.records_per_fetch = entry.options.get(OPT_RECORDS_PER_FETCH, DEFAULT_RECORDS_PER_FETCH)
        self.transport = AccountTransport(self)
        self._store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.visit_analytics")
        self._legacy_store = (
            Store(hass, 1, f"{LEGACY_DOMAIN}.{self.namespace}.visit_analytics")
            if entry.data.get(CONF_LEGACY_ENTRY_ID)
            else None
        )
        self.history = History()
        self._history_loaded = False
        self._last_rest_update_at = None
        self._last_mqtt_update_at_by_serial = {}
        self._mqtt_state_by_serial = {}
        self._presence_suppressed = {}
        self._cancel_refresh = None
        self._stopping = False
        self._state_waiters = {}

    async def _async_update_data(self):
        if not self._history_loaded:
            self.history = History(await self._load_stored_history())
            self._history_loaded = True
        if self.transport.yielding and self.data:
            return self.data
        try:
            data = await self.hass.async_add_executor_job(self.client.get_dashboard)
        except UbpetApiError as err:
            if isinstance(err, UbpetAuthenticationError) or err.status == 401:
                raise ConfigEntryAuthFailed("Account authentication failed; check provider and region") from err
            raise UpdateFailed(str(err)) from err
        except (OSError, RuntimeError) as err:
            raise UpdateFailed(type(err).__name__) from err
        now = datetime.now(UTC)
        self._last_rest_update_at = now
        for serial, item in data.get("devices", {}).items():
            self._ingest_records(serial, item, now)
            item["last_visit"] = self.history.state["box_visits"].get(serial)
            item["history_truncated"] = any(
                self.history.state["streams"].get(f"{serial}:{kind}", {}).get("truncated", False)
                for kind in ("cat_records", "device_records")
            )
            if serial in self._mqtt_state_by_serial:
                item["mqtt_state"] = self._mqtt_state_by_serial[serial]
            item["runtime_state"] = {
                "last_rest_update_at": now,
                "last_mqtt_update_at": self.last_mqtt_update_at(serial),
            }
        self._attach_analytics(data, now)
        self._store.async_delay_save(lambda: self.history.state, 10)
        return data

    def _ingest_records(self, serial, item, now):
        for kind, event_name in (("cat_records", EVENT_VISIT), ("device_records", EVENT_BOX_EVENT)):
            if not item.get("fresh", {}).get(kind):
                continue
            for event in self.history.ingest(serial, kind, item.get(kind), now, self.client.records_per_fetch):
                self.hass.bus.async_fire(event_name, {"entry_id": self.entry.entry_id, **event})

    def _attach_analytics(self, data, now):
        """Derive per-cat and per-box aggregates from the stored history; "today" follows the HA time zone."""
        day_start = dt_util.start_of_local_day().astimezone(UTC)
        cats = data.get("cats", [])
        for cat in cats:
            cat["visit_analytics"] = self.history.analytics(cat.get("catInfoId"), now, day_start)
        nicknames = {str(cat.get("catInfoId")): cat.get("nickname") for cat in cats}
        for serial, item in data.get("devices", {}).items():
            reset_at = timestamp((item.get("box_use_times") or {}).get("boxUseTimesResetTime"))
            analytics = self.history.box_analytics(serial, now, day_start, reset_at)
            analytics["last_used_by"] = nicknames.get(str(analytics.pop("last_visit_cat_id")))
            item["box_analytics"] = analytics

    def receive_push(self, serial, decoded):
        if self._stopping or serial not in (self.data or {}).get("devices", {}):
            return
        if "online_status" in decoded:
            status = decoded["online_status"]
            if status not in ("status/online", "status/offline"):
                return
            data = dict(self.data)
            data["devices"] = dict(data["devices"])
            item = dict(data["devices"][serial])
            item["online"] = {"online": status == "status/online"}
            data["devices"][serial] = item
            self.data = data
            self.async_update_listeners()
            return
        cmd = decoded.get("risp_cmd")
        if cmd in (0x3FF, 2535):
            self.schedule_refresh()
        if cmd not in (0x3FD, 0x400):
            return
        # Discard out-of-order or replayed snapshots without advancing last-update sensors.
        state = {
            k: v for k, v in decoded.items() if not k.endswith("_hex") and k not in ("cid", "gid", "created_at_ms")
        }
        previous = self._mqtt_state_by_serial.get(serial, {})
        if state.get("timestamp") and previous.get("timestamp") and state["timestamp"] < previous["timestamp"]:
            return
        inside, suppressed = presence(previous, state, self._presence_suppressed.get(serial, False))
        self._presence_suppressed[serial] = suppressed
        state["cat_inside"] = inside
        old_inside = previous.get("cat_inside")
        if old_inside is not None and inside is not None and inside != old_inside:
            self.hass.bus.async_fire(
                EVENT_PRESENCE,
                {
                    "entry_id": self.entry.entry_id,
                    "serial_number": serial,
                    "present": inside,
                    "timestamp": state.get("timestamp"),
                },
            )
            if not inside:
                self.schedule_refresh()
        self._mqtt_state_by_serial[serial] = state
        self._last_mqtt_update_at_by_serial[serial] = datetime.now(UTC)
        if waiter := self._state_waiters.get(serial):
            waiter.set()
        data = dict(self.data)
        data["devices"] = dict(data["devices"])
        item = dict(data["devices"][serial])
        item["mqtt_state"] = state
        item["runtime_state"] = {
            "last_rest_update_at": self._last_rest_update_at,
            "last_mqtt_update_at": self.last_mqtt_update_at(serial),
        }
        data["devices"][serial] = item
        self.data = data
        self.async_update_listeners()

    async def async_ensure_fresh_state(self, serial):
        last = self.last_mqtt_update_at(serial)
        if last and (datetime.now(UTC) - last).total_seconds() <= 5:
            return
        waiter = self._state_waiters.setdefault(serial, asyncio.Event())
        waiter.clear()
        try:
            await self.hass.async_add_executor_job(self.client.send_mqtt_service, serial, "request_state")
            await asyncio.wait_for(waiter.wait(), timeout=10)
        except asyncio.TimeoutError as err:
            raise RuntimeError("No fresh device state received; movement was not sent") from err
        finally:
            self._state_waiters.pop(serial, None)

    def schedule_refresh(self, delay=3):
        if self._cancel_refresh or self._stopping:
            return

        def refresh(_now):
            self._cancel_refresh = None
            self.entry.async_create_background_task(self.hass, self.async_request_refresh(), "Cat litter REST refresh")

        self._cancel_refresh = async_call_later(self.hass, delay, refresh)

    async def async_shutdown(self):
        if self._stopping:
            return
        self._stopping = True
        if self._cancel_refresh:
            self._cancel_refresh()
            self._cancel_refresh = None
        await self.transport.stop()
        if self._history_loaded:
            await self._store.async_save(self.history.state)
        if shutdown := getattr(super(), "async_shutdown", None):
            await shutdown()
        else:
            self._unschedule_refresh()
            self._debounced_refresh.async_cancel()

    @property
    def namespace(self):
        return entry_namespace(self.entry)

    async def _load_stored_history(self):
        stored = await self._store.async_load()
        if stored is None and self._legacy_store is not None:
            stored = await self._legacy_store.async_load()
        return stored

    @property
    def provider_label(self):
        return PROVIDERS.get(self.entry.data.get("provider", "upet"), PROVIDERS["upet"]).label

    def cat_identifier(self, cat_id):
        return f"cat_{self.namespace}_{cat_id}"

    @property
    def last_rest_update_at(self):
        return self._last_rest_update_at

    def last_mqtt_update_at(self, serial):
        return self._last_mqtt_update_at_by_serial.get(serial)

    def cat_poo_duration_threshold(self, cat_id):
        return self.history.threshold(cat_id)

    async def async_set_cat_poo_duration_threshold(self, cat_id, seconds):
        self.history.set_threshold(cat_id, seconds)
        self._attach_analytics(self.data or {}, datetime.now(UTC))
        self._store.async_delay_save(lambda: self.history.state, 2)
        self.async_update_listeners()

    def store_mqtt_result(self, serial, result):
        # Commands are confirmed only by device pushes, never an optimistic work state.
        return False

    def start_mqtt_state_poll(self, serial, *, fast=False):
        self.schedule_refresh()
