"""Check the vendor wire contract using fixed command and telemetry examples."""
from __future__ import annotations

import pytest
from test_history import load

wire = load("mqtt")


@pytest.mark.parametrize(("service", "mode", "action"), [
    ("start_clean_up", 1, 1), ("pause_clean_up", 1, 2), ("resume_clean_up", 1, 3),
    ("start_flatten", 3, 1), ("pause_flatten", 3, 2), ("resume_flatten", 3, 3),
    ("start_rise", 7, 1), ("start_drop", 8, 1),
])
def test_motion_commands(service, mode, action):
    message = wire.resolve_service_payload(service, seq=12)
    assert message.op_body == bytes((8, mode, 16, action))
    assert wire.summarize_risp_frame(message.risp_frame) == {
        "risp_cmd": 1019, "risp_seq": 12, "risp_attr": 1,
        "risp_data_len": 4, "risp_body_hex": message.op_body.hex(),
        "op_mode": mode, "op_state": action,
    }


@pytest.mark.parametrize(("service", "frame"), [
    ("request_state", "db09080210fd0728013801f6"),
    ("start_clean_up", "db0b080210fb072004280138018b08011001de"),
])
def test_reference_command_bytes(service, frame):
    message = wire.resolve_service_payload(service, seq=1)
    expected = bytes.fromhex(frame)
    assert message.risp_frame == expected
    assert message.command_proto == bytes((8, 2, 18, len(expected))) + expected


@pytest.mark.parametrize("service", ["pause_drop", "resume_rise", "start_exchange_sand", "request_state_gid100"])
def test_unknown_command_does_not_construct_a_frame(service):
    with pytest.raises(ValueError, match="unknown MQTT"):
        wire.resolve_service_payload(service, seq=4)


def test_telemetry_without_mode_and_state_uses_the_proto_defaults():
    state = wire.summarize_all_state_body(bytes.fromhex("185a9001b6beafd106"))
    assert (state["w_mode_app_name"], state["w_state_app_name"]) == ("IDLE", "PENDING")
    assert (state["w_mode_name"], state["w_state_name"]) == ("idle", "idle")
    assert state["w_cause"] == 90
    assert state["timestamp"] == 1781260086


def test_command_envelope_routes_to_the_device(monkeypatch):
    monkeypatch.setattr(wire.time, "time", lambda: 1700000000.123)
    monkeypatch.setattr(wire.random, "random", lambda: 0.234567)
    request = wire.resolve_service_payload("request_state", seq=2, from_uid="account", to_uid="box", gid="105")
    assert request.cid == "1700000000123+311110"
    assert request.command_proto in request.im_message
    decoded = wire.decode_mqtt_payload_safely(request.im_message)
    assert (decoded["cid"], decoded["gid"]) == (request.cid, "105")
    assert (decoded["from_uid"], decoded["to_uid"]) == ("account", "box")
    assert decoded["protocol_version"] == "1.0.1"
    assert (decoded["risp_cmd"], decoded["risp_seq"]) == (1021, 2)


def test_message_counter_fills_the_low_20_bits(monkeypatch):
    monkeypatch.setattr(wire, "_GID_COUNTER", 0)
    monkeypatch.setattr(wire.time, "time", lambda: 1780900866.3)
    assert wire.generate_gid(1780900866300) == "1867409906781388801"
    assert wire.generate_gid() == "1867409906781388802"


def _blob(number, data):
    """Small fixture builder for the lengths used by this receipt."""
    return bytes((8 * number + 2, len(data))) + data


def test_broker_receipt_contains_vendor_result():
    type_url = b"type.googleapis.com/rosa.im.protobuf.ReceiptNotification"
    notice = _blob(1, b"receipt/success")
    event = _blob(1, b"receipt") + _blob(2, _blob(1, type_url) + _blob(2, notice))
    packet = _blob(1, b"message-17") + _blob(4, b"box") + _blob(5, b"account") + _blob(7, event)
    summary = wire.decode_mqtt_payload_safely(packet)
    assert (summary["cid"], summary["from_uid"], summary["to_uid"]) == ("message-17", "box", "account")
    assert (summary["content_type"], summary["receipt_status"]) == ("receipt", "receipt/success")


@pytest.mark.parametrize("packet", [b"\x3a\x10\x00", b"\x08\x80", b"\x07"])
def test_malformed_wire_data_is_reported_without_a_callback_exception(packet):
    assert "decode_error" in wire.decode_mqtt_payload_safely(packet)


@pytest.mark.parametrize("url", ["https://eu.example.test/path", "eu.example.test/"])
def test_mqtt_uses_the_regional_api_host(url):
    assert wire.mqtt_endpoint(url, {"url": "ssl://ignored.example.test:21001"}) == (
        "eu.example.test", 21000, "base_url",
    )
