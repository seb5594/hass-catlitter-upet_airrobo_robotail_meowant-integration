# Changelog

## 2026.11.03.2

- **Dashboard cards**, registered automatically: `ubpet-litter-box-card` (status, cat presence, waste bin, info chips, actions, statistics) and `ubpet-cat-card` (weight and visit statistics). Sections, chips, actions and statistics are selectable and orderable in a visual editor.
- Devices now carry the model `Litter box` or `Cat`, which the card editor uses to offer only matching devices.

## 2026.11.03.1

- **New domain `ubpet_cat_litter_hub`** (folder `custom_components/ubpet_cat_litter_hub`). Entries of the old `ubpet` domain can be adopted once from the menu when adding the integration, including entity IDs, devices, visit history, thresholds and options. Create a backup first and remove the old folder.
- Providers and regions come from `providers.json`; the pre-selection uses the country, then the time zone, and shows its basis.
- **Multilingual:** translations for 20 languages (de, en, fr, es, it, nl, pl, pt, pt-BR, ru, uk, cs, sv, da, nb, fi, tr, ja, ko, zh-Hans, zh-Hant). State values and error messages are translatable.
- **Attention, state values changed:** box status is now `standby`/`running`/`paused`, cat position `inside`/`away`. Automations that compare against the English texts need to be adjusted.
- Empty-bin reminder: the select offers translated presets (off, every day, weekdays, weekend); arbitrary combinations through seven weekday switches (disabled by default).
- New: visits today, cleans today, last clean, cleans since bin reset, last used by, scheduled cleans; per cat visits today and weight at last visit; foreign object detection switch.
- A box that reports mode `IDLE` with state `RUNNING` is treated as idle, so start commands stay available.
- The events `ubpet_box_event` and `ubpet_visit` carry `event_name` for known event numbers.
- Cleaned up: shared base classes instead of ninefold repetition, removed the unused one-shot MQTT path and the obfuscated default bundle, less work on every push message.

## 2026.11.02.1

- Multiple providers and accounts in one integration with explicit server region and regional pre-selection.
- Adopt existing `ubpet` entries, entity unique IDs and the visit store of the multi-region fork.
- Persistent MQTT per account instead of repeated reconnects and per-second state polling.
- Handle session takeovers, login failures and owner permissions; fewer routine logs.
- Visit events, persistent deduplication and additional factual visit statistics.
- Keep the urine/stool estimates and their thresholds and label them clearly as estimates.
- Additional presence and fault sensors, configuration switches and odour block reset.
- German setup, German documentation, shared workflow and own brand artwork.
- Compatibility bridges for older core versions; determine the minimum version through real runtime tests.

Hardware confirmation for this development state is still open.
