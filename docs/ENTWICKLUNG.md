# Aufbau und Erweiterungen

## Datenfluss

`providers.json` ist die einzige Stelle, die Marken und Regionen kennt: Regionen mit Host und Ländern, Zeitzonenregeln für die Vorauswahl sowie jeden Anbieter mit App-Profil, erlaubten Regionen und optionalen Host-/App-Überschreibungen je Region. `providers.py` liest nur diese Daten. `mobile_apps.json` enthält ausschließlich die bereits öffentlich dokumentierten Kennungen der Hersteller-Apps; keine persönlichen Zugangsdaten.

**Neue Marke hinzufügen:** App-Profil in `mobile_apps.json`, Anbieter in `providers.json` (`label`, `app`, `regions`, bei Abweichungen `hosts`/`region_apps`), je ein Eintrag in `strings.json` (nur wenn eine neue Region auftaucht) und ein Test in `.github/tests/test_derived_data.py`. Code muss nicht angefasst werden. Nicht allein anhand ähnlicher Produktnamen einen funktionierenden Login annehmen; belegte App-/Serverdaten sind Voraussetzung.

**Regionsvorauswahl:** Land aus der Home-Assistant-Konfiguration, danach Zeitzone, danach EU. Die Grundlage (`EU · DE`, `NA · America/Chicago`) steht im Formular, damit eine Schätzung als solche erkennbar ist. Es wird bewusst nicht an mehreren Servern probiert: Eine falsche Region liefert dieselbe Antwort wie ein falsches Passwort und würde Fehlversuche anhäufen.

`api.py` enthält den gemeinsamen signierten REST-Client. HTTP-Aufrufe laufen außerhalb der Home-Assistant-Ereignisschleife; je Dashboardabruf sind höchstens vier gleichzeitige Anfragen erlaubt. Die Authentifizierung ist verriegelt. Eine abgelehnte Sitzung wird höchstens einmal erneuert; eindeutige Passwortfehler stoppen weitere automatische Versuche dieses Clients. Optional fehlende Endpunkte haben einen begrenzten Negativcache und löschen vorhandene Messwerte nicht.

`transport.py` verwaltet je Konfigurationseintrag genau eine Paho-Verbindung zum herstellereigenen TLS-Broker. Status und Befehle nutzen dieselbe Sitzung. Brokerbestätigungen sind keine Bestätigung einer ausgeführten Bewegung. Nach einer neuen Verbindung müssen Gerätezustände neu eintreffen, bevor Bewegungsbefehle wieder verfügbar werden.

`coordinator.py` verbindet REST, MQTT und lokalen Verlauf. Pushmeldungen ändern Daten und benachrichtigen Entitäten, ohne den regelmäßigen REST-Termin zu verschieben. Wiederholte Besuchs-/Konfigurationshinweise werden zu einer verzögerten Aktualisierung zusammengefasst. Beim Entladen werden Tasks, Verbindungen und verzögerte Aufrufe beendet.

`history.py` enthält ohne HA-Abhängigkeiten die Deduplizierung, Zeitnormalisierung, begrenzte Historie und Berechnungen. Der Speicher heißt `ubpet_cat_litter_hub.<entry_id>.visit_analytics`; übernommene Einträge lesen beim ersten Start den Speicher `ubpet.<alte_entry_id>.visit_analytics` der alten Integration. Datensätze werden je Gerät und Verlauf unterschieden; numerisch gleiche IDs verschiedener Katzenklos kollidieren nicht.

`entities.py` bündelt die Basisklassen aller Plattformen (`UbpetDeviceEntity`, `UbpetCatEntity` und die Schreibwege für Erinnerung und Zeitfenster), Verfügbarkeit, Entdeckung neuer Geräte und Katzen sowie Hardwarefähigkeiten. `box_config.py` liest reine Konfigurationsdaten (Erinnerung, Wochentage, Zeitfenster) ohne Home-Assistant-Abhängigkeit. Die Entity-Unique-IDs beginnen mit dem `namespace` des Eintrags: der eigenen Entry-ID oder, bei einem übernommenen Eintrag, der ID des alten.

`legacy.py` übernimmt Einträge der alten Domain `ubpet`: Gerät um den neuen Eintrag erweitern, Entitäten verschieben, erst danach den alten Eintrag vom Gerät lösen (Home Assistant löscht sonst die Entitäten mit). Ausgelöst wird das einmalig vom Menü im Konfigurationsablauf; der geleerte alte Eintrag wird nur entfernt, wenn nichts mehr an ihm hängt. Katzen-Gerätekennungen werden pro Konto getrennt. Entfernte Cloudgeräte werden nicht automatisch aus dem HA-Geräteverzeichnis gelöscht.

`compat.py` beschränkt Versionsunterschiede auf wenige Stellen: Coordinator-Argumente, eingefrorene Entity-Beschreibungen, Geräteinformationen und Reauth. Der Funktionsumfang wird nicht durch eine künstlich hohe Core-Mindestversion eingeschränkt.

## Abgeleitete Werte

Alles, was die Hersteller-API nicht selbst liefert, wird in `history.py` aus beobachteten Datensätzen berechnet und dauerhaft gespeichert: Besuche und Reinigungen heute (lokaler Tag der Home-Assistant-Zeitzone), Reinigungen seit Behälterreset, letzte Reinigung, zuletzt benutzende Katze und Gewicht beim letzten Besuch. Reinigungen sind `eventType` 31; das ist laut [bojanrajkovic/upet-hass#6](https://github.com/bojanrajkovic/upet-hass/issues/6) aus dem Zeitverlauf abgeleitet und nicht für jede Firmware bestätigt. Bekannte Ereignisnummern (3, 21, 31) erhalten auf dem Ereignisbus den Namen `event_name`; unbekannte bleiben numerisch.

## Mehrsprachigkeit

Alle sichtbaren Texte stehen in `strings.json` (Englisch, Quelle) und `translations/<sprache>.json`. Zustandswerte sind Schlüssel (`standby`, `inside`, `weekdays` …), keine Texte, und werden über `state` übersetzt. Fehlermeldungen laufen über `exceptions` (`translated_error` in `compat.py`; ältere Core-Versionen fallen auf Englisch zurück). Die Sprache folgt automatisch der Home-Assistant-Benutzersprache; fehlt eine Übersetzung, erscheint Englisch. `python .github/checks/project.py` prüft für jede Sprachdatei gleiche Schlüssel, nicht leere Texte und identische Platzhalter.

## Neue Sensoren

Vor jeder neuen Entität müssen Datenquelle, Einheit, unbekannter Zustand und Gültigkeitsbereich klar sein. Fehlende Felder bedeuten nicht `0` oder `False`. Rollierende Zähler sind `measurement`, weil sie auch ohne Reset sinken können. Ein berechneter Rest bis zur API-Behälterkapazität ist keine zusätzliche physische Füllstandsmessung.

Protokollfelder und ihre Zuordnung stehen in `mqtt.py`. Die vollständigen Zustandsmeldungen verwenden Proto3-Nullwerte für ausgelassene Skalare. RISP-Prüfsummen und Längen werden vor der Auswertung geprüft. Ein später eintreffendes altes Zustandsabbild darf keinen neueren Gerätestand überschreiben.

Unbestätigte Warncodes, Kamerabilder, OTA-Befehle und medizinische Interpretationen werden nicht als gesicherte Sensoren ausgegeben. Bekannte Ansatzpunkte stehen in [QUELLEN.md](QUELLEN.md).

## Tests

Regulär:

```powershell
python -m pip install -r .github/dev/requirements-dev.txt
python -m pytest -c .github/dev/pyproject.toml --rootdir . .github/tests
python .github/checks/project.py
```

Mit echter Core-Installation zusätzlich `.github/ha_tests` an pytest übergeben. Die zentrale Engine erstellt dafür getrennte Umgebungen mit passendem Python und Testplugin. Für normale Tests sind keine Herstellerkonten erforderlich.

Das Brandmotiv liegt als SVG in `assets/cat-litter-hub.svg`. Mit `resvg-py` und `python tools/build_brand.py` werden daraus die vier Integrations-PNGs erzeugt. Die Darstellungsdateien müssen zur Laufzeit nicht neu gerendert werden.
