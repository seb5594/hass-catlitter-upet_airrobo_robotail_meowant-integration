"""Bounded, persistent visit history and factual aggregates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isfinite

UTC = timezone.utc


MAX_EVENTS = 10000
MAX_CLEANINGS = 2000

# Vendor ``eventType`` values that are confirmed by app captures or issue reports.
EVENT_CAT_VISIT = 3
EVENT_WEIGHT_RECORDED = 21
EVENT_CLEAN_FINISHED = 31  # inferred from timing; reported by bojanrajkovic/upet-hass#6
BOX_EVENT_NAMES = {
    EVENT_CAT_VISIT: "cat_visit",
    EVENT_WEIGHT_RECORDED: "weight_recorded",
    EVENT_CLEAN_FINISHED: "clean_finished",
}


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def timestamp(value):
    if (n := number(value)) is not None:
        try:
            return datetime.fromtimestamp(n / 1000 if abs(n) > 100_000_000_000 else n, UTC)
        except (ValueError, OverflowError, OSError):
            return None
    if isinstance(value, str):
        try:
            date = datetime.fromisoformat(value.replace("Z", "+00:00"))
            # PnnnG established that timeStr is the vendor's UTC+8 clock.
            return (
                date.replace(tzinfo=timezone(timedelta(hours=8))).astimezone(UTC)
                if date.tzinfo is None
                else date.astimezone(UTC)
            )
        except ValueError:
            pass
    return None


class History:
    def __init__(self, state=None):
        self.state = state if isinstance(state, dict) else {}
        self.state.setdefault("cats", {})
        self.state.setdefault("streams", {})
        self.state.setdefault("box_visits", {})
        self.state.setdefault("box_cleanings", {})

    def cat(self, cat_id):
        cat = self.state["cats"].setdefault(str(cat_id), {})
        cat.setdefault("events", [])
        cat.setdefault("poo_duration_threshold_seconds", 100)
        return cat

    def threshold(self, cat_id):
        return self.cat(cat_id)["poo_duration_threshold_seconds"]

    def set_threshold(self, cat_id, value):
        n = number(value)
        if n is None or not 10 <= n <= 150:
            raise ValueError("Threshold must be between 10 and 150 seconds")
        self.cat(cat_id)["poo_duration_threshold_seconds"] = round(n)

    def ingest(self, serial, kind, records, now, limit=100):
        if not isinstance(records, list):
            return []
        key = f"{serial}:{kind}"
        stream = self.state["streams"].get(key)
        new_stream = stream is None
        stream = stream or {"seen": [], "initialized": False, "truncated": False}
        seen = set(stream.get("seen", []))
        emitted = []
        valid = []
        for record in records:
            if not isinstance(record, dict):
                continue
            at = timestamp(record.get("eventTime")) or timestamp(record.get("timeStr"))
            if at is None or at > now + timedelta(minutes=5):
                continue
            identity = str(
                record.get("recordId")
                or record.get("id")
                or f"{at.isoformat()}:{record.get('catInfoId')}:{record.get('eventType')}:{record.get('costTime')}"
            )
            valid.append((at, identity, record))
        for at, identity, record in sorted(valid, key=lambda r: (r[0], r[1])):
            if identity in seen:
                continue
            seen.add(identity)
            event_type = number(record.get("eventType"))
            event = {**record, "serial_number": serial, "timestamp": at.isoformat()}
            if event_type in BOX_EVENT_NAMES:
                event["event_name"] = BOX_EVENT_NAMES[event_type]
            if kind == "device_records" and event_type == EVENT_CLEAN_FINISHED:
                self._record_cleaning(serial, at)
            if not new_stream:
                emitted.append(event)
            duration = number(record.get("costTime"))
            cat_id = record.get("catInfoId")
            if kind == "cat_records" and event_type == EVENT_CAT_VISIT and duration is not None and duration > 0:
                item = {
                    "at": at.isoformat(),
                    "duration_seconds": duration,
                    "record_id": f"{serial}:{identity}",
                    "weight": number(record.get("weight")),
                    "serial": serial,
                }
                previous = self.state["box_visits"].get(serial, {})
                if item["at"] >= previous.get("at", ""):
                    self.state["box_visits"][serial] = {**item, "cat_info_id": cat_id}
                if cat_id is not None:
                    events = self.cat(cat_id)["events"]
                    # Preserve the old fork's history without double-counting its backfill.
                    match = next(
                        (
                            e
                            for e in events
                            if e.get("record_id") in (identity, item["record_id"])
                            or (
                                e.get("at") == item["at"]
                                and e.get("duration_seconds") == duration
                                and not e.get("serial")
                            )
                        ),
                        None,
                    )
                    if match is not None:
                        match.update(item)
                    else:
                        events.append(item)
                    events.sort(key=lambda e: e.get("at", ""))
                    del events[:-MAX_EVENTS]
        stream["seen"] = list(dict.fromkeys([*stream.get("seen", []), *(identity for _, identity, _ in valid)]))[
            -MAX_EVENTS:
        ]
        stream["coverage_start"] = min((at.isoformat() for at, _, _ in valid), default=stream.get("coverage_start"))
        stream["complete_24h"] = len(records) < limit or any(at <= now - timedelta(hours=24) for at, _, _ in valid)
        stream["last_success_at"] = now.isoformat()
        stream["initialized"] = True
        stream["truncated"] = len(records) >= limit
        self.state["streams"][key] = stream
        return emitted

    def _record_cleaning(self, serial, at):
        cleanings = self.state["box_cleanings"].setdefault(serial, [])
        stamp = at.isoformat()
        if stamp not in cleanings:
            cleanings.append(stamp)
            cleanings.sort()
            del cleanings[:-MAX_CLEANINGS]

    def box_analytics(self, serial, now, day_start, bin_reset_at=None):
        """Aggregates of one box that the vendor API does not provide itself."""
        cleanings = [
            at for stamp in self.state["box_cleanings"].get(serial, []) if (at := timestamp(stamp)) and at <= now
        ]
        visits = [
            at
            for cat in self.state["cats"].values()
            for event in cat["events"]
            if event.get("serial") == serial and (at := timestamp(event.get("at"))) and at <= now
        ]
        return {
            "visits_today": sum(at >= day_start for at in visits),
            "cleans_today": sum(at >= day_start for at in cleanings),
            "last_clean": max(cleanings, default=None),
            "cleans_since_bin_reset": sum(at >= bin_reset_at for at in cleanings) if bin_reset_at else None,
            "last_visit_cat_id": (self.state["box_visits"].get(serial) or {}).get("cat_info_id"),
        }

    def analytics(self, cat_id, now, day_start=None):
        cat = self.cat(cat_id)
        events = [
            (at, e)
            for e in cat["events"]
            if (at := timestamp(e.get("at"))) is not None
            and at <= now
            and number(e.get("duration_seconds")) is not None
        ]
        events.sort(key=lambda x: x[0])
        recent = [(at, e) for at, e in events if at > now - timedelta(hours=24)]
        durations = [float(e["duration_seconds"]) for _, e in recent]
        threshold = self.threshold(cat_id)
        pee = [(at, e) for at, e in events if float(e["duration_seconds"]) < threshold]
        poo = [(at, e) for at, e in events if float(e["duration_seconds"]) >= threshold]
        weights = [e["weight"] for _, e in events if number(e.get("weight")) is not None]
        return {
            "last_visit": events[-1][0] if events else None,
            "last_visit_duration_seconds": events[-1][1]["duration_seconds"] if events else None,
            "visits_24h": len(recent),
            "visits_today": sum(at >= day_start for at, _ in events) if day_start else None,
            "last_visit_weight": next((w for _, e in reversed(events) if (w := number(e.get("weight")))), None),
            "duration_24h": sum(durations),
            "average_duration_24h": round(sum(durations) / len(durations), 2) if durations else None,
            "maximum_duration_24h": max(durations) if durations else None,
            "weight_change": round(weights[-1] - weights[-2], 3) if len(weights) > 1 else None,
            "pee_visits_24h": sum(d < threshold for d in durations),
            "poo_visits_24h": sum(d >= threshold for d in durations),
            "last_pee": pee[-1][0] if pee else None,
            "last_poo": poo[-1][0] if poo else None,
            "classification": "duration_estimate",
            "history_source": "observed_vendor_records",
        }


def remaining_uses(item):
    values = item.get("box_use_times", {})
    count, capacity = number(values.get("boxUseTimes")), number(values.get("boxFullMax"))
    return max(0, capacity - count) if count is not None and capacity is not None and capacity > 0 else None


def waste_full(item):
    values = item.get("box_use_times", {})
    count, threshold = number(values.get("boxUseTimes")), number(values.get("boxFullAlert"))
    return count >= threshold if count is not None and threshold is not None and threshold > 0 else None


def presence(previous, current, suppressed=False):
    if current.get("lid_state") == 1:
        return None, True
    if suppressed:
        if current.get("w_mode_app_name") == "IDLE" and current.get("toilet_state") == 0:
            suppressed = False
        else:
            return None, True
    value = current.get("toilet_state")
    return (value == 1 if value in (0, 1) else None), suppressed
