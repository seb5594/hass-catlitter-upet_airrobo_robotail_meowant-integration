# Source and licensing notes

Cat Litter Hub started in the fork network of
[CrazzyBerg/upet-hass](https://github.com/CrazzyBerg/upet-hass). The README and
[SOURCES.md](SOURCES.md) credit the original idea and protocol research.
Migration from the earlier Home Assistant domain is part of the integration.

The MIT license applies to the current project source and artwork starting
with release 2026.11.09.1. The earlier upstream commits and release archives
retain their respective rights status. The [upstream license inquiry](https://github.com/CrazzyBerg/upet-hass/issues/8)
remains open.

## Release source

The HTTP and MQTT implementations, inherited entity logic and API and MQTT
tests were rewritten. Tests retain the protocol facts needed for
compatibility. The maintainer confirmed that the cat profile fields were
observed through personal use of the UBPet (UPET) and Robotail apps. The
sensor maps those fields to the existing Home Assistant attributes using a
fresh implementation. The matching English and Ukrainian labels were
rewritten from the functions of the devices. Entity registry keys,
translation keys and raw state values remain compatible.

The four brand PNGs render from the new, self-contained vector drawing at
`assets/cat-litter-hub.svg`. It depicts a cat, a tray and a sparkle using
simple shapes and has no external assets. The HACS ZIP includes the license
next to the component files.

## Provider access

Profiles describe regional hosts, routing and app identifiers. The public
release ZIP includes no app signing keys. The setup flow can read an optional
`vendor_app_keys.json` supplied in a separate local installation package.
The file maps app profile names to signing keys and is outside the project's
MIT license grant. Existing entries retain their locally stored key. A new
entry can use the supplied key for its selected app profile automatically.

A public third-party credential issuance path could not be verified. The
published [UBPet terms](https://www.ubpet.com/pages/terms-conditions) describe
limits on automated use of the covered services. The terms applicable to
each app endpoint were not established by the review. Automated compatibility
tests simulate cloud traffic.
