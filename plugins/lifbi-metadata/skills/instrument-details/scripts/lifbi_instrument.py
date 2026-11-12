#!/usr/bin/env python3
"""Show the structure and content of a LIfBi survey instrument (questionnaire).

Standard library only. Uses GET https://variablesearch.lifbi.de/api/Instruments/{id}.
Responses are large (hundreds of KB), so they are cached locally for a day.

Usage:
  python lifbi_instrument.py <id>                      # overview + chapter tree
  python lifbi_instrument.py <id> --chapter <id|name>  # items/variables of one chapter
  python lifbi_instrument.py <id> --find <text>        # items/variables matching text
  python lifbi_instrument.py <id> --items              # all items (long!)
  python lifbi_instrument.py <id> --json               # raw JSON
"""
import argparse
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request

BASE_URL = "https://variablesearch.lifbi.de/api"
TIMEOUT = 90
CACHE_DIR = os.path.join(tempfile.gettempdir(), "lifbi-variablesearch-cache")
CACHE_TTL = 24 * 3600


def parse_json(raw):
    """Parse JSON, unwrapping payloads the server double-encoded as a JSON string."""
    data = json.loads(raw)
    while isinstance(data, str) and data.lstrip()[:1] in ("{", "["):
        data = json.loads(data)
    return data


def fetch_instrument(inst_id, refresh=False):
    cache_file = os.path.join(CACHE_DIR, f"instrument_{inst_id}.json")
    if not refresh and os.path.exists(cache_file) and time.time() - os.path.getmtime(cache_file) < CACHE_TTL:
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)
    req = urllib.request.Request(f"{BASE_URL}/Instruments/{inst_id}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        sys.exit(f"API-Fehler {e.code}: Instrument {inst_id} nicht abrufbar.")
    except urllib.error.URLError as e:
        sys.exit(f"Verbindungsfehler: {e.reason}")
    if not raw.strip():
        sys.exit(f"Instrument {inst_id} nicht gefunden (leere Antwort).")
    if raw.lstrip().startswith("<"):
        sys.exit("Der Server lieferte HTML statt JSON (Bot-Schutz/Rate-Limit oder ungültige ID). "
                 "Bitte kurz warten und keine Anfragen in schneller Folge stellen.")
    data = parse_json(raw)
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError:
        pass  # caching is best effort
    return data


def clean(text):
    return " ".join(str(text).split()) if text else ""


def iter_chapters(chapters, path=()):
    for c in chapters or []:
        p = path + (clean(c.get("name")),)
        yield c, p
        yield from iter_chapters(c.get("chapters"), p)


def count(chapter):
    """(items, variables) of a chapter including its sub-chapters."""
    items = chapter.get("items") or []
    n_items, n_vars = len(items), sum(len(i.get("variables") or []) for i in items)
    for sub in chapter.get("chapters") or []:
        si, sv = count(sub)
        n_items, n_vars = n_items + si, n_vars + sv
    return n_items, n_vars


def print_header(d):
    print(f"Instrument {d.get('id')}: {clean(d.get('name'))}")
    print("=" * 60)
    if d.get("description"):
        print(f"Beschreibung: {clean(d['description'])}")
    for key, label in [("projects", "Projekt"), ("cohorts", "Kohorte"), ("waves", "Welle(n)"),
                       ("years", "Jahr(e)"), ("targets", "Zielgruppe"), ("start", "Beginn"),
                       ("end", "Ende"), ("lastModified", "Zuletzt geändert")]:
        if d.get(key):
            print(f"{label}: {d[key]}")
    print(f"Umfang: {d.get('itemCount')} Items, {d.get('variableCount')} Variablen")


def print_tree(d):
    print("\nKapitelstruktur  [Kapitel-ID] Name (Items/Variablen inkl. Unterkapitel)")
    for c, path in iter_chapters(d.get("chapters")):
        n_items, n_vars = count(c)
        flags = " [Schleife/Episode]" if c.get("episode") else ""
        if c.get("module"):
            flags += f" [Modul: {clean(c['module'])}]"
        print(f"{'  ' * (len(path) - 1)}- [{c.get('id')}] {path[-1] or '(ohne Namen)'} "
              f"({n_items}/{n_vars}){flags}")


def print_item(item, indent="  ", show_filters=True):
    concepts = ", ".join(clean(c.get("name")) for c in item.get("concepts") or [])
    print(f"{indent}• Item {item.get('itemId')}: {clean(item.get('label'))}"
          + (f"  [Konzepte: {concepts}]" if concepts else ""))
    for v in item.get("variables") or []:
        scheme = v.get("scheme") or {}
        extra = ""
        if scheme.get("name"):
            extra = f" | Schema: {clean(scheme['name'])}"
        elif v.get("unit") or v.get("minValue") is not None or v.get("maxValue") is not None:
            extra = f" | Wertebereich: {v.get('minValue')}–{v.get('maxValue')} {v.get('unit') or ''}".rstrip()
        suf = v.get("sufVariable")
        name = v.get("name") + (f" (SUF: {suf})" if suf and suf != v.get("name") else "")
        print(f"{indent}    - {name}: {clean(v.get('label'))}{extra}")
    if show_filters:
        for wf in item.get("conditionalWorkflows") or []:
            if wf.get("condition"):
                print(f"{indent}    ↳ Filter/Steuerung: {clean(wf['condition'])[:200]}")


def find_chapter(d, ref):
    matches = []
    for c, path in iter_chapters(d.get("chapters")):
        if ref.isdigit() and str(c.get("id")) == ref:
            return [(c, path)]
        if not ref.isdigit() and ref.lower() in " > ".join(path).lower():
            matches.append((c, path))
    return matches


def print_chapter(c, path):
    print(f"\n## {' > '.join(p for p in path if p)}  [Kapitel {c.get('id')}]")
    for item in c.get("items") or []:
        print_item(item)
    for sub, sub_path in iter_chapters(c.get("chapters"), path):
        if sub.get("items"):
            print(f"\n### {' > '.join(p for p in sub_path if p)}  [Kapitel {sub.get('id')}]")
            for item in sub["items"]:
                print_item(item)


def cmd_find(d, text):
    t = text.lower()
    chapter_hits = [(c, path) for c, path in iter_chapters(d.get("chapters")) if t in path[-1].lower()]
    if chapter_hits:
        print(f"\nKapitel zu „{text}“ (Inhalt mit --chapter <ID>):")
        for c, path in chapter_hits:
            n_items, n_vars = count(c)
            print(f"  [{c.get('id')}] {' > '.join(p for p in path if p)} ({n_items}/{n_vars})")
    hits = 0
    for c, path in iter_chapters(d.get("chapters")):
        for item in c.get("items") or []:
            haystack = [item.get("label")] + [x for v in item.get("variables") or []
                                              for x in (v.get("name"), v.get("label"), v.get("sufVariable"),
                                                        (v.get("scheme") or {}).get("name"))]
            if any(t in clean(h).lower() for h in haystack if h):
                if hits == 0:
                    print(f"\nTreffer für „{text}“:")
                print(f"\n  [{' > '.join(p for p in path if p)}]")
                print_item(item, indent="    ")
                hits += 1
    if not hits and not chapter_hits:
        print(f"\nKeine Kapitel, Items oder Variablen zu „{text}“ in diesem Instrument.")


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Details zu einem Erhebungsinstrument der LIfBi-Variablensuche")
    p.add_argument("instrument", type=int, help="Instrument-ID (z. B. InstrumentId aus item-details)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--chapter", help="Kapitel-ID oder Teil des Kapitelnamens: Items/Variablen dieses Kapitels")
    g.add_argument("--find", help="Items/Variablen im Instrument nach Text durchsuchen")
    g.add_argument("--items", action="store_true", help="alle Items mit Variablen ausgeben (lang)")
    g.add_argument("--json", action="store_true", help="Rohes JSON ausgeben")
    p.add_argument("--refresh", action="store_true", help="Cache ignorieren und neu laden")
    args = p.parse_args()

    d = fetch_instrument(args.instrument, args.refresh)
    if args.json:
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return

    print_header(d)
    if args.chapter:
        matches = find_chapter(d, args.chapter.strip())
        if not matches:
            print(f"\nKein Kapitel zu „{args.chapter}“ gefunden.")
            print_tree(d)
        elif len(matches) > 1 and not args.chapter.isdigit():
            print(f"\nMehrere Kapitel passen zu „{args.chapter}“ – bitte per ID wählen:")
            for c, path in matches:
                print(f"  [{c.get('id')}] {' > '.join(p for p in path if p)}")
        else:
            print_chapter(*matches[0])
    elif args.find:
        cmd_find(d, args.find)
    elif args.items:
        for c, path in iter_chapters(d.get("chapters")):
            if c.get("items"):
                print(f"\n## {' > '.join(p for p in path if p)}  [Kapitel {c.get('id')}]")
                for item in c["items"]:
                    print_item(item, show_filters=False)
    else:
        print_tree(d)
        print("\nTipp: --chapter <ID> zeigt Items und Variablen eines Kapitels, --find <Text> durchsucht das Instrument.")


if __name__ == "__main__":
    main()
