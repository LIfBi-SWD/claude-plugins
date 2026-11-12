#!/usr/bin/env python3
"""Search survey instruments (questionnaires, tests, interviews) of the LIfBi variable search.

Standard library only. Uses POST https://variablesearch.lifbi.de/api/Instruments/search.
Note: the API treats an empty string as "match nothing", so only set fields are sent.

Usage:
  python lifbi_instrument_search.py "<text>" [--project 1] [--cohort 6] [--stage 8]
                                             [--wave 9] [--year 2016] [--max 25] [--lang de|en] [--json]
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

URL = "https://variablesearch.lifbi.de/api/Instruments/search"
TIMEOUT = 60

FILTER_FIELDS = {
    "project": "ProjectIds",
    "cohort": "CohortIds",
    "stage": "StageIds",
    "wave": "Waves",
    "year": "Years",
}


def parse_json(raw):
    data = json.loads(raw)
    while isinstance(data, str) and data.lstrip()[:1] in ("{", "["):
        data = json.loads(data)
    return data


def build_body(args):
    body = {"MaxItems": args.max, "DisplayLanguage": args.lang}
    if args.query and args.query.strip():
        body["SearchText"] = args.query.strip()
    for opt, field in FILTER_FIELDS.items():
        value = ",".join(v.strip() for v in (getattr(args, opt) or "").split(",") if v.strip())
        if value:  # never send empty strings – the API would return no hits
            body[field] = value
    return body


def search(body):
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        sys.exit(f"API-Fehler {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    except urllib.error.URLError as e:
        sys.exit(f"Verbindungsfehler: {e.reason}")
    if raw.lstrip().startswith("<"):
        sys.exit("Der Server lieferte HTML statt JSON (Bot-Schutz/Rate-Limit). "
                 "Bitte kurz warten und keine Anfragen in schneller Folge stellen.")
    return parse_json(raw) if raw.strip() else []


def clean(text):
    return " ".join(str(text).split()) if text else ""


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Instrumentensuche der LIfBi-Variablensuche")
    p.add_argument("query", nargs="?", default="", help="Suchtext (durchsucht v. a. den Instrumentnamen)")
    for opt in FILTER_FIELDS:
        p.add_argument(f"--{opt}", help="kommagetrennte IDs bzw. Werte")
    p.add_argument("--max", type=int, default=25, help="max. Trefferzahl (Standard 25)")
    p.add_argument("--lang", choices=["de", "en"], default="de")
    p.add_argument("--json", action="store_true", help="Rohes JSON ausgeben")
    args = p.parse_args()

    body = build_body(args)
    hits = search(body)
    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return
    if not hits:
        print("Keine Instrumente gefunden. Tipp: kürzere/andere Suchbegriffe (z. B. 'SC6', 'Eltern', 'Welle 9') "
              "oder weniger Filter.")
        return
    print(f"{len(hits)} Instrument(e) (max. {args.max}):\n")
    for h in hits:
        print(f"- [{h.get('id')}] {clean(h.get('name'))}")
        meta = [f"{label}: {clean(h.get(key))}" for key, label in
                [("cohorts", "Kohorte"), ("waves", "Welle"), ("years", "Jahr"), ("targets", "Zielgruppe")]
                if h.get(key)]
        meta.append(f"{h.get('itemCount')} Items / {h.get('variableCount')} Variablen")
        print("    " + " | ".join(meta))
        if h.get("description"):
            print(f"    {clean(h['description'])}")
    if len(hits) >= args.max:
        print(f"\nHinweis: Limit von {args.max} erreicht – es gibt evtl. weitere Instrumente "
              f"(--max erhöhen oder mit Filtern/Suchtext eingrenzen).")


if __name__ == "__main__":
    main()
