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

For a future MIT publication, review the exact tree that will ship, including
non-code assets and protocol profiles, and confirm that the publisher can
license every file. Start any independent publication from that reviewed tree.
The inherited commits and older release ZIPs are separate from the candidate
and are not covered by the source comparison. Keep the attribution to the
original project in the new README.

Home Assistant 2023.6.3 and 2026.2.3 were checked with the existing shared
workflow engine. The suites use simulated cloud traffic. A device run for each
supported provider is still needed to verify live behavior.
