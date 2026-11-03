"""One vendor MQTT session per account for push updates and commands."""

from __future__ import annotations

import asyncio
import logging
import random
import ssl
import time
from datetime import datetime, timezone
from threading import Lock

import paho.mqtt.client as mqtt

from .api import UbpetAuthenticationError
from .compat import start_reauth
from .mqtt import decode_mqtt_payload_safely, mqtt_endpoint, resolve_service_payload

UTC = timezone.utc


_LOGGER = logging.getLogger(__name__)


class AccountTransport:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.api = coordinator.client
        self.hass = coordinator.hass
        self._mqtt = None
        self._task = None
        self._ready = asyncio.Event()
        self._ended = asyncio.Event()
        self._stopped = False
        self._yielding = False
        self._contacts = {}
        self._credentials = {}
        self._connected_at = 0.0
        self._token = None
        self._delay = 0
        self._unavailable_logged = False
        self.connected = False
        self.connected_since = None
        self._send_lock = Lock()
        self.api.mqtt_sender = self.send

    @property
    def yielding(self):
        return self._yielding

    def start(self):
        if self._task is None:
            self._task = self.coordinator.entry.async_create_background_task(
                self.hass, self._run(), "Cat litter account MQTT"
            )

    async def stop(self):
        self._stopped = True
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        await self._close()

    def _open(self):
        if self._stopped:
            return
        self.api.auth_paused_until = 0
        self._credentials = self.api.get_im_credentials()
        self._contacts = {
            str(f["userId"]): f["userName"] for f in self.api.get_im_friends() if f.get("userId") and f.get("userName")
        }
        self._token = self.api.auth.token if self.api.auth else None
        c = self._credentials
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=str(c["clientId"]),
            protocol=mqtt.MQTTv311,
            reconnect_on_failure=False,
        )
        client.username_pw_set(str(c["mqttUserName"]), str(c["mqttPassword"]))
        client.tls_set_context(ssl.create_default_context())
        client.on_connect = self._on_connect
        client.on_subscribe = self._on_subscribe
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        host, port, _ = mqtt_endpoint(self.api.base_url, c)
        client.connect(host, port, keepalive=30)
        if self._stopped:
            client.disconnect()
            return
        self._mqtt = client
        client.loop_start()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            self.hass.loop.call_soon_threadsafe(self._ended.set)
            return
        client.subscribe(str(self._credentials["subTopic"]), qos=1)

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties):
        event = self._ended if any(code.is_failure for code in reason_codes) else self._ready
        self.hass.loop.call_soon_threadsafe(event.set)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.hass.loop.call_soon_threadsafe(self._disconnected)

    def _disconnected(self):
        self.connected = False
        self._ended.set()
        self.coordinator.async_update_listeners()

    def _on_message(self, client, userdata, message):
        if len(message.payload) > 262144:
            return
        decoded = decode_mqtt_payload_safely(message.payload)
        self.hass.loop.call_soon_threadsafe(self._receive, decoded)

    def _receive(self, decoded):
        if self._stopped:
            return
        if decoded.get("type_url", "").endswith(".ForceOfflineNotification"):
            self._yielding = True
            # Block REST login immediately, before the supervisor schedules reconnect.
            self.api.auth_paused_until = time.monotonic() + 1800
            self._ended.set()
            return
        uid = decoded.get("status_uid") or decoded.get("from_uid")
        serial = self._contacts.get(str(uid))
        if serial:
            self.coordinator.receive_push(serial, decoded)

    async def _close(self):
        client, self._mqtt = self._mqtt, None
        self.connected = False
        if client:
            await self.hass.async_add_executor_job(self._close_client, client)

    @staticmethod
    def _close_client(client):
        client.disconnect()
        client.loop_stop()

    async def _run(self):
        try:
            while not self._stopped:
                self._ready.clear()
                self._ended.clear()
                self._connected_at = 0
                try:
                    await self.hass.async_add_executor_job(self._open)
                    # A failure before SUBACK should also end setup promptly.
                    ready = asyncio.create_task(self._ready.wait())
                    ended = asyncio.create_task(self._ended.wait())
                    try:
                        await asyncio.wait({ready, ended}, timeout=20, return_when=asyncio.FIRST_COMPLETED)
                        if not self._ready.is_set() or self._ended.is_set():
                            raise OSError("MQTT connection not ready")
                    finally:
                        for task in (ready, ended):
                            task.cancel()
                        await asyncio.gather(ready, ended, return_exceptions=True)
                    self.connected = True
                    self.connected_since = datetime.now(UTC)
                    self._yielding = False
                    self._connected_at = time.monotonic()
                    if self._unavailable_logged:
                        _LOGGER.info("Cat litter account MQTT connection restored")
                    self._unavailable_logged = False
                    self.coordinator.async_update_listeners()
                    for serial in (self.coordinator.data or {}).get("devices", {}):
                        await self.hass.async_add_executor_job(self.send, serial, "request_state")
                    self.coordinator.schedule_refresh()
                    await self._ended.wait()
                except UbpetAuthenticationError:
                    self._stopped = True
                    start_reauth(self.hass, self.coordinator.entry)
                    return
                except (OSError, RuntimeError, KeyError, ValueError):
                    if not self._unavailable_logged:
                        _LOGGER.warning("Cat litter MQTT unavailable; retrying with backoff")
                        self._unavailable_logged = True
                finally:
                    await self._close()
                own_login = self.api.auth is not None and self.api.auth.token != self._token
                healthy = self._connected_at and time.monotonic() - self._connected_at >= 600
                self._delay = 5 if own_login else (60 if healthy or not self._delay else min(1800, self._delay * 2))
                delay = self._delay * random.uniform(1, 1.1)
                # Also yield after an unexplained short disconnect: avoid login ping-pong.
                self._yielding = not own_login
                if self._yielding:
                    self.api.auth_paused_until = time.monotonic() + delay
                await asyncio.sleep(delay)
        finally:
            await self._close()

    def send(self, serial, service):
        with self._send_lock:
            return self._send(serial, service)

    def _send(self, serial, service):
        client = self._mqtt
        if not self.connected or client is None or self._yielding:
            raise RuntimeError("Vendor MQTT session is unavailable")
        target = next((uid for uid, sn in self._contacts.items() if sn == serial), None)
        if target is None:
            raise RuntimeError("Device has no MQTT contact")
        c = self._credentials
        sender = c.get("uid") or c.get("userId") or (self.api.auth.user_id if self.api.auth else None)
        if sender is None:
            raise RuntimeError("Account has no MQTT sender")
        parts = resolve_service_payload(service, seq=None, from_uid=str(sender), to_uid=target)
        result = client.publish(str(c["pubTopic"]), parts.im_message, qos=1)
        result.wait_for_publish(timeout=5)
        if result.rc != mqtt.MQTT_ERR_SUCCESS or not result.is_published():
            raise RuntimeError("MQTT command was not acknowledged by broker")
        return {
            "service_id": service,
            "seq": parts.seq,
            "cid": parts.cid,
            "received_messages": [],
            "delivery_status": "broker_acknowledged",
            "device_confirmation": "pending",
        }
