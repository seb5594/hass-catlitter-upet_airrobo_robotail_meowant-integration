# Gerätetest

Softwaretests ersetzen keinen Test an einem echten Katzenklo. Für diese Version liegt noch keine Bestätigung am C20 oder am Gerät des Nachbarn vor. Die genaue Modellbezeichnung des Robotail-Geräts muss noch am Typenschild bzw. in der App geprüft werden; C31 ist bisher eine Vermutung.

## Umstieg am UBPet C20

1. Sicherung erstellen und die alten Entity-IDs bzw. deren Anzahl notieren. Der Screenshot der vorhandenen Installation zeigt 54 Entitäten für zwei Katzen und ein Katzenklo; die tatsächliche Zahl hängt von den Gerätefähigkeiten ab.
2. Den alten Ordner `<config>/custom_components/ubpet` **löschen** und `ubpet_cat_litter_hub.zip` in einen separaten Ordner entpacken. Dessen Inhalt nach `<config>/custom_components/ubpet_cat_litter_hub` übernehmen. Der alte Konfigurationseintrag und `.storage` bleiben unberührt.
3. Home Assistant neu starten. Der alte Eintrag erscheint als nicht ladbar. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen → Cat Litter Hub** den Punkt **Bestehende UPET-Einrichtung übernehmen** wählen. Danach prüfen, ob vorhandene Entity-IDs, Automationen, Katzen, Besuchsverlauf und individuelle Dauerschwellen weiterhin vorhanden sind und der alte Eintrag verschwunden ist. Läuft die alte Integration noch, bricht der Ablauf mit einem Hinweis ab.
4. Kontoanbieter, Serverregion und Kontoland mit der Handy-App abgleichen. Ein deutsches Konto wird typischerweise EU vorschlagen; maßgeblich ist die Kontoregion.
5. Kontrollieren, ob Gewicht, Firmware, Behälterzähler, Geruchsblock und Online-Status zur App passen. Ein API-Füllstand ist nicht automatisch eine physische Füllstandsmessung.
6. Ohne Bewegungsbefehl einen normalen Katzenbesuch abwarten. Präsenz, letzter Besuch, Besuchsdauer und 24-Stunden-Zähler vergleichen. Mehrere Besuche vor einem REST-Abruf dürfen nicht zusammenfallen.
7. Home Assistant neu starten und prüfen, ob die Besuche nicht doppelt erscheinen und Dauerschwellen erhalten bleiben.
8. Bei leerem, normal betriebsbereitem Gerät einen bekannten Reinigungsablauf testen: Start, Pause, Fortsetzen. Während eines Besuchs dürfen keine Startbefehle freigegeben sein. Abdeckung zur Wartung öffnen: Die Präsenzanzeige darf das nicht als Katzenbesuch melden.
9. Reinigungsverzögerung ändern, während automatische Reinigung ausgeschaltet ist: Sie muss ausgeschaltet bleiben. Vorherigen Wert wiederherstellen.
10. Eine normale Handy-App-Anmeldung durchführen. Prüfen, ob die Integration bei einer Sitzungsübernahme zurücktritt und ohne dauernde Loginmeldungen wiederkommt.

Die Urin-/Kotwerte werden nur anhand der Dauer geschätzt. Eine geänderte Schwelle klassifiziert die gespeicherten Besuche neu; sie misst keine andere Ausscheidungsart.

## Neue Werte prüfen

- **Besuche/Reinigungen heute** gegen die Tagesansicht der App vergleichen; „heute“ folgt der Home-Assistant-Zeitzone und springt spätestens beim nächsten REST-Abruf um Mitternacht zurück.
- **Reinigungen seit Behälterreset** nach „Behälter zurücksetzen“ und einer Reinigung prüfen. Wenn der Hersteller-Zähler bei 0 stehen bleibt (bojanrajkovic/upet-hass#9), ist dieser Wert die belastbare Alternative.
- **Zuletzt benutzt von** und **Gewicht beim letzten Besuch** nach einem bekannten Besuch.
- **Geplante Reinigungen** gegen die Zeitpläne in der App.
- **Fremdkörpererkennung** und die Wochentag-Schalter der Leerungserinnerung (standardmäßig deaktiviert) nur an passender Hardware umschalten und den Zustand in der App gegenprüfen.
- Sprache des Benutzerprofils wechseln und prüfen, dass Entitätsnamen, Zustände (Betriebsstatus, Katzenposition) und Fehlermeldungen folgen.

## Zweites Konto / Robotail

Einen weiteren Eintrag mit Anbieter **Robotail** anlegen. Das Konto des Nachbarn wird von ihm selbst eingegeben. Das erste Konto muss weiter funktionieren. Falls in beiden Konten dieselben numerischen Katzen-IDs existieren, dürfen Geräte und Werte nicht vermischt werden. Anschließend dieselben Status- und Besuchstests durchführen.

Rechenbefehle sind bei neuen Installationen standardmäßig deaktiviert. Nur bei passender Hardware aktivieren. Eine gemeinsame App/API beweist nicht, dass ein Modell einen Streurechen besitzt.

## Hilfreiche Rückmeldung

Benötigt werden Modell, Firmware, App-Name, gewählter Anbieter, Serverregion, Kontoland, Home-Assistant-Version und der konkrete Vergleich zwischen App und Entität. Zusätzlich sind die integrierten Diagnosedaten hilfreich. Keine Passwörter, Tokens oder unbearbeiteten Cloudmitschnitte in Issues einstellen.

## Automatisierte Prüfung

Die reguläre Suite liegt in `.github/tests`, die Tests mit echten Home-Assistant-Klassen in `.github/ha_tests`. Die zentrale Compatibility-Pipeline verwendet je Core-Version eine eigene Python- und Testumgebung. Zuletzt liefen 113 Tests unter Core 2026.2.3 (Python 3.13), einschließlich des Anlegens der Entitäten aller sieben Plattformen und der Übernahme alter Einträge mit echten Registries. Die älteren Core-Stände wurden mit diesem Umfang noch nicht erneut geprüft; dafür ist die Compatibility-Pipeline zuständig. Die Übernahme-Tests brauchen das Plugin `pytest-homeassistant-custom-component` und werden ohne es übersprungen. Auch 2023.7.3 wurde geprüft. Die Mindestversion ist 2023.6.0. Beim zusätzlichen Test unter 2023.3.0 fehlte das importierbare Modul `homeassistant.components.time`; dieser Stand wird deshalb nicht als vollständig unterstützt ausgewiesen. Diese Tests verwenden echte Core-Klassen; die gerätebezogene Ende-zu-Ende-Prüfung bleibt separat offen.

```powershell
python -m pytest -c .github/dev/pyproject.toml --rootdir . .github/tests .github/ha_tests
```

Für lokale Core-Tests die jeweilige Home-Assistant-Version samt passender Python-Version und `paho-mqtt==2.1.0` in einer separaten virtuellen Umgebung installieren. Die normale Entwicklersuite benötigt keine Anmeldung und keine echte Hardware.
