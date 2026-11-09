"""HTTP interface for account login, litter-box configuration and visit records."""
from __future__ import annotations

import hashlib
import json
import random
import string
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Any

_BOX = "/catbox-server/box/config/"
_DEODORANT = "/catbox-server/app/deodorant-block/"
_IM = "/v1/ubtechinc-im-manager/im/"
_LOGIN = "/user-service-rest/v2/user/login"
_CLIENT = "CatLitterBoxOverseasEu/2.1.12 (com.ubtrobot.airpet.overseaseu; build:699; iOS 26.5.0) Alamofire/5.5.0"
_MISMATCHED_ACCOUNT_TYPE = frozenset({1009, 2004, 2010, 2011, 2019, 2042})
_CREDENTIAL_REJECTED = frozenset({2002, 2006, 2014, 2342})


class UbpetApiError(RuntimeError):
    """A vendor response that cannot be used by the integration."""

    def __init__(self, status: int, payload: Any):
        self.status = status
        self.payload = payload
        super().__init__(f"Cat litter API returned HTTP {status}, vendor code {_code(payload)}")


class UbpetAuthenticationError(UbpetApiError):
    """The account must be reauthenticated by the user."""


@dataclass(slots=True)
class UbpetAuth:
    token: str
    refresh_token: str | None
    expires_at_ms: int | None
    user_id: int | None


def _code(message):
    return message.get("code") if isinstance(message, dict) else None


def _data(message):
    return message.get("data") if isinstance(message, dict) else None


def _expect(message, shape):
    value = _data(message)
    if isinstance(value, shape):
        return value
    raise UbpetApiError(200, message)


def _parse(raw):
    try:
        return json.loads(raw)
    except (UnicodeError, ValueError):
        return raw.decode(errors="replace")


class UbtV2Signer:
    """Build the signature header required by the cloud API."""

    def __init__(self, app_key: str):
        self.app_key = app_key

    def sign(self, *, device_id: str) -> str:
        seconds = int(time.time())
        alphabet = string.digits + string.ascii_uppercase + string.ascii_lowercase
        challenge = "".join(random.choice(alphabet) for _ in range(10))
        digest = hashlib.md5(f"{seconds}{self.app_key}{challenge}{device_id}".encode()).hexdigest()
        return " ".join((digest, str(seconds), challenge, "v2"))


class UbpetClient:
    def __init__(self, *, account, password, app_key, device_id, base_url, app_id, product, area_code=""):
        self.account = account
        self.password = password
        self.device_id = device_id
        self.base_url = base_url.rstrip("/")
        self.app_id = app_id
        self.product = product
        self.area_code = area_code
        self.signer = UbtV2Signer(app_key)
        self.auth: UbpetAuth | None = None
        self.auth_paused_until = 0.0
        self.records_per_fetch = 100
        self.mqtt_sender = None
        self._login_lock = Lock()
        self._auth_failure: UbpetAuthenticationError | None = None
        self._values = {}
        self._retry_at = {}

    def _check_login_allowed(self):
        if self._auth_failure:
            raise self._auth_failure
        if time.monotonic() < self.auth_paused_until:
            raise UbpetApiError(409, {"code": "session_in_use"})

    def _can_reuse_auth(self, rejected_token=None):
        auth = self.auth
        return auth is not None and auth.token != rejected_token and (
            not auth.expires_at_ms or auth.expires_at_ms >= (time.time() + 300) * 1000
        )

    def _session(self, rejected_token=None) -> UbpetAuth:
        self._check_login_allowed()
        if self._can_reuse_auth(rejected_token):
            return self.auth
        with self._login_lock:
            self._check_login_allowed()
            if self._can_reuse_auth(rejected_token):
                return self.auth
            self.auth = None
            return self._authenticate()

    def ensure_login(self) -> UbpetAuth:
        return self._session()

    def login(self) -> UbpetAuth:
        with self._login_lock:
            return self._authenticate()

    def _authenticate(self) -> UbpetAuth:
        order = ("1", "0", "2") if "@" in self.account else ("0", "1", "2")
        rejected = None
        for kind in order:
            try:
                auth = self._login_with_account_type(kind)
            except UbpetApiError as error:
                code = _code(error.payload)
                if error.status in (401, 403) or code in _CREDENTIAL_REJECTED:
                    rejected = error
                    break
                if code not in _MISMATCHED_ACCOUNT_TYPE:
                    raise
                rejected = error
            else:
                self.auth = auth
                self._auth_failure = None
                return auth
        assert rejected is not None
        self._auth_failure = UbpetAuthenticationError(rejected.status, rejected.payload)
        raise self._auth_failure from rejected

    def _login_with_account_type(self, kind: str) -> UbpetAuth:
        fields = dict(
            account=self.account, password=hashlib.md5(self.password.encode()).hexdigest(),
            accountType=kind, areaCode=self.area_code,
        )
        response = self._exchange("PUT", _LOGIN, fields)
        content = _data(response)
        if not isinstance(content, dict):
            content = response
        token = content.get("token") if isinstance(content, dict) else None
        if not isinstance(token, dict) or not token.get("token"):
            raise UbpetApiError(200, response)
        user = content.get("user")
        return UbpetAuth(
            token["token"], token.get("refreshToken"), token.get("expireAt"),
            user.get("userId") if isinstance(user, dict) else None,
        )

    def _exchange(self, method, path, fields=None, session=None):
        headers = {
            "x-ubt-language": "en",
            "x-ubt-deviceid": self.device_id,
            "content-type": "application/json; charset=utf-8",
            "accept": "application/json",
            "x-ubt-appid": self.app_id,
            "priority": "u=3, i",
            "user-agent": _CLIENT,
            "x-ubt-sign": self.signer.sign(device_id=self.device_id),
        }
        if session:
            headers.update(authorization=session.token, product=self.product)
        body = json.dumps(fields, separators=(",", ":")).encode() if fields is not None else None
        request = urllib.request.Request(self.base_url + path, body, headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                status = response.status
                message = _parse(response.read())
        except urllib.error.HTTPError as error:
            with error:
                raise UbpetApiError(error.code, _parse(error.read())) from error
        if status >= 400 or _code(message) not in (None, 0):
            raise UbpetApiError(status, message)
        return message

    def _call(self, method, path, fields=None):
        session = self.ensure_login()
        try:
            return self._exchange(method, path, fields, session)
        except UbpetApiError as error:
            if error.status != 401:
                raise
        return self._exchange(method, path, fields, self._session(rejected_token=session.token))

    def _read(self, path, shape, **params):
        if params:
            path += "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        return _expect(self._call("GET", path), shape)

    def _write(self, path, serial, *, method="PUT", **values):
        self._call(method, path, dict(values, serialNumber=serial))

    def get_devices(self):
        return self._read("/user-service-rest/v2/robot/common/device/list", list)

    def get_all_config(self, serial_number):
        return self._read(_BOX + "allConfig", dict, serialNumber=serial_number)

    def get_box_use_times(self, serial_number):
        return self._read(_BOX + "box-use-times/", dict, serialNumber=serial_number)

    def reset_box_use_times(self, serial_number):
        self._write(_BOX + "box-use-times/reset", serial_number, boxUseTimes=0)

    def get_deodorant_status(self, serial_number):
        return self._read(_DEODORANT + "status", dict, serialNumber=serial_number)

    def get_device_online(self, serial_number):
        return self._read(_IM + "online/device/", dict, sn=serial_number)

    def get_im_credentials(self):
        return _expect(self._call("POST", _IM + "login", {"type": 2}), dict)

    def get_im_friends(self):
        return self._read(_IM + "friends", list)

    def send_mqtt_service(self, serial_number, service_id):
        sender = self.mqtt_sender
        if sender is None:
            raise RuntimeError("Vendor MQTT session is unavailable")
        return sender(serial_number, service_id)

    def get_cats(self):
        return self._read("/catbox-server/web/cat/info", list)

    def get_box_records(self, serial_number, message_type, size=1):
        request = dict(eventTime="0", serialNumber=serial_number, size=size, messageType=message_type)
        envelope = self._call("POST", "/catbox-server/web/box/record/new", request)
        records = _expect(envelope, dict).get("records")
        if not isinstance(records, list):
            raise UbpetApiError(200, envelope)
        return [record for record in records if isinstance(record, dict)]

    def _set_switch(self, serial, function, enabled, option):
        self._write(
            _BOX + "switch/update", serial, functionType=function, controlSwitch=int(enabled), optionInt=option,
        )

    def set_auto_clean_delay(self, serial_number, minutes, enabled=True):
        if not 1 <= minutes <= 60:
            raise ValueError("automatic cleaning delay must be between 1 and 60 minutes")
        self._set_switch(serial_number, 2, enabled, 60 * minutes)

    def set_auto_clean_enabled(self, serial_number, enabled, lazy_time_seconds):
        self._set_switch(serial_number, 2, enabled, lazy_time_seconds or 480)

    def set_function_switch(self, serial_number, function_type, enabled):
        if function_type not in (0, 1, 6, 7):
            raise ValueError("Unsupported switch function")
        self._set_switch(serial_number, function_type, enabled, 1)

    def set_deodorant_alert(self, serial_number, enabled):
        self._write(_DEODORANT + "switch", serial_number, method="POST", alertSwitch=int(enabled))

    def reset_deodorant(self, serial_number):
        self._write(_DEODORANT + "replaced", serial_number, method="POST")

    def set_time_point(self, serial_number, *, config_id, function_type, open_switch, time_hour, time_minute, option_int):
        self._write(
            _BOX + "timePoint/update", serial_number, configId=config_id, functionType=function_type,
            openSwitch=open_switch, timeHour=time_hour, timeMinute=time_minute, optionInt=option_int,
        )

    def set_time_period(
        self, serial_number, *, config_id, function_type, open_switch, start_hour, start_minute, end_hour, end_minute,
    ):
        self._write(
            _BOX + "timePeriod/update", serial_number, configId=config_id, functionType=function_type,
            openSwitch=open_switch, startTimeHour=start_hour, startTimeMinute=start_minute,
            endTimeHour=end_hour, endTimeMinute=end_minute,
        )

    def set_box_full_alert(self, serial_number, uses):
        if not isinstance(uses, int) or uses < 1:
            raise ValueError("Invalid waste bin threshold")
        self._write(_BOX + "box-full-alert", serial_number, boxFullAlertTimes=uses)

    def get_capabilities(self, serial_number):
        values = self._read(_BOX + "device/capabilities", (dict, list), sn=serial_number)
        return {"values": values}

    def _optional(self, key, func, *args, default=None):
        if time.monotonic() >= self._retry_at.get(key, 0):
            try:
                self._values[key] = func(*args)
            except UbpetApiError as error:
                if error.status in (401, 403, 409):
                    raise
                if error.status in (404, 405):
                    self._retry_at[key] = time.monotonic() + 3600
            except (OSError, RuntimeError):
                pass
            else:
                return self._values[key], True
        return self._values.get(key, default), False

    def get_dashboard(self):
        self.ensure_login()
        boxes = {
            box["serialNumber"]: {"device": box, "fresh": {}}
            for box in self.get_devices() if box.get("serialNumber")
        }
        readers = {
            "config": (self.get_all_config, (), {}),
            "box_use_times": (self.get_box_use_times, (), {}),
            "deodorant": (self.get_deodorant_status, (), {}),
            "online": (self.get_device_online, (), {}),
            "cat_records": (self.get_box_records, (0, self.records_per_fetch), []),
            "device_records": (self.get_box_records, (1, self.records_per_fetch), []),
            "capabilities": (self.get_capabilities, (), None),
        }
        # Queue optional work independently so a slow endpoint does not delay other boxes.
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="catlitter-api") as workers:
            cats_job = workers.submit(self._optional, "cats", self.get_cats, default=[])
            jobs = {}
            for serial, box in boxes.items():
                for name, (reader, args, default) in readers.items():
                    key = serial, name
                    if name == "capabilities" and key in self._values:
                        box[name] = self._values[key]
                    else:
                        jobs[key] = workers.submit(self._optional, key, reader, serial, *args, default=default)
            for (serial, name), job in jobs.items():
                value, fresh = job.result()
                boxes[serial][name] = value
                boxes[serial]["fresh"][name] = fresh
            cats, cats_fresh = cats_job.result()
        return dict(devices=boxes, cats=cats, cats_fresh=cats_fresh, user_id=self.auth.user_id if self.auth else None)
