# LIfBi Claude Plugins

Claude-Code-Plugin-Marketplace des Leibniz-Instituts für Bildungsverläufe (LIfBi).

Mit diesen Plugins kann [Claude Code](https://claude.com/claude-code) direkt in den Metadaten
der LIfBi-Studien (NEPS, ReGES, INSIDE, TAEPS) suchen – über die API der
[LIfBi-Variablensuche](https://variablesearch.lifbi.de).

## Enthaltene Plugins

| Plugin | Skill | Wofür |
|---|---|---|
| `lifbi-metadata` | `variable-search` | Variablen und Fragen suchen, gefiltert nach Projekt, Kohorte, Bildungsetappe, Zielgruppe, Jahr, Welle, Themenbereich |
| | `item-details` | Details zu einer Variable: Antwortschema, Wellen, Fragetexte, Konzepte, SUF-Dateien, Referenzen |

## Voraussetzungen

- **Claude Code** ist installiert und eingerichtet. [https://code.claude.com/docs/de/quickstart](https://code.claude.com/docs/de/quickstart)
- (Alternativ) **Copilot CLI** [https://github.com/github/copilot-cli](https://github.com/github/copilot-cli)
- (optional, aber empfohlen) **Python 3.8 oder neuer** ist installiert und im Terminal als `python` (oder `python3`) aufrufbar.
  Zusätzliche Pakete werden nicht benötigt.

## Installation

Starte Claude Code (In einem Terminal `claude` eingeben) und gib nacheinander ein:

```
/plugin marketplace add LIfBi-SWD/claude-plugins
/plugin install lifbi-metadata@lifbi
```

Der erste Befehl macht den Marketplace `lifbi` bekannt, der zweite installiert das Plugin daraus.
Alternativ kannst du `/plugin` ohne Argumente eingeben und das Plugin im interaktiven Menü
auswählen.


## Verwendung

### Einfach fragen

Du musst keine Befehle kennen. Stell deine Frage ganz normal – Claude erkennt selbst, wann es
die LIfBi-Skills braucht:

> Welche Variablen zum Haushaltseinkommen gibt es in NEPS Startkohorte 4?

> Gibt es in ReGES Fragen an die Eltern zur Mediennutzung?

> Welche Antwortkategorien hat die Variable ts23412_v1?

> In welchen Wellen und in welchem SUF finde ich t513015?

> Woher stammt die Skala zu Item 104570, was sollte ich zitieren?

> Search NEPS for variables on reading competence in grade 9. *(funktioniert auch auf Englisch)*

Ein typischer Ablauf:

1. Claude sucht passende Variablen und zeigt eine Trefferliste mit **Variablenname**, **Label**,
   **Fragetext** und **Item-ID**.
2. Bei sehr vielen Treffern zeigt Claude, wie sie sich auf Kohorten, Wellen oder Themen
   verteilen, und fragt ggf. nach, worauf eingegrenzt werden soll.
3. Zu einer ausgewählten Variable kannst du nachfragen („Erzähl mir mehr über die zweite“,
   „Welche Werte hat die?“) – Claude ruft dann die Details ab.

### Skills direkt aufrufen

Wenn du einen Skill gezielt starten willst, geht das auch als Slash-Befehl:

```
/lifbi-metadata:variable-search Einkommen in SC6
/lifbi-metadata:variable-search Kann man mit Daten der SC6 den BMI eines Teilnehmers berechnen?
/lifbi-metadata:item-details ts23412_v1
```

### Berechtigungen

Die Skills führen ein kleines Python-Skript aus, das die API abfragt. Claude Code fragt beim
ersten Mal nach, ob es das Skript ausführen darf. Mit „Yes, and don't ask again …“ musst du das
nicht jedes Mal bestätigen.

### Tipps

- **Kurze Suchbegriffe** funktionieren am besten („Lesekompetenz“, „Migrationshintergrund“),
  Claude formuliert sie aber auch selbst aus deiner Frage.
- **Variablennamen** (z. B. `ts23412_v1`) kannst du direkt angeben.
- **Wellen** beziehen sich immer auf eine Kohorte – nenne bei „Welle 3“ am besten auch die Kohorte.
- Für die Arbeit mit den Daten nennt dir `item-details` das passende **SUF-Release, die Datei
  und die DOI**.

## Aktualisieren und Entfernen

```
/plugin marketplace update lifbi          # neue Versionen holen
/plugin uninstall lifbi-metadata@lifbi    # Plugin entfernen
/plugin marketplace remove lifbi          # Marketplace entfernen
```

## Für ein ganzes Projekt/Team einrichten

Damit alle, die ein bestimmtes Projekt-Repository in Claude Code öffnen, das Plugin automatisch
angeboten bekommen, lege dort `.claude/settings.json` an:

```json
{
  "extraKnownMarketplaces": {
    "lifbi": {
      "source": { "source": "github", "repo": "LIfBi-SWD/claude-plugins" }
    }
  },
  "enabledPlugins": {
    "lifbi-metadata@lifbi": true
  }
}
```

## Fehlerbehebung

| Problem | Lösung |
|---|---|
| `marketplace add` schlägt fehl / Repository nicht gefunden | Prüfe, ob du Zugriff auf das Repo hast und Git bei GitHub angemeldet ist (`git ls-remote https://github.com/LIfBi-SWD/claude-plugins.git`). |
| `python` wird nicht gefunden | Python installieren bzw. zum `PATH` hinzufügen. Unter Windows hilft oft `py` statt `python` – Claude passt den Aufruf an, wenn du es darauf hinweist. |
| „Der Server lieferte HTML statt JSON (Bot-Schutz/Rate-Limit)“ | Die Variablensuche drosselt viele Anfragen in kurzer Zeit. Ein paar Minuten warten und dann erneut versuchen. |
| Skills werden nicht verwendet | Claude Code neu starten; unter `/plugin` prüfen, ob `lifbi-metadata` aktiviert ist; ggf. den Skill direkt per Slash-Befehl aufrufen. |

## Für Entwickler:innen

```
.claude-plugin/marketplace.json                 # Marketplace-Katalog
plugins/<plugin>/.claude-plugin/plugin.json     # Plugin-Manifest (Version hier erhöhen!)
plugins/<plugin>/skills/<skill>/SKILL.md        # Skill-Anleitung für Claude
plugins/<plugin>/skills/<skill>/scripts/        # Hilfsskripte (nur Python-Standardbibliothek)
```

Lokal testen, ohne zu pushen:

```
/plugin marketplace add C:\pfad\zu\claude-plugins
/plugin install lifbi-metadata@lifbi
```

Prüfen: `claude plugin validate .`
