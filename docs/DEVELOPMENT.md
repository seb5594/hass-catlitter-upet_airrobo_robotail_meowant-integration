# Architecture and extensions

## Data flow

`providers.json` is the only place that knows brands and regions: regions with host and countries, time zone rules for the pre-selection, and every provider with its app profile, allowed regions and optional per-region host/app overrides. `providers.py` only reads this data. `mobile_apps.json` contains only the already publicly documented identifiers of the vendor apps; no personal credentials.

**Adding a brand:** add the app profile to `mobile_apps.json`, the provider to `providers.json` (`label`, `app`, `regions`, and `hosts`/`region_apps` where it differs), one entry in `strings.json` (only if a new region appears) and a test in `.github/tests/test_derived_data.py`. No code has to change. Do not assume a working login just because product names look similar; documented app and server data is required.

**Region pre-selection:** country from the Home Assistant configuration, then time zone, then EU. The basis (`EU · DE`, `NA · America/Chicago`) is shown in the form so that a guess is recognisable as one. The integration deliberately does not try several servers: a wrong region returns the same answer as a wrong password and would pile up failed attempts.

`api.py` contains the shared signed REST client. HTTP calls run outside the Home Assistant event loop; at most four requests run concurrently per dashboard refresh. Authentication is locked. A rejected session is renewed at most once; clear password errors stop further automatic attempts of that client. Optional endpoints that are missing have a bounded negative cache and never delete existing measurements.

`transport.py` manages exactly one Paho connection to the vendor's TLS broker per config entry. Status and commands share the same session. Broker acknowledgements do not confirm that a movement was executed. After a reconnect, device states have to arrive again before movement commands become available.

`coordinator.py` ties together REST, MQTT and the local history. Push messages change data and notify entities without shifting the regular REST schedule. Repeated visit/config hints are merged into one delayed refresh. On unload, tasks, connections and delayed calls are stopped.

`history.py` holds, without Home Assistant dependencies, the deduplication, time normalisation, bounded history and calculations. The store is named `ubpet_cat_litter_hub.<entry_id>.visit_analytics`; adopted entries read the old integration's store `ubpet.<old_entry_id>.visit_analytics` on first start. Records are distinguished per device and stream; numerically identical IDs of different litter boxes do not collide.

`entities.py` bundles the base classes of all platforms (`UbpetDeviceEntity`, `UbpetCatEntity` and the write paths for reminder and time periods), availability, discovery of new devices and cats, and hardware capabilities. `box_config.py` reads pure configuration data (reminder, weekdays, time periods) without a Home Assistant dependency. Entity unique IDs start with the entry's `namespace`: its own entry ID or, for an adopted entry, the ID of the old one.

`legacy.py` adopts entries of the old `ubpet` domain: extend the device with the new entry, move the entities, and only then detach the old entry from the device (Home Assistant would otherwise delete the entities with it). This is triggered once from the menu of the config flow; the emptied old entry is only removed if nothing is attached to it anymore. Cat device identifiers are separated per account. Removed cloud devices are not deleted from the Home Assistant device registry automatically.

`compat.py` confines version differences to a few places: coordinator arguments, frozen entity descriptions, device info and reauth. The feature set is not limited by an artificially high minimum core version.

## Derived values

Everything the vendor API does not provide itself is calculated in `history.py` from observed records and stored durably: visits and cleans today (local day of the Home Assistant time zone), cleans since the bin reset, last clean, cat that used the box last, and weight at the last visit. Cleans are `eventType` 31; according to [bojanrajkovic/upet-hass#6](https://github.com/bojanrajkovic/upet-hass/issues/6) this is inferred from timing and not confirmed for every firmware. Known event numbers (3, 21, 31) get the name `event_name` on the event bus; unknown ones stay numeric.

## Languages

All visible texts live in `strings.json` (English, the source) and `translations/<language>.json`. State values are keys (`standby`, `inside`, `weekdays` …), not texts, and are translated through `state`. Error messages go through `exceptions` (`translated_error` in `compat.py`; older core versions fall back to English). The language follows the Home Assistant user language automatically; if a translation is missing, English is shown. `python .github/checks/project.py` checks every language file for identical keys, non-empty texts and identical placeholders.

## New sensors

Before adding an entity, the data source, unit, unknown state and valid range must be clear. Missing fields do not mean `0` or `False`. Rolling counters use `measurement` because they can decrease even without a reset. A calculated remainder up to the API bin capacity is not an additional physical fill-level measurement.

Protocol fields and their mapping are in `mqtt.py`. Full state messages use proto3 zero values for omitted scalars. RISP checksums and lengths are verified before evaluation. A late-arriving old state snapshot must not overwrite a newer device state.

Unconfirmed warning codes, camera images, OTA commands and medical interpretations are not exposed as reliable sensors. Known starting points are listed in [SOURCES.md](SOURCES.md).

## Tests

Regular run:

```bash
python -m pip install -r .github/dev/requirements-dev.txt
python -m pytest -c .github/dev/pyproject.toml --rootdir . .github/tests
python .github/checks/project.py
```

With a real core installation, also pass `.github/ha_tests` to pytest. The shared engine creates separate environments with a matching Python and the test plugin for this. Regular tests need no vendor accounts.

The brand artwork is an SVG in `assets/cat-litter-hub.svg`. `resvg-py` and `python tools/build_brand.py` render the four integration PNGs from it. The rendered files do not have to be regenerated at runtime.
