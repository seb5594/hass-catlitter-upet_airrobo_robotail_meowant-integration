"""Redaction shared by diagnostics and support tooling."""

from __future__ import annotations

from typing import Any

PRIVATE = {
    "recordid",
    "catinfoid",
    "macaddress",
    "devicemacaddress",
    "ipaddress",
    "ssid",
    "bssid",
    "videopath",
    "imageurl",
    "pictureurl",
    "avatar",
    "avatarurl",
    "account",
    "username",
    "authorization",
    "password",
    "refreshtoken",
    "token",
    "appkey",
    "deviceid",
    "serialnumber",
    "serial",
    "useremail",
    "userphone",
    "userimage",
    "nickname",
    "icon",
    "picture",
    "wifiname",
    "clientid",
    "mqttusername",
    "mqttpassword",
    "pubtopic",
    "subtopic",
    "userid",
    "entryid",
    "title",
    "devicename",
    "fromuid",
    "touid",
    "receivedtopic",
    "immessagehex",
    "payloadhex",
    "rawhex",
    "rispbodyhex",
}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = str(key).replace("_", "").replace("-", "").casefold()
            result[key] = (
                "REDACTED"
                if normalized in PRIVATE or any(x in normalized for x in ("password", "token", "secret"))
                else redact(item)
            )
        return result
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value
