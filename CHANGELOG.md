# Änderungen

## 2026.11.03.1

- **Neue Domain `ubpet_cat_litter_hub`** (Ordner `custom_components/ubpet_cat_litter_hub`). Einträge der alten Domain `ubpet` lassen sich einmalig über das Menü beim Hinzufügen übernehmen, samt Entity-IDs, Geräten, Besuchsverlauf, Schwellen und Optionen. Vorher Sicherung erstellen und den alten Ordner entfernen.
- Anbieter und Regionen kommen aus `providers.json`; die Vorauswahl nutzt Land, dann Zeitzone und zeigt ihre Grundlage an.
- **Mehrsprachig:** Übersetzungen für 20 Sprachen (de, en, fr, es, it, nl, pl, pt, pt-BR, ru, uk, cs, sv, da, nb, fi, tr, ja, ko, zh-Hans, zh-Hant). Zustandswerte und Fehlermeldungen sind übersetzbar.
- **Achtung, Zustandswerte geändert:** Betriebsstatus ist jetzt `standby`/`running`/`paused`, Katzenposition `inside`/`away`. Automationen, die auf die englischen Texte prüfen, müssen angepasst werden.
- Erinnerung zum Behälterleeren: die Auswahl bietet übersetzte Voreinstellungen (aus, täglich, Werktage, Wochenende); beliebige Kombinationen über sieben Wochentag-Schalter (standardmäßig deaktiviert).
- Neu: Besuche heute, Reinigungen heute, letzte Reinigung, Reinigungen seit Behälterreset, zuletzt benutzt von, geplante Reinigungen; je Katze Besuche heute und Gewicht beim letzten Besuch; Schalter Fremdkörpererkennung.
- Ereignisse `ubpet_box_event` und `ubpet_visit` enthalten `event_name` für bekannte Ereignisnummern.
- Aufgeräumt: gemeinsame Basisklassen statt neunfacher Wiederholung, nicht mehr genutzter Einmal-MQTT-Pfad und verschleierte Standardwerte entfernt, geringere Last bei jeder Push-Meldung.

## 2026.11.02.1

- Mehrere Anbieter und Konten in einer Integration mit expliziter Serverregion und regionaler Vorauswahl.
- Bestehende `ubpet`-Einträge, Entity-Unique-IDs und Besuchsspeicher des Multi-Region-Forks übernehmen.
- Dauerhaftes MQTT je Konto statt wiederholter Neuverbindungen und sekündlicher Statusabfragen.
- Sitzungsübernahmen, Anmeldefehler und Besitzerrechte berücksichtigen; Routinelogs reduzieren.
- Besuchsereignisse, persistente Deduplizierung und zusätzliche faktische Besuchsstatistiken.
- Urin-/Kot-Schätzungen samt vorhandenen Schwellwerten erhalten und eindeutig benennen.
- Zusätzliche Präsenz- und Fehlersensoren, Konfigurationsschalter und Geruchsblockreset.
- Deutsche Einrichtung, deutsche Dokumentation, gemeinsamer Workflow und eigenes Brandmotiv.
- Kompatibilitätsbrücken für ältere Core-Versionen; Mindestversion durch echte Laufzeittests bestimmen.

Hardwarebestätigung für diesen Entwicklungsstand ist noch offen.
