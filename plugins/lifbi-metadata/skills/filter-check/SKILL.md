---
name: filter-check
description: Prüft die Filter (conditional workflows – Eingangsfilter, Ausgangsfilter, automatische Wertzuweisungen/autoif, Wertefilter) eines LIfBi-/NEPS-Erhebungsinstruments gegen die LIfBi-Auszeichnungs-Konventionen (markup.st.lifbi.de, „Bedingte Inhalte“) und liefert eine Liste der Items mit fehlerhaften Filtern, dem Filter, einer Fehlerbeschreibung und einem Verbesserungsvorschlag – als Tabelle und CSV. Verwenden, wenn Filter, Bedingungen, Filterführung, autoif oder Wertefilter eines Instruments geprüft, validiert oder korrigiert werden sollen.
---

# LIfBi Filterprüfung

Prüft alle Filter eines Instruments in zwei Stufen:
1. **Automatisch:** Ein Skript prüft Syntax und Kontext regelbasiert und schlägt Korrekturen vor.
2. **Inhaltlich (durch dich):** Du prüfst die Befunde nach, verbesserst die Vorschläge und ergänzt Logikfehler, die
   das Skript nicht erkennt.

Die Regeln stehen in `references/konventionen.md`. Lies die Datei vor der inhaltlichen Prüfung.

## Werkzeug

```bash
python <skill-dir>/scripts/lifbi_filter_check.py <Instrument-ID> --csv filterpruefung_<ID>.csv
python <skill-dir>/scripts/lifbi_filter_check.py <Instrument-ID> --json     # für die eigene Auswertung
python <skill-dir>/scripts/lifbi_filter_check.py --file instrument.json     # lokale Instrument-JSON
```
Optionen: `--no-hints` lässt Hinweise zur Schreibweise weg, `--refresh` umgeht den Cache. Das Instrument wird einen
Tag gecacht, und zwar im selben Cache wie bei `instrument-details`.

Das Skript meldet pro Filter Befunde mit Schwere und Regel-ID:

| Schwere | Bedeutung | Beispiele (Regel) |
|---|---|---|
| **Fehler** | verstößt gegen die Konventionen | fehlendes `if` (IF_FEHLT), fehlende Klammern `if (…)` (KLAMMERFORM), doppeltes `if`, fehlender `:` bei autoif (DOPPELPUNKT), fehlendes Komma oder fehlender Operator (OPERATOR), unausgeglichene Klammern, undokumentierte Funktionen, Konstanten oder Bezeichner (FUNKTION, KONSTANTE, BEZEICHNER, LABELREF, TEXTWERT, ANFUEHRUNG), Schleifenkonstrukte außerhalb von Episoden (SCHLEIFE), Präfix gehört nicht zum Item (PRAEFIX), Freitext im Filterfeld (FREITEXT) |
| **Warnung** | wahrscheinlich ein Fehler, bitte prüfen | Variable fehlt im Instrument (VARIABLE), Variable wird erst später erhoben (REIHENFOLGE), `!= x & y` ist mehrdeutig (NEGLISTE), `== x & y` ist nie wahr (UNERFUELLBAR), Zielvariable gehört nicht zum Item (ZIEL) |
| **Hinweis** | akzeptierte Ersatzschreibweise oder Formatierung | `=` statt `==`, `AND`/`&` statt `and`, `<>` statt `!=`, Leerraum, Filtertyp nicht dokumentiert (TYP) |

## Vorgehen

1. **Instrument-ID klären.** Kennt der Nutzer nur den Namen, suche sie mit dem Skill `instrument-search`.
2. **Skript ausführen** mit `--csv filterpruefung_<ID>.csv` im aktuellen Arbeitsverzeichnis und zusätzlich `--json` für
   deine Auswertung.
3. **Inhaltlich prüfen.** Lies `references/konventionen.md` und gehe die Befunde durch:
   - **Vorschläge prüfen und verbessern.** Die automatischen Vorschläge sind mechanisch erzeugt. Bei undokumentierten
     Konstrukten wie `count()`, `list()`, `var(Label)`, Textwerten oder `inty` gibt es keine automatische Lösung.
     Beschreibe dann, wie es konventionskonform ginge, z. B. `inty` → `$YEAR$`. Ist das nicht möglich, empfiehl die
     Abstimmung mit der Surveytechnologie.
   - **Ergänzen, was das Skript nicht erkennt:**
     - Überschneidungen zwischen mehreren Bedingungen oder `autoif`-Zeilen desselben Feldes oder derselben Zielvariable
       (Regel „überschneidungsfrei“, die erste zutreffende Bedingung gewinnt).
     - Lücken, d. h. Fälle, die keine Zeile abdeckt, obwohl das offensichtlich gemeint ist.
     - Mischung von `and` und `or` ohne Klammern (Vorrang nicht definiert).
     - Bedingungen, die immer wahr oder nie wahr sind.
     - Filter, die vermutlich anders gemeint sind, als sie geschrieben sind.
     - Unplausible Codes: Bei Bedarf rufst du das Antwortschema einer referenzierten Variable mit `item-details
       <Variablenname> --aspect schema` ab. Das gilt nur für einzelne, konkrete Verdachtsfälle, keine Massenabfragen.
   - **Befunde, die sich als falsch erweisen,** nimmst du aus der Liste und erwähnst sie kurz.
4. **Ergebnis ausgeben** (siehe unten). Nenne den Pfad der CSV-Datei. Hast du inhaltliche Befunde ergänzt, schreibst
   du die CSV mit deinen Ergänzungen neu: UTF-8 mit BOM, Semikolon als Trennzeichen, gleiche Spalten.

## Ergebnisformat

Kurze Zusammenfassung, z. B. „46 Filter geprüft, 44 fehlerhaft, häufigste Ursache: fehlende Klammern `if (…)`“.
Danach eine Tabelle, sortiert nach Schwere und dann in der Reihenfolge im Instrument:

| Item | Filter | Fehlerbeschreibung | Verbesserungsvorschlag |
|---|---|---|---|
| 87012 – Kurzlabel (Variablen) | `if e400000 = 1` | Bedingung nicht in Klammern; `=` statt `==` | `if (e400000 == 1)` |

- Wiederholt sich derselbe Fehler bei vielen Items, kannst du ihn zusätzlich zusammengefasst erklären. Jedes
  betroffene Item muss trotzdem in der Tabelle stehen.
- Reine Schreibweise-Hinweise listest du **getrennt** nach den Fehlern, kompakt.
- Kennzeichne, welche Befunde vom Skript stammen und welche aus deiner inhaltlichen Prüfung.
- Schreibe Filter und Vorschläge immer in Backticks und wörtlich, mehrzeilige Filter mit `<br>`.

## Fehler

„HTML statt JSON“ bedeutet Bot-Schutz oder Rate-Limit. Dann keine weiteren Anfragen in schneller Folge stellen und den
Nutzer informieren.
