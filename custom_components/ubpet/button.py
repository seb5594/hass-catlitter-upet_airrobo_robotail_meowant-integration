from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .compat import DeviceInfo, description_is_frozen, serial_info
from .const import DOMAIN
from .coordinator import UbpetDataUpdateCoordinator
from .entities import DeviceAvailability, setup_discovery

_LOGGER = logging.getLogger(__name__)

REST_REQUEST_SERVICE = "__rest_request"
RESET_WASTE_BIN_SERVICE = "__reset_waste_bin"
DIAGNOSTIC_SERVICES = {"request_state", REST_REQUEST_SERVICE}


@dataclass(frozen=description_is_frozen(ButtonEntityDescription), kw_only=True)
class UbpetMqttButtonDescription(ButtonEntityDescription):
    service_id: str


MQTT_BUTTONS: tuple[UbpetMqttButtonDescription, ...] = (
    UbpetMqttButtonDescription(
        key="rest_request",
        name="REST request",
        icon="mdi:cloud-refresh",
        translation_key="rest_request",
        entity_category=EntityCategory.DIAGNOSTIC,
        service_id=REST_REQUEST_SERVICE,
    ),
    UbpetMqttButtonDescription(
        key="mqtt_request_state",
        name="Request state",
        icon="mdi:refresh",
        translation_key="mqtt_request_state",
        entity_category=EntityCategory.DIAGNOSTIC,
        service_id="request_state",
    ),
    UbpetMqttButtonDescription(
        key="reset_waste_bin",
        name="Reset waste bin",
        icon="mdi:delete-empty",
        translation_key="reset_waste_bin",
        entity_category=EntityCategory.CONFIG,
        service_id=RESET_WASTE_BIN_SERVICE,
    ),
    UbpetMqttButtonDescription(
        key="mqtt_start_clean_up",
        name="Start clean",
        icon="mdi:broom",
        translation_key="mqtt_start_clean_up",
        service_id="start_clean_up",
    ),
    UbpetMqttButtonDescription(
        key="mqtt_pause_clean_up",
        name="Pause clean",
        icon="mdi:pause",
        translation_key="mqtt_pause_clean_up",
        service_id="pause_clean_up",
    ),
    UbpetMqttButtonDescription(
        key="mqtt_resume_clean_up",
        name="Resume clean",
        icon="mdi:play",
        translation_key="mqtt_resume_clean_up",
        service_id="resume_clean_up",
    ),
    UbpetMqttButtonDescription(
        key="mqtt_start_flatten",
        name="Flatten",
        icon="mdi:format-align-middle",
        translation_key="mqtt_start_flatten",
        service_id="start_flatten",
    ),
    UbpetMqttButtonDescription(
        key="mqtt_pause_flatten",
        name="Pause flatten",
        icon="mdi:pause",
        translation_key="mqtt_pause_flatten",
        service_id="pause_flatten",
    ),
    UbpetMqttButtonDescription(
        key="mqtt_resume_flatten",
        name="Resume flatten",
        icon="mdi:play",
        translation_key="mqtt_resume_flatten",
        service_id="resume_flatten",
    ),
    UbpetMqttButtonDescription(
        key="mqtt_start_rise",
        entity_registry_enabled_default=False,
        name="Raise litter rake",
        icon="mdi:arrow-up-bold",
        translation_key="mqtt_start_rise",
        service_id="start_rise",
    ),
    UbpetMqttButtonDescription(
        key="mqtt_start_drop",
        entity_registry_enabled_default=False,
        name="Lower litter rake",
        icon="mdi:arrow-down-bold",
        translation_key="mqtt_start_drop",
        service_id="start_drop",
    ),
)


MQTT_BUTTONS += (
    UbpetMqttButtonDescription(
        key="reset_deodorant",
        name="Reset deodorant",
        translation_key="reset_deodorant",
        icon="mdi:air-filter",
        entity_category=EntityCategory.CONFIG,
        service_id="__reset_deodorant",
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: UbpetDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    def build():
        entities: list[UbpetMqttCommandButton] = []
        for serial in coordinator.data.get("devices", {}):
            for description in MQTT_BUTTONS:
                entity = UbpetMqttCommandButton(coordinator, entry.entry_id, serial, description)
                entities.append(entity)
        return entities

    setup_discovery(coordinator, entry, async_add_entities, build)


class UbpetMqttCommandButton(DeviceAvailability, CoordinatorEntity[UbpetDataUpdateCoordinator], ButtonEntity):
    entity_description: UbpetMqttButtonDescription

    def __init__(
        self,
        coordinator: UbpetDataUpdateCoordinator,
        entry_id: str,
        serial: str,
        description: UbpetMqttButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{serial}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        item = self.coordinator.data.get("devices", {}).get(self._serial, {})
        device = item.get("device", {})
        return DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            manufacturer=self.coordinator.provider_label,
            name=device.get("deviceName") or self._serial,
            **serial_info(self._serial),
        )

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        service_id = self.entity_description.service_id
        if service_id == REST_REQUEST_SERVICE or service_id in {RESET_WASTE_BIN_SERVICE, "__reset_deodorant"}:
            return True
        if not self.coordinator.transport.connected:
            return False
        if service_id == "request_state":
            return True
        item = self.coordinator.data.get("devices", {}).get(self._serial)
        mode = _mqtt_work_mode(item)
        state = _mqtt_work_state(item)
        last_update = self.coordinator.last_mqtt_update_at(self._serial)
        connected_since = self.coordinator.transport.connected_since
        if state is None or last_update is None or connected_since is None or last_update < connected_since:
            return False
        live = (item or {}).get("mqtt_state", {})
        if service_id in {"start_clean_up", "start_flatten", "start_rise", "start_drop"} and (
            live.get("cat_inside")
            or live.get("foreign_state") == 1
            or live.get("lid_state") == 1
            or live.get("box_state") == 1
        ):
            return False
        if service_id == "start_drop":
            return mode == "RAKING_UP" and state == "PAUSED"
        if service_id in {"start_clean_up", "start_flatten", "start_rise"}:
            return state == "PENDING"
        if service_id == "pause_clean_up":
            return mode == "CLEANING" and state == "RUNNING"
        if service_id == "resume_clean_up":
            return mode == "CLEANING" and state == "PAUSED"
        if service_id == "pause_flatten":
            return mode == "SMOOTHING" and state == "RUNNING"
        if service_id == "resume_flatten":
            return mode == "SMOOTHING" and state == "PAUSED"
        return True

    async def async_press(self) -> None:
        if not self.available:
            raise HomeAssistantError("This command is currently unavailable")
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
                if service not in DIAGNOSTIC_SERVICES:
                    await self.coordinator.async_ensure_fresh_state(self._serial)
                    if not self.available:
                        raise HomeAssistantError("Device state changed; movement was not sent")
                await self.hass.async_add_executor_job(self.coordinator.client.send_mqtt_service, self._serial, service)
                self.coordinator.schedule_refresh()
        except (OSError, RuntimeError) as err:
            raise HomeAssistantError("Vendor command failed; see connection diagnostics") from err


def _mqtt_work_state(item: dict[str, Any] | None) -> str | None:
    if not isinstance(item, dict):
        return None
    mqtt_state = item.get("mqtt_state")
    if not isinstance(mqtt_state, dict):
        return None
    state = mqtt_state.get("w_state_app_name")
    return state if isinstance(state, str) else None


def _mqtt_work_mode(item: dict[str, Any] | None) -> str | None:
    if not isinstance(item, dict):
        return None
    mqtt_state = item.get("mqtt_state")
    if not isinstance(mqtt_state, dict):
        return None
    mode = mqtt_state.get("w_mode_app_name")
    return mode if isinstance(mode, str) else None
