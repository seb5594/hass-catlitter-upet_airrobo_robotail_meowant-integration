# Aufbau und Erweiterungen

## Datenfluss

`providers.py` trennt Anbieter, App-Kennung und Serverregion. `mobile_apps.json` enthält ausschließlich die bereits öffentlich dokumentierten Kennungen der Hersteller-Apps; keine persönlichen Zugangsdaten. Ein neuer Anbieter benötigt ein eigenes Profil und belegte App-/Serverdaten. Nicht allein anhand ähnlicher Produktnamen einen funktionierenden Login annehmen.

`api.py` enthält den gemeinsamen signierten REST-Client. HTTP-Aufrufe laufen außerhalb der Home-Assistant-Ereignisschleife; je Dashboardabruf sind höchstens vier gleichzeitige Anfragen erlaubt. Die Authentifizierung ist verriegelt. Eine abgelehnte Sitzung wird höchstens einmal erneuert; eindeutige Passwortfehler stoppen weitere automatische Versuche dieses Clients. Optional fehlende Endpunkte haben einen begrenzten Negativcache und löschen vorhandene Messwerte nicht.

`transport.py` verwaltet je Konfigurationseintrag genau eine Paho-Verbindung zum herstellereigenen TLS-Broker. Status und Befehle nutzen dieselbe Sitzung. Brokerbestätigungen sind keine Bestätigung einer ausgeführten Bewegung. Nach einer neuen Verbindung müssen Gerätezustände neu eintreffen, bevor Bewegungsbefehle wieder verfügbar werden.

`coordinator.py` verbindet REST, MQTT und lokalen Verlauf. Pushmeldungen ändern Daten und benachrichtigen Entitäten, ohne den regelmäßigen REST-Termin zu verschieben. Wiederholte Besuchs-/Konfigurationshinweise werden zu einer verzögerten Aktualisierung zusammengefasst. Beim Entladen werden Tasks, Verbindungen und verzögerte Aufrufe beendet.

`history.py` enthält ohne HA-Abhängigkeiten die Deduplizierung, Zeitnormalisierung, begrenzte Historie und Berechnungen. Der Speicher heißt weiterhin `ubpet.<entry_id>.visit_analytics`, damit bestehende PnnnG-Daten nicht verloren gehen. Datensätze werden je Gerät und Verlauf unterschieden; numerisch gleiche IDs verschiedener Katzenklos kollidieren nicht.

`entities.py` bündelt Verfügbarkeit, neue Geräte und Katzen, Hardwarefähigkeiten und Gerätekennungen. Die Entity-Unique-IDs enthalten weiterhin die bestehende Entry-ID. Katzen-Gerätekennungen werden pro Konto getrennt. Entfernte Cloudgeräte werden nicht automatisch aus dem HA-Geräteverzeichnis gelöscht.

`compat.py` beschränkt Versionsunterschiede auf wenige Stellen: Coordinator-Argumente, eingefrorene Entity-Beschreibungen, Geräteinformationen und Reauth. Der Funktionsumfang wird nicht durch eine künstlich hohe Core-Mindestversion eingeschränkt.

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
