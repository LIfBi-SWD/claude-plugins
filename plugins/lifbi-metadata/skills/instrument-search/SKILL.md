---
name: instrument-search
description: Sucht Erhebungsinstrumente (Fragebögen, Interviews, Tests, Kompetenztests) der LIfBi-Studien (NEPS, ReGES, INSIDE, TAEPS) über variablesearch.lifbi.de – nach Name, Projekt, Startkohorte, Bildungsetappe, Welle und Jahr. Verwenden, wenn gefragt wird, welche Fragebögen/Instrumente es gibt, z. B. „Welche Instrumente gibt es für SC6 Welle 9?“, „Gibt es einen Elternfragebogen in SC2?“, „Welche Lehrkräftebefragungen gab es in SC8?“, oder wenn eine Instrument-ID gesucht wird. Searches LIfBi/NEPS survey instruments.
---

# LIfBi Instrumentensuche

Findet Erhebungsinstrumente, also Fragebögen, Interviews und Tests, und liefert deren **Instrument-ID**. Mit dieser ID
zeigt der Skill `instrument-details` Aufbau und Inhalt des Instruments.

## Werkzeug

Skript `scripts/lifbi_instrument_search.py` im Verzeichnis dieses Skills (nur Python-Standardbibliothek):

```bash
python <skill-dir>/scripts/lifbi_instrument_search.py "<Suchtext>" [--project IDs] [--cohort IDs] [--stage IDs] [--wave N] [--year JJJJ] [--max N] [--lang de|en] [--json]
```

Der Suchtext ist optional. Mit Filtern allein bekommt man z. B. alle Instrumente einer Kohorte und Welle.

### Filter (kommagetrennt, gleiche IDs wie in `variable-search`)

| Option | Bedeutung | Beispiele |
|---|---|---|
| `--project` | Projekt | 1 NEPS, 2 ReGES, 3 INSIDE, 9 TAEPS |
| `--cohort` | Startkohorte | 1–6 = NEPS SC1–SC6, 13 = SC8, 7 = TH, 8 = BW, 9 = ReGES RC1, 12 = RC2 |
| `--stage` | Bildungsetappe | 1 frühkindl. Betreuung … 8 Erwachsenenbildung |
| `--wave` | Welle | Wellennummer, z. B. 9 |
| `--year` | Erhebungsjahr | z. B. 2016 |

Die aktuellen IDs liefert bei Bedarf `variable-search` mit dem Befehl `facets`.

### Ausgabe

Pro Instrument: `[ID] Name`, dazu Kohorte, Welle, Jahr, Zielgruppe, Anzahl Items und Variablen sowie ggf. eine
Beschreibung. Instrumentnamen folgen meist dem Muster
`<Projekt> <Kohorte>: <Zielgruppe/Teil>, <Erhebung>, Welle <n>, <Modus>`. Der Modus ist z. B. CATI, CAPI, CAWI, PAPI
oder CBT.

## Vorgehen

1. Übersetze die Anfrage in Suchtext und/oder Filter. Der Suchtext durchsucht vor allem den **Instrumentnamen**.
   Kurze Begriffe funktionieren daher am besten, z. B. „Eltern“, „Lehrkräfte“, „Kompetenztest“, „CATI“ oder „SC6“.
   Kohorte und Welle setzt du besser als Filter statt als Text.
2. Gibt es keine Treffer, versuchst du es mit einem kürzeren oder anderen Begriff oder lässt Filter weg.
3. Bei vielen Treffern gruppierst du sie für den Nutzer sinnvoll, z. B. nach Welle oder Zielgruppe. Wird das Limit
   erreicht, weist du darauf hin.
4. Für Aufbau und Inhalt eines Instruments rufst du `instrument-details <ID>` auf. Für die Variablen eines Instruments
   rufst du `variable-search --instrument <ID>` auf.

Erfinde keine Instrumente. Nenne immer die Instrument-ID, damit Nachfragen möglich sind.

## Fehler

„HTML statt JSON“ bedeutet Bot-Schutz oder Rate-Limit. Dann keine weiteren Anfragen in schneller Folge stellen und den
Nutzer informieren.

## Direkte API (Referenz)

`POST https://variablesearch.lifbi.de/api/Instruments/search` mit JSON-Body:

```json
{ "MaxItems": 25, "DisplayLanguage": "de", "SearchText": "Lehrkräfte", "CohortIds": "13", "ProjectIds": "1",
  "StageIds": "", "Waves": "", "Years": "" }
```

**Achtung:** Leere Strings wirken als Filter „passt auf nichts“, die Antwort ist dann `[]`. Nicht gesetzte Felder
lässt man deshalb weg. Die Antwort ist eine Liste von Objekten mit `id`, `name`, `description`, `projects`,
`cohorts`, `waves`, `years`, `targets`, `itemCount` und `variableCount`.
