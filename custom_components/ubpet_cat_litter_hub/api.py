from __future__ import annotations

import hashlib
import json
import logging
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

USER_AGENT = "CatLitterBoxOverseasEu/2.1.12 (com.ubtrobot.airpet.overseaseu; build:699; iOS 26.5.0) Alamofire/5.5.0"
NONCE_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_LOGGER = logging.getLogger(__name__)


class UbpetApiError(RuntimeError):
    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self.payload = payload
        code = payload.get("code") if isinstance(payload, dict) else None
        super().__init__(f"Cat litter API error status={status} code={code}")


class UbpetAuthenticationError(UbpetApiError):
    """Credentials were definitively rejected; retries would risk account lockout."""


@dataclass(slots=True)
class UbpetAuth:
    token: str
    refresh_token: str | None
    expires_at_ms: int | None
    user_id: int | None


class UbtV2Signer:
    def __init__(self, app_key: str) -> None:
        self.app_key = app_key

    def sign(self, *, device_id: str) -> str:
        timestamp = str(int(time.time()))
        nonce = "".join(random.choice(NONCE_ALPHABET) for _ in range(10))
        preimage = timestamp + self.app_key + nonce + device_id
        digest = hashlib.md5(preimage.encode("utf-8")).hexdigest()
        return f"{digest} {timestamp} {nonce} v2"


class UbpetClient:
    def __init__(
        self,
        *,
        account: str,
        password: str,
        app_key: str,
        device_id: str,
        base_url: str,
        app_id: str,
        product: str,
        area_code: str = "",
    ) -> None:
        self.account = account
        self.password = password
        self.device_id = device_id
        self.base_url = base_url.rstrip("/")
        self.app_id = app_id
        self.product = product
        self.area_code = area_code
        self.signer = UbtV2Signer(app_key)
        self.auth: UbpetAuth | None = None
        self._auth_lock = threading.Lock()
        self._dashboard_cache = {}
        self._unsupported_until = {}
        self.records_per_fetch = 100
        self.mqtt_sender = None
        self.auth_paused_until = 0.0
        self._auth_failure = None

    def ensure_login(self) -> UbpetAuth:
        if self._auth_failure is not None:
            raise self._auth_failure
        if time.monotonic() < self.auth_paused_until:
            raise UbpetApiError(409, {"code": "session_in_use"})
        if auth := self._usable_auth():
            return auth
        with self._auth_lock:
            if self._auth_failure is not None:
                raise self._auth_failure
            if auth := self._usable_auth():
                return auth
            _LOGGER.debug("UPET auth token is missing or expiring, logging in")
            return self._login_unlocked()

    def _usable_auth(self) -> UbpetAuth | None:
        now_ms = int(time.time() * 1000)
        auth = self.auth
        if auth is None or (auth.expires_at_ms and auth.expires_at_ms - now_ms < 300_000):
            return None
        return auth

    def login(self) -> UbpetAuth:
        with self._auth_lock:
            return self._login_unlocked()

    def _login_unlocked(self) -> UbpetAuth:
        last_error: UbpetApiError | None = None
        for account_type in _account_type_candidates(self.account):
            try:
                _LOGGER.debug(
                    "Trying UPET login with endpoint=%s areaCode=%s accountType=%s",
                    self.base_url,
                    self.area_code,
                    account_type,
                )
                return self._login_with_account_type(account_type)
            except UbpetApiError as err:
                _LOGGER.debug(
                    "UPET login failed with endpoint=%s areaCode=%s accountType=%s: %s",
                    self.base_url,
                    self.area_code,
                    account_type,
                    err,
                )
                code = err.payload.get("code") if isinstance(err.payload, dict) else None
                if code in {2002, 2006, 2014, 2342} or err.status in {401, 403}:
                    self._auth_failure = UbpetAuthenticationError(err.status, err.payload)
                    raise self._auth_failure from err
                if code not in {1009, 2004, 2010, 2011, 2019, 2042}:
                    raise
                last_error = err
        if last_error is not None:
            self._auth_failure = UbpetAuthenticationError(last_error.status, last_error.payload)
            raise self._auth_failure from last_error
        raise RuntimeError("no account type candidates")

    def _refresh_after_unauthorized(self, rejected_token: str) -> UbpetAuth:
        if time.monotonic() < self.auth_paused_until:
            raise UbpetApiError(409, {"code": "session_in_use"})
        with self._auth_lock:
            if self._auth_failure is not None:
                raise self._auth_failure
            current_auth = self._usable_auth()
            if current_auth is not None and current_auth.token != rejected_token:
                return current_auth
            _LOGGER.debug("UPET auth token was rejected, logging in again")
            self.auth = None
            return self._login_unlocked()

    def _login_with_account_type(self, account_type: str) -> UbpetAuth:
        payload = {
            "account": self.account,
            "password": _md5_password(self.password),
            "accountType": account_type,
            "areaCode": self.area_code,
        }
        response = self._request("PUT", "/user-service-rest/v2/user/login", payload=payload, auth=False)
        data = _response_data(response)
        token_data = data.get("token") if isinstance(data, dict) else None
        user_data = data.get("user") if isinstance(data, dict) else None
        if not isinstance(token_data, dict) or not token_data.get("token"):
            raise UbpetApiError(200, response)
        self.auth = UbpetAuth(
            token=token_data["token"],
            refresh_token=token_data.get("refreshToken"),
            expires_at_ms=token_data.get("expireAt"),
            user_id=user_data.get("userId") if isinstance(user_data, dict) else None,
        )
        _LOGGER.debug("UPET login succeeded with accountType=%s", account_type)
        return self.auth

    def get_devices(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/user-service-rest/v2/robot/common/device/list", auth=True)
        return _require_list(data)

    def get_all_config(self, serial_number: str) -> dict[str, Any]:
        data = self._request(
            "GET",
            f"/catbox-server/box/config/allConfig?serialNumber={_quote(serial_number)}",
            auth=True,
        )
        return _require_dict(data)

    def get_box_use_times(self, serial_number: str) -> dict[str, Any]:
        data = self._request(
            "GET",
            f"/catbox-server/box/config/box-use-times/?serialNumber={_quote(serial_number)}",
            auth=True,
        )
        return _require_dict(data)

    def reset_box_use_times(self, serial_number: str) -> None:
        payload = {
            "boxUseTimes": 0,
            "serialNumber": serial_number,
        }
        self._request("PUT", "/catbox-server/box/config/box-use-times/reset", payload=payload, auth=True)

    def get_deodorant_status(self, serial_number: str) -> dict[str, Any]:
        data = self._request(
            "GET",
            f"/catbox-server/app/deodorant-block/status?serialNumber={_quote(serial_number)}",
            auth=True,
        )
        return _require_dict(data)

    def get_device_online(self, serial_number: str) -> dict[str, Any]:
        data = self._request(
            "GET",
            f"/v1/ubtechinc-im-manager/im/online/device/?sn={_quote(serial_number)}",
            auth=True,
        )
        return _require_dict(data)

    def get_im_credentials(self) -> dict[str, Any]:
        data = self._request("POST", "/v1/ubtechinc-im-manager/im/login", payload={"type": 2}, auth=True)
        return _require_dict(data)

    def get_im_friends(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/v1/ubtechinc-im-manager/im/friends", auth=True)
        return _require_list(data)

    def send_mqtt_service(self, serial_number: str, service_id: str) -> dict[str, Any]:
        """Send a device command through the account's persistent MQTT session."""
        if self.mqtt_sender is None:
            raise RuntimeError("Vendor MQTT session is unavailable")
        return self.mqtt_sender(serial_number, service_id)

    def get_cats(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/catbox-server/web/cat/info", auth=True)
        return _require_list(data)

    def get_box_records(self, serial_number: str, message_type: int, size: int = 1) -> list[dict[str, Any]]:
        payload = {
            "eventTime": "0",
            "serialNumber": serial_number,
            "size": size,
            "messageType": message_type,
        }
        data = self._request("POST", "/catbox-server/web/box/record/new", payload=payload, auth=True)
        body = data.get("data") if isinstance(data, dict) else None
        records = body.get("records") if isinstance(body, dict) else None
        if not isinstance(records, list):
            raise UbpetApiError(200, data)
        return [record for record in records if isinstance(record, dict)]

    def set_auto_clean_delay(self, serial_number: str, minutes: int, enabled: bool = True) -> None:
        if not 1 <= minutes <= 60:
            raise ValueError("auto clean delay must be at least 1 minute")
        payload = {
            "serialNumber": serial_number,
            "functionType": 2,
            "controlSwitch": int(enabled),
            "optionInt": minutes * 60,
        }
        self._request("PUT", "/catbox-server/box/config/switch/update", payload=payload, auth=True)

    def set_auto_clean_enabled(self, serial_number: str, enabled: bool, lazy_time_seconds: int | None) -> None:
        payload = {
            "serialNumber": serial_number,
            "functionType": 2,
            "controlSwitch": 1 if enabled else 0,
            "optionInt": lazy_time_seconds or 480,
        }
        self._request("PUT", "/catbox-server/box/config/switch/update", payload=payload, auth=True)

    def set_deodorant_alert(self, serial_number: str, enabled: bool) -> None:
        payload = {
            "serialNumber": serial_number,
            "alertSwitch": 1 if enabled else 0,
        }
        self._request("POST", "/catbox-server/app/deodorant-block/switch", payload=payload, auth=True)

    def set_time_point(
        self,
        serial_number: str,
        *,
        config_id: int,
        function_type: int,
        open_switch: int,
        time_hour: int,
        time_minute: int,
        option_int: int,
    ) -> None:
        payload = {
            "serialNumber": serial_number,
            "configId": config_id,
            "functionType": function_type,
            "openSwitch": open_switch,
            "timeHour": time_hour,
            "timeMinute": time_minute,
            "optionInt": option_int,
        }
        self._request("PUT", "/catbox-server/box/config/timePoint/update", payload=payload, auth=True)

    def set_time_period(
        self,
        serial_number: str,
        *,
        config_id: int,
        function_type: int,
        open_switch: int,
        start_hour: int,
        start_minute: int,
        end_hour: int,
        end_minute: int,
    ) -> None:
        payload = {
            "serialNumber": serial_number,
            "functionType": function_type,
            "openSwitch": open_switch,
            "configId": config_id,
            "startTimeHour": start_hour,
            "startTimeMinute": start_minute,
            "endTimeHour": end_hour,
            "endTimeMinute": end_minute,
        }
        self._request("PUT", "/catbox-server/box/config/timePeriod/update", payload=payload, auth=True)

    def set_function_switch(self, serial_number, function_type, enabled):
        if function_type not in (0, 1, 6, 7):
            raise ValueError("Unsupported switch function")
        self._request(
            "PUT",
            "/catbox-server/box/config/switch/update",
            payload={
                "serialNumber": serial_number,
                "functionType": function_type,
                "controlSwitch": int(enabled),
                "optionInt": 1,
            },
            auth=True,
        )

    def set_box_full_alert(self, serial_number, uses):
        if not isinstance(uses, int) or uses < 1:
            raise ValueError("Invalid waste bin threshold")
        self._request(
            "PUT",
            "/catbox-server/box/config/box-full-alert",
            payload={"serialNumber": serial_number, "boxFullAlertTimes": uses},
            auth=True,
        )

    def reset_deodorant(self, serial_number: str) -> None:
        self._request(
            "POST", "/catbox-server/app/deodorant-block/replaced", payload={"serialNumber": serial_number}, auth=True
        )

    def get_capabilities(self, serial_number: str) -> dict[str, Any]:
        response = self._request(
            "GET", f"/catbox-server/box/config/device/capabilities?sn={_quote(serial_number)}", auth=True
        )
        data = response.get("data") if isinstance(response, dict) else None
        if not isinstance(data, (dict, list)):
            raise UbpetApiError(200, {"code": "invalid_capabilities"})
        return {"values": data}

    def _optional(self, key, func, *args, default=None):
        if self._unsupported_until.get(key, 0) > time.monotonic():
            return self._dashboard_cache.get(key, default), False
        try:
            value = func(*args)
        except UbpetApiError as err:
            if err.status in (401, 403, 409):
                raise
            if err.status in (404, 405):
                self._unsupported_until[key] = time.monotonic() + 3600
            return self._dashboard_cache.get(key, default), False
        except (OSError, RuntimeError):
            return self._dashboard_cache.get(key, default), False
        self._dashboard_cache[key] = value
        return value, True

    def get_dashboard(self) -> dict[str, Any]:
        self.ensure_login()
        devices = self.get_devices()
        by_serial = {}
        futures = []
        # Bound simultaneous requests per account; slow optional endpoints do not
        # serialize six timeouts per box or consume HA's whole executor pool.
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="catlitter-api") as pool:
            cats_future = pool.submit(self._optional, "cats", self.get_cats, default=[])
            for device in devices:
                serial = device.get("serialNumber")
                if not serial:
                    continue
                item = {"device": device, "fresh": {}}
                by_serial[serial] = item
                for key, func, args, default in (
                    ("config", self.get_all_config, (serial,), {}),
                    ("box_use_times", self.get_box_use_times, (serial,), {}),
                    ("deodorant", self.get_deodorant_status, (serial,), {}),
                    ("online", self.get_device_online, (serial,), {}),
                    ("cat_records", self.get_box_records, (serial, 0, self.records_per_fetch), []),
                    ("device_records", self.get_box_records, (serial, 1, self.records_per_fetch), []),
                ):
                    futures.append(
                        (item, key, pool.submit(self._optional, (serial, key), func, *args, default=default))
                    )
                cap_key = (serial, "capabilities")
                if cap_key in self._dashboard_cache:
                    item["capabilities"] = self._dashboard_cache[cap_key]
                else:
                    futures.append(
                        (
                            item,
                            "capabilities",
                            pool.submit(self._optional, cap_key, self.get_capabilities, serial, default=None),
                        )
                    )
            for item, key, future in futures:
                item[key], item["fresh"][key] = future.result()
            cats, cats_fresh = cats_future.result()
        return {
            "devices": by_serial,
            "cats": cats,
            "cats_fresh": cats_fresh,
            "user_id": self.auth.user_id if self.auth else None,
        }

    def _request(self, method: str, path: str, *, payload: dict[str, Any] | None = None, auth: bool) -> Any:
        auth_token = self.ensure_login().token if auth else None
        try:
            return self._request_once(method, path, payload=payload, auth_token=auth_token)
        except UbpetApiError as err:
            if not auth or err.status != 401 or auth_token is None:
                raise
            _LOGGER.debug("UPET HTTP %s %s returned 401; refreshing authentication once", method, path)
            refreshed_auth = self._refresh_after_unauthorized(auth_token)
            return self._request_once(method, path, payload=payload, auth_token=refreshed_auth.token)

    def _request_once(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None,
        auth_token: str | None,
    ) -> Any:
        body = None
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

        headers = {
            "x-ubt-language": "en",
            "x-ubt-deviceid": self.device_id,
            "content-type": "application/json; charset=utf-8",
            "accept": "application/json",
            "x-ubt-appid": self.app_id,
            "priority": "u=3, i",
            "user-agent": USER_AGENT,
            "x-ubt-sign": self.signer.sign(device_id=self.device_id),
        }
        if auth_token is not None:
            headers["authorization"] = auth_token
            headers["product"] = self.product

        req = urllib.request.Request(self.base_url + path, data=body, headers=headers, method=method)
        started = time.monotonic()
        _LOGGER.debug("UPET HTTP %s %s auth=%s", method, path, auth_token is not None)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = _decode_response(resp.read())
                _raise_for_api_error(resp.status, data)
                _LOGGER.debug(
                    "UPET HTTP %s %s completed with status=%s in %.2fs",
                    method,
                    path,
                    resp.status,
                    time.monotonic() - started,
                )
                return data
        except urllib.error.HTTPError as err:
            try:
                data = _decode_response(err.read())
            finally:
                err.close()
            _LOGGER.debug("UPET HTTP %s %s failed with status=%s", method, path, err.code)
            raise UbpetApiError(err.code, data) from err


def _md5_password(password: str) -> str:
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def _account_type_candidates(account: str) -> tuple[str, ...]:
    if "@" in account:
        return ("1", "0", "2")
    return ("0", "1", "2")


def _decode_response(raw: bytes) -> Any:
    text = raw.decode("utf-8", "replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _raise_for_api_error(status: int, data: Any) -> None:
    if status >= 400:
        raise UbpetApiError(status, data)
    if isinstance(data, dict):
        code = data.get("code")
        if code not in (None, 0):
            raise UbpetApiError(status, data)


def _response_data(payload: Any) -> Any:
    """Unwrap the standard vendor response envelope when it is present."""
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload


def _require_dict(payload: Any) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise UbpetApiError(200, payload)
    return data


def _require_list(payload: Any) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        raise UbpetApiError(200, payload)
    return data


def _quote(value: str) -> str:
    return urllib.parse.quote(value, safe="")
