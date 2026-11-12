---
name: instrument-details
description: Zeigt Aufbau und Inhalt eines LIfBi-/NEPS-Erhebungsinstruments (Fragebogen, Test, Interview) aus variablesearch.lifbi.de – Projekt, Kohorte, Welle, Jahr, Zielgruppe, Kapitelstruktur, Items, Variablen mit Antwortschemata und Filterführung. Verwenden, wenn zu einem bestimmten Instrument (Instrument-ID, z. B. aus item-details oder der Instrumentensuche) gefragt wird, z. B. „Wie ist der Lehrkräftefragebogen SC8 Welle 1 aufgebaut?“, „Welche Fragen enthält das Kapitel …?“, „Welche Variablen gibt es in diesem Fragebogen zu …?“. Shows structure and content of a LIfBi/NEPS survey instrument.
---

# LIfBi Instrument-Details

Zeigt Informationen zu **einem** Erhebungsinstrument (Fragebogen/Interview/Test) der LIfBi-Studien.
Das Instrument wird über seine **Instrument-ID** angesprochen. Sie stammt aus:
- `item-details --aspect questions`: Feld `InstrumentId`,
- der Instrumentensuche (Skill `instrument-search`).

## Werkzeug

Skript `scripts/lifbi_instrument.py` im Verzeichnis dieses Skills (nur Python-Standardbibliothek):

```bash
python <skill-dir>/scripts/lifbi_instrument.py <Instrument-ID>                   # Übersicht + Kapitelbaum
python <skill-dir>/scripts/lifbi_instrument.py <Instrument-ID> --chapter <ID|Name>  # Items/Variablen eines Kapitels
python <skill-dir>/scripts/lifbi_instrument.py <Instrument-ID> --find <Text>        # Kapitel/Items/Variablen nach Text
python <skill-dir>/scripts/lifbi_instrument.py <Instrument-ID> --items              # alles (sehr lang!)
```

- Die **Übersicht** zeigt Metadaten wie Projekt, Kohorte, Welle, Jahr, Zielgruppe und Umfang. Dazu kommt der Kapitelbaum
  mit Kapitel-IDs und der Anzahl Items/Variablen je Kapitel. `[Schleife/Episode]` markiert Kapitel, die wiederholt
  durchlaufen werden, z. B. pro Fach oder Episode.
- `--chapter` listet die Items eines Kapitels mit Variablennamen, Labels, Antwortschema, zugeordneten Konzepten und
  Filterbedingungen (`↳ Filter/Steuerung`). Passt ein Name zu mehreren Kapiteln, werden die IDs zur Auswahl angezeigt.
- `--find` sucht in Kapitelnamen, Item-Labels, Variablennamen, Variablenlabels und Schemanamen.
- Antworten werden einen Tag lang lokal gecacht, weil Instrumente mehrere hundert KB groß sind. `--refresh`
  erzwingt ein Neuladen.

## Vorgehen

1. **Immer zuerst die Übersicht abrufen.** Gib nie ungefragt `--items` aus, denn ein Instrument hat oft Hunderte Variablen.
2. Erkläre den Aufbau knapp: Für wen ist das Instrument, wann wurde erhoben, welche Hauptteile hat es? Kürzel wie LK-A
   oder SL stehen meist für Teilinstrumente bzw. Befragtengruppen, z. B. Lehrkraft allgemein und Schulleitung.
3. Für inhaltliche Fragen gezielt `--find <Begriff>` oder `--chapter <ID>` verwenden.
4. **Weiter zu einer Variable:** Für Details wie Wertelabels, SUF-Datei, Wellen oder Referenzen rufst du den Skill
   `item-details` mit dem **Variablennamen** auf, z. B. `e22245a`. Die `Item`-Nummern in diesem Skill sind
   *Instrument-Item-IDs* und **nicht** die IDs, die `item-details` erwartet.
5. **Weitere Variablen aus demselben Instrument** findest du mit `variable-search --instrument <Instrument-ID>`.

Filterbedingungen (`if ed00502 = 1` …) beschreiben, wer eine Frage gestellt bekommt. Gib sie wörtlich wieder und
interpretiere Variablen darin nur, wenn du ihre Bedeutung im Instrument nachgeschlagen hast.

## Fehler

„HTML statt JSON“ bedeutet Bot-Schutz oder Rate-Limit. Dann keine weiteren Anfragen in schneller Folge stellen und den
Nutzer informieren. Bei HTTP 404 oder einer leeren Antwort ist die Instrument-ID ungültig.

## Direkte API (Referenz)

`GET https://variablesearch.lifbi.de/api/Instruments/{id}` liefert ein Objekt mit `id`, `name`, `description`,
`projects`, `cohorts`, `waves`, `years`, `targets`, `itemCount`, `variableCount` und `chapters`. Kapitel sind rekursiv
verschachtelt (`chapters`) und enthalten `items`. Jedes Item hat `itemId`, `label`, `concepts`, `conditionalWorkflows`
und `variables`. Jede Variable hat `name`, `label`, `sufVariable`, `instrumentVariable` und `scheme` mit `name`,
`category` und `optionCount`.
