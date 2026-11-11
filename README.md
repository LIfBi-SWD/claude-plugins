# LIfBi Claude Plugins

Claude-Code-Plugin-Marketplace des Leibniz-Instituts für Bildungsverläufe (LIfBi).

## Installation

In Claude Code:

```
/plugin marketplace add LIfBi-SWD/claude-plugins
/plugin install lifbi-metadata@lifbi
```

## Enthaltene Plugins

| Plugin | Skills | Beschreibung |
|---|---|---|
| `lifbi-metadata` | `variable-search` | Suche nach Variablen und Fragen über variablesearch.lifbi.de |
| | `item-details` | Details zu einem Item: Antwortschema, Wellen, Fragetexte, Konzepte, SUF-Dateien, Referenzen |

## Struktur

```
.claude-plugin/marketplace.json      # Marketplace-Katalog
plugins/<plugin>/.claude-plugin/plugin.json
plugins/<plugin>/skills/<skill>/SKILL.md
```
