# Workflow und Versionen

Dieses Projekt verwendet die vorhandene private Engine `seb5594/hass-workflows`, fest gepinnt auf Commit `23ecff0b6b887eb3e1eda6d0c0632490965b61d2`.

- `.github/workflows/ci.yml` ist der unveränderte, generierte Integration-Caller.
- `.github/workflows/compat.yml` ist der dazugehörige Compatibility-Caller.
- `ORCHESTRATION_PAT` dient dem Checkout der privaten Engine und der Katalogbenachrichtigung. Der Wert wird weder ausgelesen noch in dieses Repository übernommen.
- Normale Prüfungen und Packaging verwenden die Regeln der Engine. Tests liegen in `.github/tests` und `.github/ha_tests`; zusätzliche Metadaten-, Sprach- und Ruff-Prüfungen in `.github/checks`.
- Pull Requests aus fremden Forks erhalten den privaten Token nicht. Der Zugriffsschutz entspricht der gemeinsamen Engine-Vorlage.
- Auf `main` bzw. einem passenden Versionstag kann die Engine nach bestandenen Prüfungen ein Release veröffentlichen und den Integrationskatalog benachrichtigen. Ein PR veröffentlicht noch kein Release. Die Core-Kompatibilitätsmatrix ist ein eigener Workflow und sollte vor dem Merge ebenfalls grün sein.

Die zentrale Engine misst Tests und ZIP-Größe und aktualisiert den generierten README-Kopf. Freie deutsche Anleitungstexte unterhalb dieses Kopfes bleiben beim Aktualisieren erhalten. Andere Projekte oder der private Engine-Code werden durch diese Einrichtung nicht geändert.

## Schema

`2026.11.02.1` bedeutet: erster Build am 2. November 2026. Danach folgen `.2`, `.3` usw. Am nächsten Kalendertag beginnt die Tageszählung wieder bei `.1`. Maßgeblich ist **Europe/Berlin**. Der Release-Tag lautet beispielsweise `v2026.11.02.1`.

Die Versionsquelle ist `custom_components/ubpet/manifest.json`. Das Schema wird als gültiges Calendar Versioning erkannt und von der vorhandenen ZIP-/Release-Engine unterstützt.

```powershell
# Select the next available day build from the manifest and local Git tags:
python tools/version.py

# Prepare a specific build:
python tools/version.py --date 2026-11-02 --build 2
```

Vor einem Tagesbuild `git fetch --tags origin` ausführen, damit bereits veröffentlichte Tags berücksichtigt werden. Das Skript verändert nur das Manifest; Eintrag im Changelog und Gerätetest passend zum tatsächlichen Änderungsumfang ergänzen. Danach unter der vorhandenen Git-Identität committen.

## Lokal dieselben Engine-Regeln verwenden

```powershell
python .engine/.scripts/managed.py check integration
python .engine/.scripts/project.py validate
python .engine/.scripts/project.py package
```

Die Engine wird vorher außerhalb des veröffentlichten Komponentenordners ausgecheckt. `dist/ubpet.zip` enthält ausschließlich den Inhalt von `custom_components/ubpet`, ohne `.research`, Tests, Zugangsdaten aus Home Assistant oder virtuelle Umgebungen. Die Engine setzt feste ZIP-Zeitstempel und prüft das Archiv vor der Ausgabe einer SHA-256-Prüfsumme.

Der offene Upstream-Lizenzstatus wird dokumentiert; die Engine überspringt den für den HACS-Standardkatalog vorgesehenen Lizenztest, solange keine Lizenzdatei vorhanden ist. Es wird keine fremde Lizenz fingiert.
