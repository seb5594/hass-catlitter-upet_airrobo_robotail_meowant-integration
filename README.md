<!-- header:begin (generated from project metadata) -->
<h1 align="center">Cat Litter Hub – UPET / UBPet / AIRROBO / Robotail / Meowant</h1>

<p align="center">
  <img src="https://raw.githubusercontent.com/seb5594/hass-ubpet_cat_litter_hub-integration/main/custom_components/ubpet_cat_litter_hub/brand/logo@2x.png" alt="Cat Litter Hub – UPET / UBPet / AIRROBO / Robotail / Meowant" width="160" height="160">
</p>

---

<p align="center">
  <a href="https://paypal.me/seb5594"><img src="https://img.shields.io/static/v1?label=Support&amp;message=PayPal&amp;color=0070BA&amp;logo=paypal&amp;logoColor=white&amp;style=for-the-badge" alt="PayPal" height="40"></a>
  <a href="https://buymeacoffee.com/seb5594"><img src="https://img.shields.io/static/v1?label=Support&amp;message=Buy%20Me%20a%20Coffee&amp;color=FFDD00&amp;logo=buy-me-a-coffee&amp;logoColor=black&amp;style=for-the-badge" alt="Buy Me a Coffee" height="40"></a><br>
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=seb5594&amp;repository=hass-ubpet_cat_litter_hub-integration&amp;category=integration"><img src="https://img.shields.io/static/v1?label=HACS%20%C2%B7%20Marketplace&amp;message=Add%20integration&amp;color=41BDF5&amp;logo=homeassistantcommunitystore&amp;logoColor=white&amp;style=for-the-badge" alt="HACS · Marketplace" height="28"></a>
  <a href="https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration/actions/workflows/compat.yml"><img src="https://img.shields.io/static/v1?label=home%20assistant&amp;message=%E2%89%A5%202023.6.0&amp;color=1877A5&amp;style=for-the-badge" alt="home assistant" height="28"></a>
  <a href="https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration/releases/tag/v2026.11.03.2"><img src="https://img.shields.io/static/v1?label=version&amp;message=2026.11.03.2&amp;color=1877A5&amp;style=for-the-badge" alt="version" height="28"></a><br>
  <a href="https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration/releases"><img src="https://img.shields.io/github/downloads/seb5594/hass-ubpet_cat_litter_hub-integration/v2026.11.03.2/total?label=downloads&amp;color=1877A5&amp;style=flat" alt="downloads" height="20"></a>
  <a href="https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration/issues"><img src="https://img.shields.io/github/issues/seb5594/hass-ubpet_cat_litter_hub-integration?label=issues&amp;style=flat" alt="issues" height="20"></a>
  <img src="https://img.shields.io/static/v1?label=tests&amp;message=78%20passed&amp;color=2F855A&amp;style=flat" alt="tests" height="20">
  <a href="https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/seb5594/hass-ubpet_cat_litter_hub-integration/ci.yml?branch=main&amp;label=checks&amp;style=flat" alt="checks" height="20"></a>
</p>
<!-- header:end -->

<p align="center"><b>🇬🇧 English</b> · <a href="README.de.md">🇩🇪 Deutsch</a></p>

A Home Assistant integration for smart cat litter boxes that share the UBPet / AIRROBO cloud API: **UPET, UBPet, AIR PET, AIRROBO, Robotail and Meowant**. Several accounts, providers and account regions run side by side in one integration, each with its own connection.

**Status: 2026.11.03.1 · hardware test with this version still open.** The software is checked automatically (unit tests, tests with real Home Assistant classes, adoption of old entries with real registries). A matching API alone does not prove that every model supports every function; what still has to be verified on the C20 and on Robotail is listed in [TESTING.md](docs/TESTING.md).

## What it does

- **Provider and region per account.** The region is an explicit choice. The Home Assistant country and time zone only provide the pre-selection and show what it was derived from (`EU · DE`, `NA · America/Chicago`).
- **One persistent, encrypted MQTT connection per account** for status messages and commands; no local broker needed. REST sync every three minutes (60–3600 s configurable), plus after visit and configuration messages, with at most four parallel requests per account.
- **Status and diagnostics:** box status, weight, waste bin, odour block, firmware, online, cover, drum, scale, camera, light, cat presence. Hardware-dependent entities are only created if the device reports them.
- **Visit history** with durably stored deduplication and up to 10,000 visits per cat. Derived from it: visits and time in the box over 24 hours, **visits and cleans today**, last clean, **cleans since bin reset** (a substitute if the vendor counter gets stuck), cat that used the box last, weight at the last visit and weight change.
- **Control:** automatic cleaning including delay, child lock, shake mode, foreign object detection, bin warning, do-not-disturb and light schedule, empty-bin reminder (time, presets and individual weekdays). Reset the bin and the odour block. Cleaning, smoothing and rake are only enabled when the device allows it; a box that reports "running" while idle stays operable.
- **Scheduled cleans** as a sensor (number of active ones, times as attribute).
- **Events** `ubpet_visit`, `ubpet_box_event` and `ubpet_presence` for automations; known event numbers carry a readable `event_name`.
- **New devices and cats** are discovered while running. Cats with the same cloud ID in different accounts stay separate.
- **Languages:** UI, entity names, states and error messages follow the Home Assistant language automatically: German, English, French, Spanish, Italian, Dutch, Polish, Portuguese (PT/BR), Russian, Ukrainian, Czech, Swedish, Danish, Norwegian, Finnish, Turkish, Japanese, Korean, Chinese (simplified/traditional). If a language is missing, English is shown.
- **Downloadable diagnostics** with credentials, device and pet identifiers redacted.

**Urine/stool are estimates based on the visit duration.** The entities and the adjustable duration threshold are kept but explicitly labelled "estimated"; the API does not confirm a kind of excretion.

## Installation

New accounts need a signing key you are authorized to use for the selected vendor app and region. Enter it in the account form. Existing entries retain the key already stored in Home Assistant.

Home Assistant Core **2023.6.0 or newer**, see [hacs.json](hacs.json). The state of the versions actually tested is described in [TESTING.md](docs/TESTING.md).

1. In HACS, add `https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration` under **Custom repositories** as an **Integration**.
2. Install **Cat Litter Hub** and restart Home Assistant.
3. Under **Settings → Devices & services → Add integration**, search for **Cat Litter Hub** (the brands UPET, UBPet, AIRROBO, Robotail and Meowant find the entry as well).

### Switching from the UPET integration or a fork

The domain is now `ubpet_cat_litter_hub`. This lets the integration be installed next to the original (CrazzyBerg) and the forks without the two getting in each other's way. Existing entries of the old `ubpet` domain can be adopted, **keeping** entity IDs, devices, visit history, duration thresholds and options:

1. Create a Home Assistant backup.
2. Remove the folder `custom_components/ubpet` (the old integration must no longer run), install Cat Litter Hub, restart Home Assistant.
3. **Add integration → Cat Litter Hub → Adopt the existing UPET setup.** Repeat for every old entry. The emptied old entry disappears by itself afterwards.

The former standalone `robotail` domain is not rewritten automatically; create a new Cat Litter Hub entry with the provider **Robotail** instead. Note: box status and cat position now return keys (`standby`, `running`, `paused`; `inside`, `away`) instead of English texts so that they can be translated. Please adjust automations that compare against the old texts.

## Setting up an account

1. Select the **app of the account**. The print on the litter box is not decisive.
2. Enter the **server region of the account** and the country used at registration. The pre-selection is a suggestion; the region in the app is what counts.
3. Enter account and password. The password is taken over unchanged and hashed internally for the proprietary login.
4. For another provider or account, choose **Add entry** again.

| Choice | Backend | Notes |
| --- | --- | --- |
| UPET / UBPet | EU, North America, Japan/Korea, Russia | Regional endpoints; North America has a different app ID |
| AIR PET / AIRROBO | Same regional Airrobo endpoints | Own app profile; do not derive it from the hardware brand |
| Robotail | Regional Airrobo endpoint with the Robotail app ID | EU described in the source fork; other regions without hardware confirmation |
| Meowant | `apis.airrobo-home.com` | Fixed NA/global backend host; still enter the account country |
| AIR PET on `ubtrobot.com` | EU, North America, global, China | Experimental: known alternative hosts, no general account confirmation yet |

The integration **does not try credentials on different servers automatically**: a wrong region gives the same answer as a wrong password, and every failed attempt counts. If the login fails, first compare app, account region and account country. After a clear password rejection, further automatic login attempts of that client are stopped.

The vendor partly allows only one session per account. When another login takes the session over, the integration backs off with a growing delay and also pauses REST logins. A separate account shared by the owner can help; some settings still require owner rights.

## Dashboard cards

Two cards are registered automatically when the integration loads; no resource has to be added and no file copied. They appear in the card picker as **Cat Litter Hub – Litter box** and **Cat Litter Hub – Cat** and have a visual editor. Entities are found through the device, so renaming entities does not break a card, and all texts follow your language.

```yaml
type: custom:ubpet-litter-box-card
device_id: <litter box device>      # chosen in the editor
name: Cat litter box                # optional
image: /local/litter-box.png        # optional picture
sections: [status, presence, bin, chips, actions, stats]   # order and visibility
chips: [online, deodorant, child_lock, auto_clean_delay, problems]
actions: [clean, flatten, reset_bin, request_state]
stats: [cleans_today, last_clean, last_used_by]
```

```yaml
type: custom:ubpet-cat-card
device_id: <cat device>
show_picture: true
stats: [cat_last_visit_duration, visits_split, cat_last_poo, cat_last_pee]
```

Available `actions`: `clean`, `pause_clean`, `resume_clean`, `flatten`, `pause_flatten`, `resume_flatten`, `rake_up`, `rake_down`, `reset_bin`, `reset_deodorant`, `request_state`, `rest_request` (reset actions ask for confirmation; buttons the device currently does not allow are greyed out). Available `stats` for the litter box: `visits_today`, `cleans_today`, `last_clean`, `last_visit`, `last_used_by`, `cleans_since_bin_reset`, `remaining_bin_uses`, `scheduled_cleans`, `firmware_version`; for a cat: `cat_last_visit_duration`, `visits_split`, `cat_visits_24h`, `cat_visits_today`, `cat_last_visit`, `cat_last_poo`, `cat_last_pee`, `cat_pee_visits_24h`, `cat_poo_visits_24h`, `cat_duration_24h`, `cat_average_duration_24h`, `cat_maximum_duration_24h`, `cat_last_visit_weight`, `cat_weight_change`. Selected values that the device does not provide are skipped.

## Data quality and resources

24-hour and daily values refer to the imported vendor records. The attribute `history_complete_24h` and the diagnostic sensor **History fetch limit reached** show possible gaps. A long outage with more records than the fetch limit cannot be reconstructed completely without confirmed pagination. Historical import data is not written retroactively into the recorder. "Today" follows the Home Assistant time zone.

The options control the REST interval (60–3600 seconds), the fetch limit (20–200 records per device and stream) and MQTT. With MQTT disabled, REST sensors stay available; device commands are then unavailable.

Failures of optional endpoints do not replace existing values with zeros. Missing HTTP endpoints are not requested again for an hour. Routine messages are logged at debug level; connection problems are reported once per state change. Frequently changing timestamp diagnostic sensors are disabled by default on new installations.

## Development and sources

- [Device test for C20 and Robotail](docs/TESTING.md)
- [Architecture, new brands and translations](docs/DEVELOPMENT.md)
- [Forks, branches, issues and open findings](docs/SOURCES.md)
- [Version scheme and workflow](docs/WORKFLOW.md)
- [Changelog](CHANGELOG.md)

The starting point is [CrazzyBerg/upet-hass](https://github.com/CrazzyBerg/upet-hass). Important protocol and bug findings come from [PnnnG](https://github.com/PnnnG/upet-hass-multi-region), [Robotail](https://github.com/hermeneanc/robotail-hass), [pfgcoder](https://github.com/pfgcoder/meowant-hass), [bojanrajkovic](https://github.com/bojanrajkovic/upet-hass) and the other forks listed in the sources overview.

## Name and discoverability

**Cat Litter Hub** is the independent integration name, `ubpet_cat_litter_hub` the technical domain. UBPet is UBTECH's brand that carries the "upet/ubpet" word stem; AIRROBO (`airrobo-home.com`) is the shared platform that the manufacturers of other brands run on as well. That is why "ubpet" is in the repository name, while the other brands are in the description, topics, HACS name and this README. No ownership relation to Robotail or Meowant is derived from that. Sources: [UBPet](https://www.ubpet.com/pages/about-us), [AIRROBO](https://air-robo.com/pages/about-airrobo).

Recommended GitHub description:

> Home Assistant / HACS integration for smart cat litter boxes that use the UBPet / AIRROBO cloud: UPET, UBPet, AIR PET, AIRROBO, Robotail and Meowant. Multi-account, multi-region, 20 languages, MQTT push and visit statistics.

Recommended topics:

`home-assistant` · `hacs` · `custom-integration` · `cat-litter` · `litter-box` · `smart-litter-box` · `ubpet` · `upet` · `airrobo` · `air-pet` · `robotail` · `meowant` · `mqtt` · `multi-account` · `multi-region`

## Origin and license status

[Source review for an independent release](docs/PROVENANCE.md)

The original and the examined forks contained no license file at the time of research. [Upstream issue #8](https://github.com/CrazzyBerg/upet-hass/issues/8) explicitly asks about redistribution. This project therefore does not assign an invented license to the third-party code. For a general release and for inclusion in the HACS default catalog, the license status has to be clarified with the rights holders. The upstream history and source references are preserved.

<!-- support:begin (generated, shared text) -->
## Say thanks

All my projects are built in my spare time, just for the fun of it. Still, they take a lot of time and care, and many of the smart home gadgets I buy end up here because I want to make them cloud-free and smart-home ready. Every bit of support means a lot to me.

If my work helped you or turned out to be useful, show your appreciation with a hot drink for my next sleepless night.

[![PayPal](https://img.shields.io/static/v1?label=Support&message=PayPal&color=0070BA&logo=paypal&logoColor=white&style=for-the-badge)](https://paypal.me/seb5594) [![Buy Me a Coffee](https://img.shields.io/static/v1?label=Support&message=Buy%20Me%20a%20Coffee&color=FFDD00&logo=buy-me-a-coffee&logoColor=black&style=for-the-badge)](https://buymeacoffee.com/seb5594)
<!-- support:end -->
