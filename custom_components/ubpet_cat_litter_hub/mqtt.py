"""Encode and inspect device messages carried over the account MQTT session."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from threading import Lock
from urllib.parse import urlsplit

MESSAGE_PROTOCOL_VERSION = "1.0.1"
ANY_BYTES_VALUE_TYPE_URL = "type.googleapis.com/google.protobuf.BytesValue"
ANY_RECEIPT_NOTIFICATION_TYPE_URL = "type.googleapis.com/rosa.im.protobuf.ReceiptNotification"
_ONLINE_NOTIFICATION = "type.googleapis.com/rosa.im.protobuf.OnlineStatusNotification"
_STATE = 1021
_OPERATION = 1019
_COUNTER_LOCK = Lock()
_sequence = random.randint(1, 10000)
_GID_COUNTER = random.randrange(1 << 20)

_OPERATIONS = {
    "start_clean_up": (1, 1),
    "pause_clean_up": (1, 2),
    "resume_clean_up": (1, 3),
    "start_flatten": (3, 1),
    "pause_flatten": (3, 2),
    "resume_flatten": (3, 3),
    "start_rise": (7, 1),
    "start_drop": (8, 1),
}
SERVICE_ID_MAP = {
    "request_state": {"kind": "all-state", "read_only": True},
    **{
        name: {"kind": "operation", "op_mode_value": mode, "op_state_value": action}
        for name, (mode, action) in _OPERATIONS.items()
    },
}
_TELEMETRY = (
    "w_mode", "w_state", "w_cause", "toilet_state", "foreign_state", "weigh_state",
    "lid_state", "motor_state", "key_state", "object_state", "camera_state",
    "image_ctrl_state", "pic_ctrl_state", "update_state", "hall_state",
    "infrared_state", "box_state", "timestamp", "weigh_sensor", "led_state",
)
_MODES = (
    ("idle", "IDLE"), ("reset", "RESETTING"), ("clean", "CLEANING"),
    ("smooth", "SMOOTHING"), ("clear", "REPLACING"), ("rakeup", "RAKING_UP"),
)
_STATES = (("idle", "PENDING"), ("running", "RUNNING"), ("block", "BLOCKED"), ("paused", "PAUSED"))


def _varint(value: int) -> bytes:
    if not 0 <= value < 1 << 64:
        raise ValueError("integer does not fit a protobuf varint")
    groups = max(1, (value.bit_length() + 6) // 7)
    return bytes(
        ((value >> (index * 7)) & 127) + (128 if index < groups - 1 else 0)
        for index in range(groups)
    )


def field_varint(number: int, value: int) -> bytes:
    return _varint(8 * number) + _varint(value) if value else b""


def field_bytes(number: int, value: bytes) -> bytes:
    return _varint(8 * number + 2) + _varint(len(value)) + value if value else b""


def field_string(number: int, value: str) -> bytes:
    return field_bytes(number, value.encode())


def _message(*fields: int | str | bytes) -> bytes:
    encoders = {int: field_varint, str: field_string, bytes: field_bytes}
    return b"".join(encoders[type(value)](number, value) for number, value in enumerate(fields, 1))


class _Reader:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.position = 0

    def take(self, size: int) -> bytes:
        end = self.position + size
        if end > len(self.payload):
            raise ValueError("truncated protobuf field")
        value = self.payload[self.position:end]
        self.position = end
        return value

    def unsigned(self) -> int:
        result = 0
        for shift in range(0, 70, 7):
            octet = self.take(1)[0]
            result |= (octet & 127) << shift
            if octet < 128:
                if result < 1 << 64:
                    return result
                break
        raise ValueError("oversized protobuf varint")

    def fields(self) -> dict[tuple[int, int], int | bytes]:
        fields = {}
        while self.position < len(self.payload):
            number, wire = divmod(self.unsigned(), 8)
            if not 1 <= number < 1 << 29:
                raise ValueError("invalid protobuf field number")
            if wire == 0:
                value = self.unsigned()
            elif wire == 2:
                value = self.take(self.unsigned())
            elif wire in (1, 5):
                value = self.take(8 if wire == 1 else 4)
            else:
                raise ValueError(f"unsupported protobuf wire type {wire}")
            fields[(number, wire)] = value
        return fields


def _crc_remainder(byte: int) -> int:
    register = byte * 256
    # Divide by x^8 + x^2 + x + 1 in GF(2).
    for bit in range(15, 7, -1):
        if register >> bit & 1:
            register ^= 0x107 << (bit - 8)
    return register


_CRC_TABLE = tuple(map(_crc_remainder, range(256)))


def _protected(payload: bytes) -> bytes:
    remainder = 0
    for octet in payload:
        remainder = _CRC_TABLE[remainder ^ octet]
    return payload + bytes((remainder ^ 0x55,))


def build_risp_frame(*, dev: int, cmd: int, attr: int, seq: int, body: bytes) -> bytes:
    header = _message(dev, cmd, 0, len(body), attr, 0, seq)
    return bytes((219, len(header))) + _protected(header) + (_protected(body) if body else b"")


def _labels(table, number):
    if 0 <= number < len(table):
        return table[number]
    return f"unknown_{number}", f"UNKNOWN_{number}"


def summarize_all_state_body(body: bytes) -> dict:
    fields = _Reader(body).fields()
    state = {name: fields.get((i, 0), 0) for i, name in enumerate(_TELEMETRY, 1)}
    mode, mode_label = _labels(_MODES, state["w_mode"])
    action, action_label = _labels(_STATES, state["w_state"])
    state.update(
        w_mode_name=mode, w_mode_app_name=mode_label, w_state_name=action,
        w_state_app_raw_name=action_label,
        w_state_app_name="PENDING" if mode == "idle" and action == "running" else action_label,
    )
    return state


def summarize_risp_frame(frame: bytes) -> dict:
    reader = _Reader(frame)
    marker, header_size = reader.take(2)
    if marker != 219:
        raise ValueError("invalid RISP frame marker")
    header = reader.take(header_size)
    if _protected(header)[-1:] != reader.take(1):
        raise ValueError("RISP header checksum mismatch")
    fields = _Reader(header).fields()
    length = fields.get((4, 0), 0)
    body = reader.take(length)
    if length and _protected(body)[-1:] != reader.take(1):
        raise ValueError("RISP body checksum mismatch")
    command = fields.get((2, 0))
    result = dict(
        risp_cmd=command, risp_seq=fields.get((7, 0)), risp_attr=fields.get((5, 0)),
        risp_data_len=length, risp_body_hex=body.hex(),
    )
    if command in (_STATE, 1024):
        result.update(summarize_all_state_body(body))
    elif command == _OPERATION:
        operation = _Reader(body).fields()
        result.update(op_mode=operation.get((1, 0)), op_state=operation.get((2, 0)))
    return result


def _texts(fields, mapping):
    return {
        name: fields[(number, 2)].decode("utf-8", errors="replace") if (number, 2) in fields else None
        for name, number in mapping.items()
    }


def _decode(payload: bytes) -> dict:
    envelope = _Reader(payload).fields()
    result = _texts(envelope, {"cid": 1, "gid": 2, "from_uid": 4, "to_uid": 5, "protocol_version": 8})
    result.update(created_at_ms=envelope.get((3, 0)), message_type=envelope.get((6, 0)))
    if (7, 2) not in envelope:
        return result
    content = _Reader(envelope[(7, 2)]).fields()
    result.update(_texts(content, {"content_type": 1}))
    if (2, 2) not in content:
        return result
    tagged = _Reader(content[(2, 2)]).fields()
    result.update(_texts(tagged, {"type_url": 1}))
    kind = result["type_url"]
    if (2, 2) not in tagged or kind not in (
        _ONLINE_NOTIFICATION, ANY_RECEIPT_NOTIFICATION_TYPE_URL, ANY_BYTES_VALUE_TYPE_URL,
    ):
        return result
    value = _Reader(tagged[(2, 2)]).fields()
    if kind == _ONLINE_NOTIFICATION:
        result.update(_texts(value, {"online_status": 1, "status_uid": 2}))
    elif kind == ANY_RECEIPT_NOTIFICATION_TYPE_URL:
        result.update(_texts(value, {"receipt_status": 1, "receipt_cause": 2}))
    elif kind == ANY_BYTES_VALUE_TYPE_URL and (1, 2) in value:
        command = _Reader(value[(1, 2)]).fields()
        result["command_protype"] = command.get((1, 0))
        if (2, 2) in command:
            result.update(summarize_risp_frame(command[(2, 2)]))
    return result


def decode_mqtt_payload_safely(payload: bytes) -> dict:
    try:
        return _decode(payload)
    except ValueError as exc:
        return {"decode_error": str(exc)}


@dataclass(frozen=True, slots=True)
class OutboundCommand:
    seq: int
    op_body: bytes
    risp_frame: bytes
    command_proto: bytes
    cid: str | None
    im_message: bytes | None


def generate_gid(created_at_ms: int | None = None) -> str:
    global _GID_COUNTER
    with _COUNTER_LOCK:
        _GID_COUNTER = (_GID_COUNTER + 1) % (1 << 20)
        counter = _GID_COUNTER
    timestamp = int(time.time() * 1000) if created_at_ms is None else created_at_ms
    return str(timestamp * (1 << 20) + counter)


def _allocate_sequence() -> int:
    global _sequence
    with _COUNTER_LOCK:
        value = _sequence
        _sequence = value % 32767 + 1
    return value


def build_payload_parts(
    *, kind, op_mode=0, op_state=0, from_uid=None, to_uid=None,
    seq=None, cid=None, gid=None, created_at_ms=None,
) -> OutboundCommand:
    if kind not in ("operation", "all-state"):
        raise ValueError(f"unknown command kind: {kind}")
    if (from_uid is not None or to_uid is not None) and not (from_uid and to_uid):
        raise ValueError("a message requires both sender and recipient")
    device = 2
    operation = kind == "operation"
    cmd = _OPERATION if operation else _STATE
    body = _message(op_mode, op_state) if operation else b""
    seq = _allocate_sequence() if seq is None else seq
    frame = build_risp_frame(dev=device, cmd=cmd, attr=1, seq=seq, body=body)
    command = _message(2, frame)
    message = None
    if from_uid:
        now = int(time.time() * 1000)
        cid = cid or f"{now}+{100000 + int(900000 * random.random())}"
        created_at_ms = now if created_at_ms is None else created_at_ms
        gid = gid or generate_gid(created_at_ms)
        content = _message("custom", _message(ANY_BYTES_VALUE_TYPE_URL, _message(command)))
        message = _message(cid, gid, created_at_ms, from_uid, to_uid, 0, content, MESSAGE_PROTOCOL_VERSION)
    return OutboundCommand(
        seq=seq, op_body=body, risp_frame=frame, command_proto=command, cid=cid, im_message=message,
    )


def resolve_service_payload(service_id: str, *, seq=None, from_uid=None, to_uid=None, gid=None) -> OutboundCommand:
    if service_id == "request_state":
        kind, mode, action = "all-state", 0, 0
    else:
        try:
            mode, action = _OPERATIONS[service_id]
        except KeyError:
            raise ValueError(f"unknown MQTT service id: {service_id}") from None
        kind = "operation"
    return build_payload_parts(
        kind=kind, op_mode=mode, op_state=action, seq=seq, from_uid=from_uid, to_uid=to_uid, gid=gid,
    )


def mqtt_host_from_base_url(base_url: str) -> str:
    url = urlsplit(base_url if "://" in base_url else "//" + base_url)
    if not url.hostname:
        raise ValueError("the regional API URL does not contain a broker hostname")
    return url.hostname


def mqtt_endpoint(base_url: str, credentials: dict, default_port: int = 21000) -> tuple[str, int, str]:
    """The broker uses the API hostname even when credentials carry a different URL."""
    return mqtt_host_from_base_url(base_url), default_port, "base_url"
