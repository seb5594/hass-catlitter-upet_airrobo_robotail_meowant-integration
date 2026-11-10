# Sources and open findings

As of 2 November 2026. Covered were the original, all ten direct forks returned by the public fork API and the additional PnnnG sub-fork: twelve repositories in total. The GitHub UI counts the network including the sub-fork as eleven forks. Private, deleted or otherwise unfindable historical forks are therefore not covered.

All published remote branches were inventoried with their SHA and compared against the original state. Issues and pull requests were read with state=all; existing issue comments were fetched as well. Unpublished local branches of other developers are not accessible.

## Result by repository

### [CrazzyBerg/upet-hass](https://github.com/CrazzyBerg/upet-hass)

Starting point; login problems, greyed-out commands, NA and Meowant pull requests and the open license request in issue #8.

- `main` → [`3b8af41ddb13`](https://github.com/CrazzyBerg/upet-hass/commit/3b8af41ddb13104bb3e2a0249ca226a8bb6b993f)

Issues recorded: 5; pull requests: 3.

- [#8: Robotail C42 extensions: contribution offer and license/redistribution question](https://github.com/CrazzyBerg/upet-hass/issues/8)
- [#7: Add deodorant-block reset button](https://github.com/CrazzyBerg/upet-hass/issues/7)
- [#6: Login Failed](https://github.com/CrazzyBerg/upet-hass/issues/6)
- [#5: Add Meowant support](https://github.com/CrazzyBerg/upet-hass/issues/5)
- [#4: Add support for North America](https://github.com/CrazzyBerg/upet-hass/issues/4)
- [#3: Actions greyed out](https://github.com/CrazzyBerg/upet-hass/issues/3)
- [#2: Authentication failed](https://github.com/CrazzyBerg/upet-hass/issues/2)
- [#1: Login does not work](https://github.com/CrazzyBerg/upet-hass/issues/1)

### [Jster42/upet-hass](https://github.com/Jster42/upet-hass)

feature/meowant-support: Meowant tenant, account country and model differences. Do not derive rake functions from the provider name for every model.

- `feature/meowant-support` → [`0934de95f57f`](https://github.com/Jster42/upet-hass/commit/0934de95f57f5a2d653082a4e56dfc139f4ee23f)
- `main` → [`3b8af41ddb13`](https://github.com/Jster42/upet-hass/commit/3b8af41ddb13104bb3e2a0249ca226a8bb6b993f)

Issues recorded: 0; pull requests: 0.

### [KennebecRiver66/upet-hass-multi-region](https://github.com/KennebecRiver66/upet-hass-multi-region)

Sub-fork of PnnnG: explicit NA/Asia regions and additional ubtrobot.com hosts. Alternative hosts are classified as experimental.

- `feat/airpet-ubtrobot-hosts` → [`6ced8ba0cc84`](https://github.com/KennebecRiver66/upet-hass-multi-region/commit/6ced8ba0cc84a198e2a7e0e0538a56cf72f06593)
- `main` → [`97695d2232ff`](https://github.com/KennebecRiver66/upet-hass-multi-region/commit/97695d2232ff714498a7adf5cccbac9193a61efe)

Issues recorded: 0; pull requests: 2.

- [#2: Add AIR PET / AIRROBO backend hosts on ubtrobot.com](https://github.com/KennebecRiver66/upet-hass-multi-region/issues/2)
- [#1: Add North America and Asia regions, with explicit region selection](https://github.com/KennebecRiver66/upet-hass-multi-region/issues/1)

### [PnnnG/upet-hass-multi-region](https://github.com/PnnnG/upet-hass-multi-region)

Flat/wrapped login, region-dependent areaCode, persistent visit analytics, pet position and safety conditions for movement.

- `main` → [`722d3d5fa6e6`](https://github.com/PnnnG/upet-hass-multi-region/commit/722d3d5fa6e6f972dff2482d5152869d86619120)

Issues recorded: 0; pull requests: 0.

### [aderusha/upet-hass](https://github.com/aderusha/upet-hass)

Earlier Meowant profile approach on feature/meowant-support; compared together with Jster42 and pfgcoder.

- `feature/meowant-support` → [`9d0ac9879207`](https://github.com/aderusha/upet-hass/commit/9d0ac9879207f0d3d15b1a6ac329ff322ccb0fc2)
- `main` → [`3b8af41ddb13`](https://github.com/aderusha/upet-hass/commit/3b8af41ddb13104bb3e2a0249ca226a8bb6b993f)

Issues recorded: 0; pull requests: 0.

### [bojanrajkovic/upet-hass](https://github.com/bojanrajkovic/upet-hass)

main still contains the starting point. The relevant additions are in the many stack/*, mqtt-push, visit-log and box-diagnostics branches. Push, session conflicts, visit events, presence/maintenance, model capabilities and configuration findings were reviewed.

- `box-diagnostics` → [`bdc045db538b`](https://github.com/bojanrajkovic/upet-hass/commit/bdc045db538b18a4001e0b90d3f662bfb29d506c)
- `fork-maintenance` → [`e69dbe0872e0`](https://github.com/bojanrajkovic/upet-hass/commit/e69dbe0872e092b3ddabe7dff6fa581e78d5ae26)
- `main` → [`3b8af41ddb13`](https://github.com/bojanrajkovic/upet-hass/commit/3b8af41ddb13104bb3e2a0249ca226a8bb6b993f)
- `mqtt-push` → [`856a45f6149e`](https://github.com/bojanrajkovic/upet-hass/commit/856a45f6149ec522f3d5c257cc0c327d8cb66f45)
- `stack/box-controls` → [`b0edf9b78c4d`](https://github.com/bojanrajkovic/upet-hass/commit/b0edf9b78c4dfcfe970ab77fa94b5688cf7b7297)
- `stack/box-sensors` → [`54e2fde56832`](https://github.com/bojanrajkovic/upet-hass/commit/54e2fde56832c6cb907da259ee58db7ecfb6020f)
- `stack/capability-gating` → [`ad084ffce3b2`](https://github.com/bojanrajkovic/upet-hass/commit/ad084ffce3b27ac34a490a2cdb39beae0c781a2a)
- `stack/cat-activity` → [`bb0a4a8efc95`](https://github.com/bojanrajkovic/upet-hass/commit/bb0a4a8efc9563f39039153cf869c033cf33712d)
- `stack/cat-inside` → [`c81a9f6efbac`](https://github.com/bojanrajkovic/upet-hass/commit/c81a9f6efbac7d7767f2e0bc31ac9adf617c2ccb)
- `stack/cover-presence` → [`b96a4bc31d1b`](https://github.com/bojanrajkovic/upet-hass/commit/b96a4bc31d1b2162c8fea08c0925bfe0227582d8)
- `stack/fork-metadata` → [`ed43881e21b1`](https://github.com/bojanrajkovic/upet-hass/commit/ed43881e21b1062360c24a46452eca09a7ab461f)
- `stack/idle-standby` → [`1cc40e81e04b`](https://github.com/bojanrajkovic/upet-hass/commit/1cc40e81e04b08f833da1e4a4e4f8e8e7094ef56)
- `stack/logbook-on-cat-pages` → [`758d5a18866e`](https://github.com/bojanrajkovic/upet-hass/commit/758d5a18866e38844267de316cf6a7c23e223296)
- `stack/more-events` → [`a8747ee17d07`](https://github.com/bojanrajkovic/upet-hass/commit/a8747ee17d07225c14dde20e7f66a28b2c5c2794)
- `stack/mqtt-connection` → [`37ebe31d0a91`](https://github.com/bojanrajkovic/upet-hass/commit/37ebe31d0a915481fbbca0330cd5a0b493de958b)
- `stack/session-handling` → [`ff5a53e70362`](https://github.com/bojanrajkovic/upet-hass/commit/ff5a53e70362f028bfe2bb0b539afc99ee5473c8)
- `stack/us-region` → [`f3ce24cf712f`](https://github.com/bojanrajkovic/upet-hass/commit/f3ce24cf712f21fc85b1fcc23a77a1586cc0b4d5)
- `stack/visit-log` → [`4bbf3b5d03f2`](https://github.com/bojanrajkovic/upet-hass/commit/4bbf3b5d03f2ba081170f5927d5c6d263f5da866)
- `us-region` → [`ad6e2513a368`](https://github.com/bojanrajkovic/upet-hass/commit/ad6e2513a36883bd535be9531146174e31f7fd7c)
- `visit-log` → [`2957a80ca4fd`](https://github.com/bojanrajkovic/upet-hass/commit/2957a80ca4fdd8a915820f34f95f14ac5b65f7cf)

Issues recorded: 8; pull requests: 16.

- [#25: Show visits on the cat's device page](https://github.com/bojanrajkovic/upet-hass/issues/25)
- [#24: Only create entities for hardware the box has](https://github.com/bojanrajkovic/upet-hass/issues/24)
- [#22: Don't mistake cover maintenance for a cat](https://github.com/bojanrajkovic/upet-hass/issues/22)
- [#21: Add child lock, shake mode, bin-full alert and threshold controls, plus a deodorant reset](https://github.com/bojanrajkovic/upet-hass/issues/21)
- [#20: Add fault, presence and light sensors from the box's state pushes](https://github.com/bojanrajkovic/upet-hass/issues/20)
- [#19: Show each cat's activity: daily counts, device-page links, first-record fix](https://github.com/bojanrajkovic/upet-hass/issues/19)
- [#18: Present the fork as the maintained integration](https://github.com/bojanrajkovic/upet-hass/issues/18)
- [#17: Fire events for box records, presence changes and undecoded messages](https://github.com/bojanrajkovic/upet-hass/issues/17)
- [#16: Stay off the account while another login holds the session](https://github.com/bojanrajkovic/upet-hass/issues/16)
- [#15: Treat idle boxes that report running as standby](https://github.com/bojanrajkovic/upet-hass/issues/15)
- [#14: Add a Cat inside sensor per box](https://github.com/bojanrajkovic/upet-hass/issues/14)
- [#13: Replace MQTT state polling with a persistent connection](https://github.com/bojanrajkovic/upet-hass/issues/13)
- [#12: Fire an event for every litter box visit](https://github.com/bojanrajkovic/upet-hass/issues/12)
- [#11: Add US and Canada accounts from the AIR PET app](https://github.com/bojanrajkovic/upet-hass/issues/11)
- [#10: Check the deodorant countdown after a reset](https://github.com/bojanrajkovic/upet-hass/issues/10)
- [#9: Waste bin use counter stays at 0](https://github.com/bojanrajkovic/upet-hass/issues/9)
- [#8: Add box fault sensors and the app's remaining settings](https://github.com/bojanrajkovic/upet-hass/issues/8)
- [#7: Per-cat period reports (day/week/year averages and trends)](https://github.com/bojanrajkovic/upet-hass/issues/7)
- [#6: Map box warning records to names](https://github.com/bojanrajkovic/upet-hass/issues/6)
- [#5: Camera snapshot per visit](https://github.com/bojanrajkovic/upet-hass/issues/5)
- [#4: Cleaning schedules](https://github.com/bojanrajkovic/upet-hass/issues/4)
- [#3: Firmware update entity (read-only)](https://github.com/bojanrajkovic/upet-hass/issues/3)
- [#2: Health alerts per cat](https://github.com/bojanrajkovic/upet-hass/issues/2)
- [#1: Make this fork the maintained UPET / Airrobo / Meowant integration](https://github.com/bojanrajkovic/upet-hass/issues/1)

### [dantaeyoung/upet-hass](https://github.com/dantaeyoung/upet-hass)

Older state 1.0.2; no additional remote branches or issues in the API listing.

- `main` → [`9a812ac271f4`](https://github.com/dantaeyoung/upet-hass/commit/9a812ac271f4d1f606e2ba8760c168c715fec3c1)

Issues recorded: 0; pull requests: 0.

### [hermeneanc/robotail-hass](https://github.com/hermeneanc/robotail-hass)

Own Robotail app profile on the same protocol family; the different app namespace is decisive for which devices are visible. The repository names C32/C42, not a confirmed C31.

- `main` → [`57a2d0933045`](https://github.com/hermeneanc/robotail-hass/commit/57a2d0933045a3c5b40f4842a3d95cc81eb5550d)

Issues recorded: 0; pull requests: 0.

### [lorenzomigliorero/upet-hass](https://github.com/lorenzomigliorero/upet-hass)

add-deodorant-reset-button: confirmed POST to deodorant-block/replaced; implemented as a separate config button.

- `add-deodorant-reset-button` → [`890356ad4652`](https://github.com/lorenzomigliorero/upet-hass/commit/890356ad46522b2a5b93511f785dfd2660911263)
- `main` → [`3b8af41ddb13`](https://github.com/lorenzomigliorero/upet-hass/commit/3b8af41ddb13104bb3e2a0249ca226a8bb6b993f)

Issues recorded: 0; pull requests: 0.

### [mrozekma/upet-hass](https://github.com/mrozekma/upet-hass)

main is older than the starting point; regions branch with EU/NA data and idle-state findings. BLOCKED must not disappear during idle normalisation.

- `main` → [`9a812ac271f4`](https://github.com/mrozekma/upet-hass/commit/9a812ac271f4d1f606e2ba8760c168c715fec3c1)
- `regions` → [`687b1e9da552`](https://github.com/mrozekma/upet-hass/commit/687b1e9da55250de63d4bc73692e92d9835e4ba0)

Issues recorded: 0; pull requests: 0.

### [pfgcoder/meowant-hass](https://github.com/pfgcoder/meowant-hass)

Active Meowant adaptation: provider profiles, persistent MQTT session, capabilities, error cases for null responses and settings; mind owner permissions and password errors.

- `main` → [`8c66e172fc16`](https://github.com/pfgcoder/meowant-hass/commit/8c66e172fc166c1c186c65b27c95b5de230b6f67)

Issues recorded: 0; pull requests: 0.

### [seb5594/hass-ubpet_cat_litter_hub-integration](https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration)

Target fork. The repository was named differently for a while and is now called hass-ubpet_cat_litter_hub-integration.

- `main` → [`3b8af41ddb13`](https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration/commit/3b8af41ddb13104bb3e2a0249ca226a8bb6b993f)

Issues recorded: 0; pull requests: 0.

## What was implemented from this

Shared REST/RISP core, separate provider profiles, explicit account region, multiple entries, one MQTT session per account, login backoff, persistent visit events, additional factual sensors and preservation of the earlier estimate sensors. Existing API data and account connections are not overwritten because an optional endpoint is temporarily missing.

## Review of issues and pull requests

As of 3 November 2026, read through GitHub search (title and description; comments only where present).

| Source | Finding | Implementation |
| --- | --- | --- |
| CrazzyBerg #6 | Login with `code=2002` ("wrong user or password"), `areaCode` empty | `areaCode` is always set from the chosen country; the error message names the region as a possible cause |
| CrazzyBerg #3, PR #4 | Controls permanently greyed out because mode `IDLE` is reported with state `RUNNING` | Availability takes the mode into account instead of the state alone |
| CrazzyBerg PR #4, #5 | North America profile, Meowant profile, SC-01 idle | as provider/region profiles in `providers.json` |
| CrazzyBerg PR #7, lorenzomigliorero | `POST …/deodorant-block/replaced` | "Reset deodorant" button |
| CrazzyBerg #8 | Robotail C42, license question | license status stays open (README) |
| bojanrajkovic #4 | Schedules in `taskConfigList` | "Scheduled cleans" sensor (number of active ones, times as attribute); editing deliberately not implemented (variable list length) |
| bojanrajkovic #6 | Event numbers 3, 21, 31 known; warning codes unknown | `event_name` only for 3, 21, 31 |
| bojanrajkovic #9 | Bin counter stays 0 | "Cleans since waste bin reset" from the device records |
| bojanrajkovic #10 | Odour block may not count down | open, needs hardware observation |
| bojanrajkovic #2 | Health alert per cat (`/web/cat/health/config`), toggles phone pushes | not implemented: changes the owner's notifications |
| bojanrajkovic #3, #5 | Firmware update entity, camera image over a second MQTT session | not implemented: no proven benefit, risk for the session |
| bojanrajkovic #7 | Daily/weekly/yearly report per cat | not implemented: semantics of week/year unclear |
| Meowant fork | `foreign_object_detection`, `cleans_today`, `visits_today`, `last_used_by` | adopted as switch and sensors |

## What still needs evidence or hardware tests

- Robotail C31 is only a guess about the neighbour's device. The Robotail source fork names C32/C42. Confirm the model on the label or in the app.
- Not every brand is demonstrably a sub-brand of the same company. The software combines protocol compatibility, not an unproven ownership structure.
- Camera/image transfer and the firmware update protocol are starting points in bojanrajkovic's issues #3/#5; image capability and a parallel session are not generally proven. No OTA install commands were added.
- Warning event numbers such as 31 or 52 are not confirmed for all firmwares. Unknown codes stay numeric instead of being given invented causes.
- Daily/weekly/yearly reports and health alerts are described in the source material. Averaging semantics, time windows and possible effects on phone notifications are partly open.
- Camera capability and state fields have to be checked on the C20/Robotail. A permanently present cameraSwitch field alone is no proof of camera hardware.
- More history than the configurable fetch limit needs confirmed pagination. A limited fetch is therefore reported as limited; a complete long-outage backfill is not claimed.
- Visits appear as `ubpet_visit`/`ubpet_box_event` on the event bus. A dedicated logbook presentation and extended device triggers have not been added yet.
- The original code and the researched forks contain no license file. Upstream issue #8 asks for permission; no answer exists in the examined snapshot.

## Cloud and app cross-check

- The Gladys integration highlights a combined last-visit summary per litter box. Cat Litter Hub uses its own stored visit records to show these details on its existing sensor and dashboard card. [Gladys UBPet features](https://github.com/StereoMuff/gladys-ubpet/blob/e75a25067b0927c2dae9d825cfb0520a19764660/docs/en.md#what-you-get)
- VIVIDMOO PET names AIRROBO in its app listing. An independent Home Assistant integration reports testing its litter box on the EU AIRROBO endpoint. Its app credentials must be supplied by the user. [VIVIDMOO PET](https://play.google.com/store/apps/details?id=com.vividmoo.vividmoopet) · [Vividmoo integration](https://github.com/edied2002/vividmoo-ha/tree/9ddf4136606d7c6baac70199d3eacaaec67e5c38)

- UBTECH publishes separate UPET and UPET-NA Android apps. Both listings describe AIRROBO litter boxes. [UPET](https://play.google.com/store/apps/details?id=com.ubtrobot.catlitterbox.overseaseu) · [UPET-NA](https://play.google.com/store/apps/details?id=com.ubtrobot.catlitterbox.overseasna)
- The AIR PET listing names Meowant. Independent testing reports live login and MQTT verification for Meowant and identifies the AIR PET app ID and backend used by this provider. [AIR PET on Google Play](https://play.google.com/store/apps/details?id=com.yibainetwork.airpet) · [Meowant protocol notes](https://github.com/Abbondanzo/ha-meowant/blob/38338bc7bd63c7f11f46f3f1640054b5f34e8eb8/API.md#tenants)
- Robotail publishes its own app. The Robotail integration documents the shared cloud protocol. [Robotail app](https://robotailpets.com/pages/app) · [Robotail integration](https://github.com/hermeneanc/robotail-hass)
- One UPET-NA review mentions a Dyersburg C31 that the app discovers but cannot pair. The cloud account and login remain unverified for that device. [UPET-NA store review](https://play.google.com/store/apps/details?hl=en_ZA&id=com.ubtrobot.catlitterbox.overseasna)

## Brand relationship

[UBPet](https://www.ubpet.com/pages/about-us) and [AIRROBO](https://air-robo.com/pages/about-airrobo) name UBTECH as trademark owner. The old [airrobo-home site](https://www.airrobo-home.com/) points to UBPet. Robotail and Meowant are named here because of their documented technical profiles; no higher-level trademark ownership is derived from that.
