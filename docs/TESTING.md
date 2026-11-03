# Device testing

Software tests do not replace a test on a real litter box. For this version there is no confirmation yet on the C20 or on the neighbour's device. The exact model of the Robotail device still has to be checked on its label or in the app; C31 is only a guess so far.

## Switching over on the UBPet C20

1. Create a backup and note the old entity IDs or their count. The screenshot of the existing installation showed 54 entities for two cats and one litter box; the actual number depends on the device capabilities.
2. **Delete** the old folder `<config>/custom_components/ubpet` and unpack `ubpet_cat_litter_hub.zip` into a separate folder. Copy its content to `<config>/custom_components/ubpet_cat_litter_hub`. The old config entry and `.storage` stay untouched.
3. Restart Home Assistant. The old entry shows up as not loadable. Under **Settings → Devices & services → Add integration → Cat Litter Hub** choose **Adopt the existing UPET setup**. Then check that existing entity IDs, automations, cats, visit history and individual duration thresholds are still there and that the old entry is gone. If the old integration is still running, the flow aborts with a hint.
4. Compare account provider, server region and account country with the phone app. A German account will typically suggest EU; the account region is what counts.
5. Check whether weight, firmware, bin counter, odour block and online status match the app. An API fill level is not automatically a physical fill-level measurement.
6. Without sending any movement command, wait for a normal cat visit. Compare presence, last visit, visit duration and the 24-hour counters. Several visits before a REST refresh must not collapse into one.
7. Restart Home Assistant and check that visits do not appear twice and duration thresholds are preserved.
8. On an empty, normally operational device, test a known cleaning cycle: start, pause, resume. No start commands may be enabled during a visit. Open the cover for maintenance: the presence indicator must not report that as a cat visit.
9. Change the clean delay while automatic cleaning is switched off: it must stay off. Restore the previous value.
10. Sign in with the phone app as usual. Check that the integration backs off when the session is taken over and comes back without constant login messages.

Urine/stool values are only estimated from the duration. A changed threshold re-classifies the stored visits; it does not measure a different kind of excretion.

## Checking the new values

- Compare **visits/cleans today** with the day view of the app; "today" follows the Home Assistant time zone and resets at midnight at the latest on the next REST refresh.
- Check **cleans since bin reset** after "Reset waste bin" and one cleaning. If the vendor counter stays at 0 (bojanrajkovic/upet-hass#9), this value is the reliable alternative.
- Check **last used by** and **weight at last visit** after a known visit.
- Compare **scheduled cleans** with the schedules in the app.
- Only toggle **foreign object detection** and the weekday switches of the empty-bin reminder (disabled by default) on matching hardware and verify the state in the app.
- Change the language of the user profile and check that entity names, states (box status, cat position) and error messages follow.

## Second account / Robotail

Create another entry with the provider **Robotail**. The neighbour's account is entered by them personally. The first account must keep working. If both accounts contain the same numeric cat IDs, devices and values must not be mixed up. Then run the same status and visit tests.

Rake commands are disabled by default on new installations. Enable them only on matching hardware. A shared app/API does not prove that a model has a litter rake.

## Useful feedback

Please provide model, firmware, app name, chosen provider, server region, account country, Home Assistant version and the concrete comparison between app and entity. The built-in diagnostics are helpful as well. Do not post passwords, tokens or raw cloud captures in issues.

## Automated checks

The regular suite is in `.github/tests`, the tests with real Home Assistant classes are in `.github/ha_tests`. The shared compatibility pipeline uses a separate Python and test environment per core version. Most recently 113 tests ran under core 2026.2.3 (Python 3.13), including creating the entities of all seven platforms and adopting old entries with real registries. The older core versions have not been re-run with this scope; the compatibility pipeline is responsible for that. The adoption tests need the plugin `pytest-homeassistant-custom-component` and are skipped without it. Core 2023.7.3 was checked earlier as well. The minimum version is 2023.6.0. In an additional test under 2023.3.0 the importable module `homeassistant.components.time` was missing, so that version is not declared fully supported. These tests use real core classes; the device-level end-to-end check remains open.

```bash
python -m pytest -c .github/dev/pyproject.toml --rootdir . .github/tests .github/ha_tests
```

For local core tests, install the respective Home Assistant version together with the matching Python version and `paho-mqtt==2.1.0` in a separate virtual environment. The regular developer suite needs no login and no real hardware.
