# Quellen und offene Erkenntnisse

Stand: 2. November 2026. Erfasst wurden das Original, alle zehn von der öffentlichen Fork-API gelieferten direkten Forks und der zusätzliche PnnnG-Unterfork: insgesamt zwölf Repositories. Die GitHub-Oberfläche zählt das Netzwerk einschließlich Unterfork als elf Forks. Private, gelöschte oder nicht auffindbare historische Forks sind damit nicht erfasst.

Alle veröffentlichten Remote-Branches wurden mit SHA inventarisiert und gegen den Originalstand verglichen. Issues und Pull Requests wurden über state=all gelesen; vorhandene Issue-Kommentare wurden zusätzlich abgerufen. Unveröffentlichte lokale Branches anderer Entwickler sind nicht zugänglich.

## Ergebnis nach Repository

### [CrazzyBerg/upet-hass](https://github.com/CrazzyBerg/upet-hass)

Ausgangsbasis; Loginprobleme, ausgegraute Befehle, NA- und Meowant-PRs sowie offener Lizenzwunsch in Issue #8.

- `main` → [`3b8af41ddb13`](https://github.com/CrazzyBerg/upet-hass/commit/3b8af41ddb13104bb3e2a0249ca226a8bb6b993f)

Erfasste Issues: 5; Pull Requests: 3.

- [#8: Robotail C42 extensions: contribution offer and license/redistribution question](https://github.com/CrazzyBerg/upet-hass/issues/8)
- [#7: Add deodorant-block reset button](https://github.com/CrazzyBerg/upet-hass/issues/7)
- [#6: Login Failed](https://github.com/CrazzyBerg/upet-hass/issues/6)
- [#5: Add Meowant support](https://github.com/CrazzyBerg/upet-hass/issues/5)
- [#4: Add support for North America](https://github.com/CrazzyBerg/upet-hass/issues/4)
- [#3: Actions greyed out](https://github.com/CrazzyBerg/upet-hass/issues/3)
- [#2: Authentication failed](https://github.com/CrazzyBerg/upet-hass/issues/2)
- [#1: Login does not work](https://github.com/CrazzyBerg/upet-hass/issues/1)

### [Jster42/upet-hass](https://github.com/Jster42/upet-hass)

feature/meowant-support: Meowant-Tenant, Kontoland und Modellunterschiede. Rechenfunktionen nicht aus dem Anbieternamen für jedes Modell ableiten.

- `feature/meowant-support` → [`0934de95f57f`](https://github.com/Jster42/upet-hass/commit/0934de95f57f5a2d653082a4e56dfc139f4ee23f)
- `main` → [`3b8af41ddb13`](https://github.com/Jster42/upet-hass/commit/3b8af41ddb13104bb3e2a0249ca226a8bb6b993f)

Erfasste Issues: 0; Pull Requests: 0.

### [KennebecRiver66/upet-hass-multi-region](https://github.com/KennebecRiver66/upet-hass-multi-region)

Unterfork von PnnnG: explizite NA-/Asien-Regionen und zusätzliche ubtrobot.com-Hosts. Alternative Hosts sind als experimentell eingeordnet.

- `feat/airpet-ubtrobot-hosts` → [`6ced8ba0cc84`](https://github.com/KennebecRiver66/upet-hass-multi-region/commit/6ced8ba0cc84a198e2a7e0e0538a56cf72f06593)
- `main` → [`97695d2232ff`](https://github.com/KennebecRiver66/upet-hass-multi-region/commit/97695d2232ff714498a7adf5cccbac9193a61efe)

Erfasste Issues: 0; Pull Requests: 2.

- [#2: Add AIR PET / AIRROBO backend hosts on ubtrobot.com](https://github.com/KennebecRiver66/upet-hass-multi-region/issues/2)
- [#1: Add North America and Asia regions, with explicit region selection](https://github.com/KennebecRiver66/upet-hass-multi-region/issues/1)

### [PnnnG/upet-hass-multi-region](https://github.com/PnnnG/upet-hass-multi-region)

Flacher/umhüllter Login, regionabhängiges areaCode, persistente Besuchsanalysen, Pet-Position und Schutzbedingungen bei Bewegung.

- `main` → [`722d3d5fa6e6`](https://github.com/PnnnG/upet-hass-multi-region/commit/722d3d5fa6e6f972dff2482d5152869d86619120)

Erfasste Issues: 0; Pull Requests: 0.

### [aderusha/upet-hass](https://github.com/aderusha/upet-hass)

Früherer Meowant-Profilansatz auf feature/meowant-support; gemeinsam mit Jster42 und pfgcoder verglichen.

- `feature/meowant-support` → [`9d0ac9879207`](https://github.com/aderusha/upet-hass/commit/9d0ac9879207f0d3d15b1a6ac329ff322ccb0fc2)
- `main` → [`3b8af41ddb13`](https://github.com/aderusha/upet-hass/commit/3b8af41ddb13104bb3e2a0249ca226a8bb6b993f)

Erfasste Issues: 0; Pull Requests: 0.

### [bojanrajkovic/upet-hass](https://github.com/bojanrajkovic/upet-hass)

main enthält noch die Ausgangsbasis. Die relevanten Neuerungen liegen in den vielen stack/*-, mqtt-push-, visit-log- und box-diagnostics-Branches. Push, Sitzungskonflikte, Besuchsereignisse, Präsenz/Wartung, Modellfähigkeiten und Konfigurationsbefunde geprüft.

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

Erfasste Issues: 8; Pull Requests: 16.

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

Älterer Stand 1.0.2; keine zusätzlichen Remote-Branches oder Issues in der API-Auflistung.

- `main` → [`9a812ac271f4`](https://github.com/dantaeyoung/upet-hass/commit/9a812ac271f4d1f606e2ba8760c168c715fec3c1)

Erfasste Issues: 0; Pull Requests: 0.

### [hermeneanc/robotail-hass](https://github.com/hermeneanc/robotail-hass)

Eigenes Robotail-App-Profil auf gleicher Protokollfamilie; der andere App-Namensraum ist für sichtbare Geräte entscheidend. Repository nennt C32/C42, nicht einen bestätigten C31.

- `main` → [`57a2d0933045`](https://github.com/hermeneanc/robotail-hass/commit/57a2d0933045a3c5b40f4842a3d95cc81eb5550d)

Erfasste Issues: 0; Pull Requests: 0.

### [lorenzomigliorero/upet-hass](https://github.com/lorenzomigliorero/upet-hass)

add-deodorant-reset-button: bestätigter POST auf deodorant-block/replaced; als eigener Konfigurationsknopf umgesetzt.

- `add-deodorant-reset-button` → [`890356ad4652`](https://github.com/lorenzomigliorero/upet-hass/commit/890356ad46522b2a5b93511f785dfd2660911263)
- `main` → [`3b8af41ddb13`](https://github.com/lorenzomigliorero/upet-hass/commit/3b8af41ddb13104bb3e2a0249ca226a8bb6b993f)

Erfasste Issues: 0; Pull Requests: 0.

### [mrozekma/upet-hass](https://github.com/mrozekma/upet-hass)

main älter als die Ausgangsbasis; regions-Branch mit EU-/NA-Daten und Idle-Zustandsbefunden. BLOCKED darf bei der Idle-Normalisierung nicht verschwinden.

- `main` → [`9a812ac271f4`](https://github.com/mrozekma/upet-hass/commit/9a812ac271f4d1f606e2ba8760c168c715fec3c1)
- `regions` → [`687b1e9da552`](https://github.com/mrozekma/upet-hass/commit/687b1e9da55250de63d4bc73692e92d9835e4ba0)

Erfasste Issues: 0; Pull Requests: 0.

### [pfgcoder/meowant-hass](https://github.com/pfgcoder/meowant-hass)

Aktive Meowant-Anpassung: Anbieterprofile, dauerhafte MQTT-Sitzung, Fähigkeiten, Fehlerfälle bei null-Antworten und Einstellungen; Besitzerrechte und Passwortfehler beachten.

- `main` → [`8c66e172fc16`](https://github.com/pfgcoder/meowant-hass/commit/8c66e172fc166c1c186c65b27c95b5de230b6f67)

Erfasste Issues: 0; Pull Requests: 0.

### [seb5594/hass-catlitter-upet_airrobo_robotail_meowant-integration](https://github.com/seb5594/hass-catlitter-upet_airrobo_robotail_meowant-integration)

Ziel-Fork; Repository während der Arbeit in hass-catlitter-upet_airrobo_robotail_meowant-integration umbenannt.

- `main` → [`3b8af41ddb13`](https://github.com/seb5594/hass-catlitter-upet_airrobo_robotail_meowant-integration/commit/3b8af41ddb13104bb3e2a0249ca226a8bb6b993f)

Erfasste Issues: 0; Pull Requests: 0.

## Was daraus umgesetzt wurde

Gemeinsamer REST-/RISP-Kern, eigene Anbieterprofile, ausdrückliche Kontoregion, mehrere Einträge, eine MQTT-Sitzung je Konto, Login-Backoff, persistente Besuchsereignisse, zusätzliche faktische Sensoren und Erhalt der bisherigen Schätzsensoren. Vorhandene API-Daten und Kontoverbindungen werden nicht wegen eines vorübergehend fehlenden optionalen Endpunkts überschrieben.

## Was noch Belege oder Hardwaretests braucht

- Robotail C31 ist bisher nur eine Vermutung zum Nachbargerät. Der Robotail-Quellfork nennt C32/C42. Modell anhand von Typenschild/App bestätigen.
- Nicht jede Marke ist nachweislich eine Submarke derselben Firma. Die Software fasst Protokollkompatibilität zusammen, keine unbelegte Eigentümerstruktur.
- Kamera-/Bildübertragung und Firmwareupdate-Protokoll sind Ansatzpunkte in bojanrajkovics Issues #3/#5; Bildfähigkeit und parallele Sitzung sind nicht allgemein belegt. Keine OTA-Installationsbefehle ergänzt.
- Warnereignisnummern wie 31 oder 52 sind nicht für alle Firmwares bestätigt. Unbekannte Codes bleiben numerisch statt mit erfundenen Ursachen benannt zu werden.
- Tages-/Wochen-/Jahresberichte und Gesundheitsmeldungen sind im Quellmaterial beschrieben. Durchschnittssemantik, Zeitfenster und mögliche Auswirkungen auf Handybenachrichtigungen sind teilweise offen.
- Kamerafähigkeit und Zustandsfelder müssen an C20/Robotail geprüft werden. Ein dauerhaftes cameraSwitch-Feld allein ist kein Beweis für vorhandene Kamerahardware.
- Mehr Verlauf als das konfigurierbare Abruflimit benötigt bestätigte Pagination. Ein begrenzter Abruf wird deshalb als begrenzt ausgewiesen; ein vollständiger Langzeitausfall-Backfill wird nicht behauptet.
- Besuche tauchen als `ubpet_visit`/`ubpet_box_event` auf dem Ereignisbus auf. Eine eigene Logbook-Darstellung und erweiterte Geräte-Trigger sind noch nicht ergänzt.
- Der Originalcode und die recherchierten Forks enthalten keine Lizenzdatei. Upstream-Issue #8 fragt eine Freigabe an; es liegt im untersuchten Snapshot keine Antwort vor.

## Markenbezug

[UBPet](https://www.ubpet.com/pages/about-us) und [AIRROBO](https://air-robo.com/pages/about-airrobo) nennen UBTECH als Markeninhaber. Die alte [airrobo-home-Seite](https://www.airrobo-home.com/) verweist auf UBPet. Robotail und Meowant werden hier aufgrund der belegten technischen Profile genannt; eine übergeordnete Markeninhaberschaft wird daraus nicht abgeleitet.
