---
name: item-details
description: Liefert Details zu einer einzelnen LIfBi-/NEPS-Variable (Item) aus variablesearch.lifbi.de – Antwortschema/Wertelabels, Wellen und Kohorten, Fragetexte mit Erhebungsmodus und Instrument, Konzept-/Themenpfade, Scientific Use Files (SUF-Datei, DOI) und Literaturreferenzen. Verwenden, wenn zu einer bestimmten Variable (Item-ID oder Variablenname wie ts23412_v1) nachgefragt wird, z. B. „Welche Antwortkategorien hat …?“, „In welchen Wellen wurde … erhoben?“, „In welchem SUF/Datensatz finde ich …?“, „Woher stammt die Skala?“. Shows details for a single LIfBi/NEPS variable.
---

# LIfBi Item-Details

Zeigt Detailinformationen zu **einem** Item bzw. **einer** SUF-Variable der LIfBi-Variablensuche. Das Item wird über seine
**Item-ID** angesprochen. Das ist das Feld `id` eines Treffers aus der Suche (Skill `variable-search`),
**nicht** der Variablenname.

## Werkzeug

Skript `scripts/lifbi_item.py` im Verzeichnis dieses Skills (nur Python-Standardbibliothek):

```bash
python <skill-dir>/scripts/lifbi_item.py <Item-ID|Variablenname> [--aspect a,b,...] [--lang de|en] [--json]
```

Statt einer ID kann auch ein **Variablenname** übergeben werden, z. B. `ts23412_v1`. Das Skript ermittelt
die ID dann über die Suche. Ist der Name mehrdeutig, listet es die Kandidaten auf.

### Aspekte (`--aspect`, Standard: alle)

| Aspekt | Inhalt | Typische Frage |
|---|---|---|
| `questions` | Fragetext, Item-Text, Projekt, Kohorte, Welle, Erhebungsmodus (CATI, CAPI, Online, PAPI …), `InstrumentId` | „Wie lautet die Frage genau?“, „Wie wurde erhoben?“ |
| `schema` | Antwortkategorien (Wert → Label) | „Welche Antwortoptionen gibt es?“, „Wie ist die Variable codiert?“ |
| `waves` | Projekt, Kohorte und Wellen, in denen das Item vorkommt | „In welchen Wellen gibt es das?“ |
| `concepts` | Themenpfade in der Konzepthierarchie | „Zu welchem Konstrukt/Thema gehört das?“ |
| `sufs` | Scientific Use Files: Release, Datei (z. B. `spEmp`, `pEducator`), DOI | „In welchem Datensatz/welcher Datei finde ich die Variable?“ |
| `references` | Literatur-/Quellenangaben (bibtex-Key, DOI), Typ (z. B. Adaption) | „Woher stammt die Skala?“, „Was soll ich zitieren?“ |

Frag nur die Aspekte ab, die zur Frage passen, z. B. `--aspect schema`. Wenn der Nutzer allgemein
„Erzähl mir mehr über …“ fragt, ruf alle Aspekte ab. Ein leerer Aspekt wird als „keine Angaben“
angezeigt. Das ist normal, besonders bei `references`.

## Vorgehen

1. Item-ID ermitteln:
   - Steht sie aus einer vorherigen Suche schon im Gespräch, nimm sie direkt.
   - Ist nur ein Variablenname bekannt, übergib ihn direkt an das Skript.
   - Ist nur ein Thema bekannt, suche zuerst mit dem Skill `variable-search` und lass bei mehreren
     Treffern den Nutzer wählen.
2. Skript mit den passenden Aspekten ausführen. Sprache: `--lang de` als Standard, `en` bei englischen Anfragen.
3. Antwort zusammenfassen:
   - Antwortschema als kompakte Tabelle Wert | Label.
   - Wellen als „SC6: Welle 1, 3, 5“.
   - Für SUFs Release, Dateiname und DOI nennen. Mit Release und Datei finden Nutzer die Variable im Datensatz.
   - Bei Referenzen die DOI als Link `https://doi.org/<doi>` ausgeben.
4. Die `InstrumentId` aus `questions` kann in der Suche als Filter dienen
   (`variable-search` → `--instrument <id>`). So findet man weitere Items desselben Fragebogens.

Erfinde keine Details, die die API nicht liefert. Fehlt etwas, sag das und verweise auf
https://variablesearch.lifbi.de.

## Fehler

Meldet das Skript „HTML statt JSON“, hat der Server Bot-Schutz oder Rate-Limit aktiviert, oder die ID
ist ungültig. Stelle dann keine weiteren Anfragen in schneller Folge, sondern nenne dem Nutzer das
Problem.

## Direkte API (Referenz)

`GET https://variablesearch.lifbi.de/api/Items/{id}/{aspect}?language=de|en`, wobei `{aspect}` einer
der Werte `schema`, `waves`, `sufs`, `concepts`, `questions` oder `references` ist. Die meisten Antworten
liegen in `{"VariableDetails": …}`. `sufs` liefert direkt eine Liste. Ohne Daten antwortet der Server mit
HTTP 204 und leerem Body.
