from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .box_config import effective_work_state
from .compat import description_is_frozen, translated_error
from .const import DOMAIN
from .coordinator import UbpetDataUpdateCoordinator
from .entities import UbpetDeviceEntity, setup_discovery

REST_REQUEST_SERVICE = "__rest_request"
RESET_WASTE_BIN_SERVICE = "__reset_waste_bin"
MOVEMENT_SERVICES = {"start_clean_up", "start_flatten", "start_rise", "start_drop", "resume_clean_up", "resume_flatten"}


@dataclass(frozen=description_is_frozen(ButtonEntityDescription), kw_only=True)
class UbpetMqttButtonDescription(ButtonEntityDescription):
    service_id: str


_DIAG = EntityCategory.DIAGNOSTIC
_CONFIG = EntityCategory.CONFIG
_RESET_DEODORANT = "__reset_deodorant"

# The key is also the registry suffix and the translation key.
MQTT_BUTTONS = tuple(
    UbpetMqttButtonDescription(
        key=key, translation_key=key, name=name, icon=icon, service_id=service,
        entity_category=category, entity_registry_enabled_default=enabled,
    )
    for key, name, icon, service, category, enabled in (
        ("rest_request", "REST request", "mdi:cloud-refresh", REST_REQUEST_SERVICE, _DIAG, True),
        ("mqtt_request_state", "Request state", "mdi:refresh", "request_state", _DIAG, True),
        ("reset_waste_bin", "Reset waste bin", "mdi:delete-empty", RESET_WASTE_BIN_SERVICE, _CONFIG, True),
        ("mqtt_start_clean_up", "Start clean", "mdi:broom", "start_clean_up", None, True),
        ("mqtt_pause_clean_up", "Pause clean", "mdi:pause", "pause_clean_up", None, True),
        ("mqtt_resume_clean_up", "Resume clean", "mdi:play", "resume_clean_up", None, True),
        ("mqtt_start_flatten", "Flatten", "mdi:format-align-middle", "start_flatten", None, True),
        ("mqtt_pause_flatten", "Pause flatten", "mdi:pause", "pause_flatten", None, True),
        ("mqtt_resume_flatten", "Resume flatten", "mdi:play", "resume_flatten", None, True),
        ("mqtt_start_rise", "Raise litter rake", "mdi:arrow-up-bold", "start_rise", None, False),
        ("mqtt_start_drop", "Lower litter rake", "mdi:arrow-down-bold", "start_drop", None, False),
        ("reset_deodorant", "Reset deodorant", "mdi:air-filter", _RESET_DEODORANT, _CONFIG, True),
    )
)
_REST_COMMANDS = {REST_REQUEST_SERVICE, RESET_WASTE_BIN_SERVICE, _RESET_DEODORANT}
_REQUIRED_STATE = {
    "start_clean_up": (None, "PENDING"),
    "start_flatten": (None, "PENDING"),
    "start_rise": (None, "PENDING"),
    "start_drop": ("RAKING_UP", "PAUSED"),
    "pause_clean_up": ("CLEANING", "RUNNING"),
    "resume_clean_up": ("CLEANING", "PAUSED"),
    "pause_flatten": ("SMOOTHING", "RUNNING"),
    "resume_flatten": ("SMOOTHING", "PAUSED"),
}
_INTERLOCKS = {
    "toilet_state": (1,), "weigh_sensor": (1,), "motor_state": (1, 2, 3, 4),
    "foreign_state": (1,), "lid_state": (1,), "box_state": (1,),
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: UbpetDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    def build():
        return [
            UbpetMqttCommandButton(coordinator, coordinator.namespace, serial, description)
            for serial in coordinator.data.get("devices", {})
            for description in MQTT_BUTTONS
        ]

    setup_discovery(coordinator, entry, async_add_entities, build)


class UbpetMqttCommandButton(UbpetDeviceEntity, ButtonEntity):
    entity_description: UbpetMqttButtonDescription

    def __init__(
        self,
        coordinator: UbpetDataUpdateCoordinator,
        entry_id: str,
        serial: str,
        description: UbpetMqttButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self._bind_box(entry_id, serial, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        command = self.entity_description.service_id
        if command in _REST_COMMANDS:
            return True
        transport = self.coordinator.transport
        if not transport.connected:
            return False
        if command == "request_state":
            return True

        snapshot = (self._device_item or {}).get("mqtt_state")
        seen = self.coordinator.last_mqtt_update_at(self._serial)
        if not isinstance(snapshot, dict) or seen is None or transport.connected_since is None:
            return False
        if seen < transport.connected_since:
            return False

        mode = snapshot.get("w_mode_app_name")
        raw_state = snapshot.get("w_state_app_name")
        if not isinstance(raw_state, str):
            return False
        state = effective_work_state(mode if isinstance(mode, str) else None, raw_state)
        if command in MOVEMENT_SERVICES:
            if snapshot.get("cat_inside") or any(
                snapshot.get(field) in unsafe_values for field, unsafe_values in _INTERLOCKS.items()
            ):
                return False
        required_mode, required_state = _REQUIRED_STATE.get(command, (None, state))
        return state == required_state and (required_mode is None or mode == required_mode)

    async def async_press(self) -> None:
        if not self.available:
            raise translated_error("command_unavailable", "This command is currently unavailable")
        service = self.entity_description.service_id
        try:
            if service == REST_REQUEST_SERVICE:
                await self.coordinator.async_request_refresh()
            elif service in {RESET_WASTE_BIN_SERVICE, "__reset_deodorant"}:
                method = (
                    self.coordinator.client.reset_box_use_times
                    if service == RESET_WASTE_BIN_SERVICE
                    else self.coordinator.client.reset_deodorant
                )
                await self.hass.async_add_executor_job(method, self._serial)
                self.coordinator.schedule_refresh(15)
            else:
                if service in MOVEMENT_SERVICES:
                    await self.coordinator.async_ensure_fresh_state(self._serial)
                    if not self.available:
                        raise translated_error("state_changed", "Device state changed; movement was not sent")
                await self.hass.async_add_executor_job(self.coordinator.client.send_mqtt_service, self._serial, service)
                self.coordinator.schedule_refresh()
        except (OSError, RuntimeError) as err:
            raise translated_error("command_failed", "Vendor command failed; see connection diagnostics") from err
