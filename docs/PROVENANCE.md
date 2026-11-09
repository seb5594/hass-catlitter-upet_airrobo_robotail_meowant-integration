# Source review for an independent release

Cat Litter Hub began in the fork network of
[CrazzyBerg/upet-hass](https://github.com/CrazzyBerg/upet-hass). Credit for the
original idea and technical investigation belongs in the README and
[SOURCES.md](SOURCES.md). The migration of Home Assistant entries from
`ubpet` remains part of the integration.

The candidate replaces the inherited HTTP and MQTT implementations, the
matching entity logic, and the inherited HTTP and MQTT test code. The new
tests retain wire-level facts such as routes, payload fields, command bytes and
expected device states. The unused upstream `secrets.py.example` is excluded
from the component. The brand PNGs are built from this repository's SVG.

The source comparison covered the original and the ten other public source
repositories in `.github/upstream-inventory.json`. It compared their available
branch tips with the candidate, using file hashes and matching text and Python
syntax blocks. This found no identical Python functions of 35 or more syntax
nodes in the candidate. The remaining short matches include Home Assistant
declarations, registry keys and protocol fields. The comparison cannot detect
every derivative passage. The implementation and review had access to the
previous code, so this is not a clean-room certification.

## Artwork and provider data

The editable SVG was added in commit `d123c82` by `seb5594`. It contains vector
paths and shapes without embedded images or external references. Rendering it
with `resvg-py` reproduced all four shipped brand PNGs byte for byte. No
byte-identical artwork was found in the reviewed upstream trees. This
establishes the source of the shipped PNGs. The publisher should still confirm
that they control the rights to the SVG.

`providers.json` describes regional hosts, routing and app identifiers. Those
are interoperability facts, with related findings recorded in
[SOURCES.md](SOURCES.md). Earlier builds bundled four app signing keys. The release candidate
removes them from `mobile_apps.json`. New setups require a key the user is
authorized to use. Existing entries retain their locally stored key.
The review did not find authorization to redistribute the keys or a public
developer program offering them for third-party use. The published [UBPet
website terms](https://www.ubpet.com/pages/terms-conditions) restrict some
automated use of its services. Their applicability to each app endpoint was
not established by this review.

Before publishing under MIT, confirm rights to the files that will ship.
The candidate leaves out the signing keys and accepts locally supplied
credentials. Start an
independent publication from the reviewed tree and retain the attribution in
the README. The inherited commits and older release ZIPs are outside that
review.

## Compatibility

The [shared Compatibility run](https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration/actions/runs/42700507404)
tested implementation commit `8b9c10d` on all 12 targets, from Home Assistant
`2023.6.3` through `2026.11.1`. On `2026.11.1`, 85 regular tests and 48
tests against Home Assistant passed. The tests use simulated cloud traffic.
A device run for each supported provider is still needed to verify live
behavior.
