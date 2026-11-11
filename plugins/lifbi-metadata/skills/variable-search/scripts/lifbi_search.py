#!/usr/bin/env python3
"""CLI for the LIfBi variable search API (https://variablesearch.lifbi.de).

Standard library only, so it runs wherever Python 3.8+ is installed.

Subcommands:
  search   Search variables/questions and print a compact hit list.
  facets   Show hit counts per filter value (projects, cohorts, stages,
           target groups, years, concepts, waves) for a query + filters.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

BASE_URL = "https://variablesearch.lifbi.de/api"
TIMEOUT = 60

# CLI option -> request body field
FILTER_FIELDS = {
    "project": "ProjectIds",
    "cohort": "CohortIds",
    "stage": "StageIds",
    "target": "TargetGroupIds",
    "year": "Years",
    "wave": "Waves",
    "concept": "ConceptIds",
    "instrument": "InstrumentIds",
}

# Filter endpoint group name -> CLI option
FACET_OPTION = {
    "Project": "--project",
    "Cohort": "--cohort",
    "Stage": "--stage",
    "TargetGroup": "--target",
    "Year": "--year",
}


def build_body(args, max_items=25):
    body = {
        "MaxItems": max_items,
        "SelectedCount": max_items,  # must always equal MaxItems
        "AggregateStep": args.aggregate,
        "DisplayLanguage": args.lang,
        "SearchText": args.query or "",
        "YearsWaves": None,
        "matrixSelection": json.dumps({"ConceptId": None, "AggId": None}),
        "SearchVariables": "",
    }
    for opt, field in FILTER_FIELDS.items():
        value = getattr(args, opt) or ""
        body[field] = ",".join(v.strip() for v in value.split(",") if v.strip())
    return body


def post(path, body, lang):
    url = f"{BASE_URL}/{path}"
    if path != "Search":
        url += "?language=" + ("de-DE" if lang == "de" else "en")
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", "replace")
            if raw.lstrip().startswith("<"):
                sys.exit("Der Server lieferte HTML statt JSON (Bot-Schutz/Rate-Limit). "
                         "Bitte kurz warten und keine Anfragen in schneller Folge stellen.")
            return json.loads(raw) if raw.strip() else []
    except urllib.error.HTTPError as e:
        sys.exit(f"API-Fehler {e.code} bei {path}: {e.read().decode('utf-8', 'replace')[:500]}")
    except urllib.error.URLError as e:
        sys.exit(f"Verbindungsfehler bei {path}: {e.reason}")


def clean(text):
    return " ".join(str(text).split()) if text else ""


def cmd_search(args):
    hits = post("Search", build_body(args, args.max), args.lang)
    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return
    if not hits:
        print("Keine Treffer.")
        return
    print(f"{len(hits)} Treffer (max. {args.max}):\n")
    for h in hits:
        print(f"- {h.get('variable') or '–'} | {clean(h.get('label'))} [{h.get('type')}, id={h.get('id')}]")
        for q in h.get("question") or []:
            print(f"    Frage: {clean(q)}")
        if h.get("variableQuestion"):
            print(f"    Item:  {clean(h['variableQuestion'])}")
        for key in ("projects", "cohorts", "waves", "years", "instruments", "targets"):
            if h.get(key):
                print(f"    {key}: {clean(json.dumps(h[key], ensure_ascii=False))}")
    if len(hits) >= args.max:
        print(f"\nHinweis: Limit von {args.max} erreicht – es gibt evtl. weitere Treffer "
              f"(--max erhöhen oder mit Filtern eingrenzen; Verteilung via 'facets').")


def cmd_facets(args):
    body = build_body(args)
    groups = post("Filter", body, args.lang)
    # AggregateStep selects the columns of the concept matrix: "Project" for
    # concept totals, "Wave" for the per-wave distribution (a variable can occur
    # in several waves, so wave columns must not be summed into concept totals).
    by_project = post("Overview", dict(body, AggregateStep="Project"), args.lang)
    by_wave = post("Overview", dict(body, AggregateStep="Wave"), args.lang)
    if args.json:
        print(json.dumps({"filters": groups, "overviewByProject": by_project,
                          "overviewByWave": by_wave}, ensure_ascii=False, indent=2))
        return
    for g in groups:
        opt = FACET_OPTION.get(g["filterName"], g["filterName"])
        print(f"{g['filterName']} ({opt}):")
        for f in g["filters"]:
            if args.all or f.get("count"):
                print(f"  {f['id']:>5}  {f['name']}  ({f.get('count', '?')})")
    print("Concept (--concept):")
    for c in by_project.get("concepts", []):
        total = sum(c.get("data") or [])
        if args.all or total:
            print(f"  {c['conceptId']:>5}  {clean(c['conceptName'])}  ({total})")
    print("Wave (--wave):  [Anzahl Variablen-Vorkommen je Welle]")
    waves = by_wave.get("headers", [])
    concepts = by_wave.get("concepts", [])
    for i, w in enumerate(waves):
        total = sum((c.get("data") or [0] * len(waves))[i] for c in concepts)
        if args.all or total:
            print(f"  {w['id']:>5}  Welle {w['name']}  ({total})")


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("query", nargs="?", default="", help="Suchtext (leer = alles)")
    common.add_argument("--lang", choices=["de", "en"], default="de")
    common.add_argument("--aggregate", choices=["Project", "Wave"], default="Project",
                        help="AggregateStep (Standard: Project)")
    common.add_argument("--json", action="store_true", help="Rohes JSON ausgeben")
    for opt in FILTER_FIELDS:
        common.add_argument(f"--{opt}", help="kommagetrennte IDs (ODER-verknüpft)")

    parser = argparse.ArgumentParser(description="LIfBi Variablensuche")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", parents=[common], help="Variablen suchen")
    s.add_argument("--max", type=int, default=25, help="max. Trefferzahl (Standard 25)")
    s.set_defaults(func=cmd_search)
    f = sub.add_parser("facets", parents=[common], help="Trefferverteilung je Filterwert")
    f.add_argument("--all", action="store_true", help="auch Werte mit 0 Treffern zeigen")
    f.set_defaults(func=cmd_facets)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
