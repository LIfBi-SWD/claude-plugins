---
name: variable-search
description: Durchsucht die Metadaten des LIfBi (NEPS, ReGES, INSIDE, TAEPS) nach Variablen, Fragetexten und Antwortschemata über variablesearch.lifbi.de. Verwenden, wenn nach LIfBi-/NEPS-Variablen, Variablennamen (z. B. ts23412_v1, t513015), Fragebogenfragen oder Items gesucht wird – auch eingeschränkt nach Projekt, Startkohorte (SC1–SC8), Bildungsetappe, Zielgruppe, Erhebungsjahr, Welle oder Themenbereich. Searches LIfBi/NEPS survey metadata for variables and questions.
---

# LIfBi Variablensuche

Durchsucht die Metadaten der LIfBi-Studien über die öffentliche API von
https://variablesearch.lifbi.de (keine Authentifizierung nötig).

## Werkzeug

Nutze das Skript `scripts/lifbi_search.py` im Verzeichnis dieses Skills (nur Python-Standardbibliothek):

```bash
python <skill-dir>/scripts/lifbi_search.py search  "<Suchtext>" [Filter] [--max N] [--lang de|en] [--json]
python <skill-dir>/scripts/lifbi_search.py facets  "<Suchtext>" [Filter] [--lang de|en] [--all]
```

- `search` liefert die Treffer: Variablenname, Label, Typ, Fragetext und ggf. Item-Text.
- `facets` liefert pro Filterwert die **ID, den Namen und die Trefferzahl** für die aktuelle Suche. So findest du gültige IDs und siehst, wie sich die Treffer verteilen.

### Filter

Alle Filter erwarten **IDs, kommagetrennt**. Mehrere Werte innerhalb eines Filters sind ODER-verknüpft, verschiedene Filter UND-verknüpft.

| Option | Bedeutung | Beispiele für IDs |
|---|---|---|
| `--project` | Studie/Projekt | 1 NEPS, 2 ReGES, 3 INSIDE, 9 TAEPS |
| `--cohort` | Startkohorte | 1–6 = NEPS SC1–SC6, 13 = SC8, 7 = TH, 8 = BW, 9 = ReGES RC1, 12 = RC2 |
| `--stage` | Bildungsetappe | 1 frühkindl. Betreuung, 2 Kindergarten, 3 Grundschule, 4 Sek I, 5 Sek II, 6 Ausbildung, 7 Hochschule, 8 Erwachsenenbildung, 0 ohne |
| `--target` | Befragte Gruppe | 1 Zielperson, 2 Eltern, 3 Erzieher/Lehrkräfte, 8 Einrichtungsleitung, 0 ohne |
| `--year` | Erhebungsjahr | Jahreszahl (2007–2025), 0 = ohne Zuordnung |
| `--wave` | Welle | Wellennummer 0–19 |
| `--concept` | Themenbereich | 10000 Kompetenzen, 10113 Lernumwelten, 10353 Bildungsbez. Ressourcen/Einstellungen, 10595 Demografie & Biografie, 10853 Individuum & Persönlichkeit, 10948 Migration, 10060 Gesellschaft/Familie/Teilhabe, 11167 Methodeninformation, 0 ohne |

Diese Tabelle dient nur der Orientierung. Bei Unsicherheit oder für Werte, die hier fehlen, ermittelst du die aktuellen IDs mit `facets`. Die Wellennummer bezieht sich immer auf eine Kohorte. „Welle 3“ ist deshalb nur zusammen mit `--cohort` sinnvoll interpretierbar.

## Vorgehen

1. Formuliere aus der Anfrage einen **kurzen Suchtext** mit ein bis drei Schlagworten, z. B. „Einkommen“, „Lesekompetenz“ oder „Migrationshintergrund“. Ganze Sätze funktionieren schlecht. Ist ein Variablenname bekannt, suchst du direkt danach.
2. Übersetze Einschränkungen des Nutzers in Filter-IDs, z. B. „NEPS Startkohorte 4, Eltern“ → `--cohort 4 --target 2`.
3. Bei unklarem oder breitem Suchbegriff führst du zuerst `facets` aus. Die Verteilung (welche Kohorten, Themen, Wellen) nennst du dem Nutzer oder grenzt damit selbst sinnvoll ein.
4. Danach `search` ausführen. Wird der Hinweis „Limit erreicht“ angezeigt, weise darauf hin, dass es weitere Treffer gibt. Dann `--max` erhöhen (z. B. 100) oder weiter filtern.
5. Sprache: `--lang de` als Standard. Fragt der Nutzer auf Englisch oder will englische Labels, nimmst du `--lang en` und einen englischen Suchtext.

## Ergebnisdarstellung

- Zeige die Treffer kompakt, am besten als Tabelle mit **Variable**, **Label** und **Frage/Item**.
- Fasse identische Fragetexte zusammen. Häufig gehören mehrere Items zu derselben Frage, z. B. a), b), c).
- Varianten wie `_v1` oder `_R` sind unterschiedliche Variablen. Erwähne sie, statt sie zu verwerfen.
- Erfinde keine Variablen, Wellen oder Kohortenzuordnungen, die die API nicht geliefert hat. Felder wie `cohorts` und `waves` sind in den Treffern meist leer. Kohorten- oder Wellenzugehörigkeit leitest du nur aus den gesetzten Filtern ab.
- Verweise für Details auf https://variablesearch.lifbi.de.

## Direkte API (Referenz)

Alle Endpunkte erwarten `POST` mit JSON-Body und `Content-Type: application/json`.

- `POST /api/Search`: Trefferliste
- `POST /api/Filter?language=de-DE|en`: Facetten Project/Cohort/Stage/TargetGroup/Year mit Trefferzahlen
- `POST /api/Overview?language=de-DE|en`: Matrix Themenbereich × Spalte (Spalten gemäß `AggregateStep`: `Project` oder `Wave`)

Body (alle Endpunkte):

```json
{
  "MaxItems": 25, "SelectedCount": 25,
  "AggregateStep": "Project",
  "DisplayLanguage": "de",
  "SearchText": "Einkommen",
  "ProjectIds": "", "CohortIds": "4,5", "StageIds": "", "TargetGroupIds": "",
  "Years": "", "Waves": "", "ConceptIds": "", "InstrumentIds": "",
  "YearsWaves": null,
  "matrixSelection": "{\"ConceptId\":null,\"AggId\":null}",
  "SearchVariables": ""
}
```

- `MaxItems` und `SelectedCount` müssen immer gleich sein.
- Die Sprache der Labels steuert `DisplayLanguage` im Body (`de`/`en`). Das gilt auch für Filter und Overview.
- `AggregateStep` akzeptiert nur `Project` oder `Wave`. Andere Werte führen zu HTTP 500.
- `matrixSelection`, `SearchVariables` und `YearsWaves` bleiben unverändert wie oben.
