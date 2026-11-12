# Auszeichnungs-Konventionen: Bedingte Inhalte (Kurzfassung)

Quelle: https://markup.st.lifbi.de/#bedingte-inhalte („Auszeichnungs-Konventionen für Bildschirmbefragungen“,
LIfBi Surveytechnologie). Bei Zweifeln oder neuerem Stand gilt die Webseite.

## Filtertypen (`filterType` der API)

| Typ | Bedeutung | Format |
|---|---|---|
| 1 | Eingangsfilter | `if (Bedingung)` bzw. `variable: if (Bedingung);` |
| 2 | Ausgangsfilter | wie Eingangsfilter |
| 3 | Automatische Wertzuweisung | `autoif (Bedingung): variable = Wert` |
| 4 | Wertefilter | `if (Bedingung): variable: Werteliste;` bzw. `… : variable: !(Werteliste);` |
| andere | nicht dokumentiert | nur allgemeine Prüfungen |

## Bedingungen

- Beginnen mit `if`, danach **ein** Leerzeichen. Die ganze Bedingung steht in **einem** Klammerpaar: `if (Bedingung)`.
- Zusätzliche Klammern zur Strukturierung sind erlaubt.
- Bedingungen in einem Feld müssen **überschneidungsfrei** sein. Sie werden wie eine verschachtelte Wenn-dann-Kette
  ausgewertet, und die erste zutreffende Bedingung gewinnt.
- Einschränkung auf einzelne Variablen eines Items erfolgt mit dem Präfix `variablenname: if (Bedingung)`. Mehrere
  solche Einschränkungen werden mit `;` getrennt, jede steht in einer eigenen Zeile.

Beispiele (korrekt):
```
if (t731168 == 7)
t731168: if (t731161 != 14)
t261621: if (t731168 == 7);
t261622: if (t731168 == 3);
```

## Operatoren und Funktionen

| Art | Bevorzugt | Akzeptierte Ersatzform (→ Hinweis) |
|---|---|---|
| Logisches UND | `and` | `&`, `AND` |
| Logisches ODER | `or` | `|`, `OR` |
| Gleich | `==` | `=` (in Bedingungen) |
| Ungleich | `!=` | `<>` |
| Vergleich | `>`, `>=`, `<`, `<=` | |
| Rechnen | `+ - * /`, `mod(a,b)` | `a MOD b` |

Kurzformen für Wertelisten:
- `x,y,…` bedeutet „einer der Werte“, also `== x or == y`.
- `x & y & …` bedeutet „alle Werte“, also `== x and == y`. Für **eine** Variable ist das nie wahr.
- `x to y` steht für das geschlossene Intervall, also `>= x and <= y`.
- Mit `!=` sind die Kurzformen **nicht definiert** und damit mehrdeutig. Dann explizit schreiben: `v != 9 and v != 14`.

Nicht dokumentiert, also **Fehler**: andere Funktionen wie `count()` oder `list()`, Label-Referenzen `var(Label)` in
Filtern, Textwerte in Anführungszeichen (besonders typografische „…“), unbekannte Konstanten und Bezeichner wie `inty`.

## Wertzuweisung (Feld „Autofüllen“)

```
autoif (t731161 != 14): t731168 = 5
```
- `=` ist hier die Zuweisung. In der Bedingung gilt `==`.
- Selten einsetzen. **Preload-Variablen** (Bezeichnung `[AUTO]`) dürfen zur Laufzeit nicht verändert werden.
- Mehrere `autoif`-Zeilen für dieselbe Zielvariable müssen überschneidungsfrei sein.

## Wertefilter (Feld „Wertefilter“)

```
if (td00410 == 9): t31035f: 4, 2, 3;
if (td00410 != 9): t31035f: 1 to 3;
if ($MODE$ == CAWI) : $ALL$: !(-98);
```
- Mit einer Positivliste werden die genannten Werte angezeigt, mit `!(…)` die genannten ausgeblendet.
- `$ALL$` gilt für alle Variablen des Items. Ohne `$ALL$` muss ein Filter für jede Variable wiederholt werden.

## Konstanten und Schleifen

- Dokumentierte Konstanten: `$FIRSTNAME$`, `$LASTNAME$`, `$MODE$` (Werte z. B. CAWI, CATI, CAPI, PAPI), `$DAY$`,
  `$MONTH$`, `$YEAR$` und `$NULL$` (leer/System-Missing).
- Nur in Kapiteln, die als Episode/Schleife markiert sind: `$LOOPCOUNTER$`, `$LOOPCOUNTER_#$`, `variable.index#`,
  `variable.lag#`.

## Bedingte Inhalte in Texten (nicht Teil der Filterfelder)

`{if (Bedingung): Inhalt}` in Prolog-, Epilog-, Frage- und Hinweistexten.
