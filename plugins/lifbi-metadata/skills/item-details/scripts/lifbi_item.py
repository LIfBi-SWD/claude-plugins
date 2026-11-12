#!/usr/bin/env python3
"""Show details for a single item of the LIfBi variable search.

Standard library only. The item id is the "id" field of a search hit
(see the variable-search skill). A variable name (e.g. ts23412_v1) is also
accepted and resolved via the search API.

Usage:
  python lifbi_item.py <id|variable> [--aspect schema,waves,...] [--lang de|en] [--json]
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request

BASE_URL = "https://variablesearch.lifbi.de/api"
TIMEOUT = 60
ASPECTS = ["questions", "schema", "waves", "concepts", "sufs", "references"]

TITLES = {
    "de": {
        "questions": "Fragetexte / Erhebungen",
        "schema": "Antwortschema",
        "waves": "Wellen",
        "concepts": "Konzepte (Themenpfade)",
        "sufs": "Scientific Use Files (SUF)",
        "references": "Referenzen",
        "empty": "(keine Angaben)",
    },
    "en": {
        "questions": "Question texts / surveys",
        "schema": "Response scheme",
        "waves": "Waves",
        "concepts": "Concepts (topic paths)",
        "sufs": "Scientific Use Files (SUF)",
        "references": "References",
        "empty": "(none)",
    },
}


class BlockedError(Exception):
    pass


def request(url, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    # No "Accept: application/json" here: with that header the Items endpoints
    # return the JSON payload double-encoded as a JSON string.
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        sys.exit(f"API-Fehler {e.code}: {url}")
    except urllib.error.URLError as e:
        sys.exit(f"Verbindungsfehler: {e.reason}")
    if not raw.strip():
        return None  # 204 No Content = nothing recorded
    if raw.lstrip().startswith("<"):
        raise BlockedError(
            "Der Server lieferte HTML statt JSON (Bot-Schutz/Rate-Limit oder ungültige ID). "
            "Bitte kurz warten und die ID prüfen; ggf. im Browser auf variablesearch.lifbi.de öffnen.")
    return parse_json(raw)


def parse_json(raw):
    """Parse JSON, unwrapping payloads the server double-encoded as a JSON string."""
    data = json.loads(raw)
    while isinstance(data, str) and data.lstrip()[:1] in ("{", "["):
        data = json.loads(data)
    return data


def resolve_id(ref, lang):
    """Return (item_id, label) for a numeric id or a variable name."""
    if ref.isdigit():
        return int(ref), None
    body = {
        "MaxItems": 50, "SelectedCount": 50, "AggregateStep": "Project",
        "DisplayLanguage": lang, "SearchText": ref,
        "ProjectIds": "", "CohortIds": "", "StageIds": "", "TargetGroupIds": "",
        "Years": "", "Waves": "", "ConceptIds": "", "InstrumentIds": "",
        "YearsWaves": None, "matrixSelection": json.dumps({"ConceptId": None, "AggId": None}),
        "SearchVariables": "",
    }
    hits = request(f"{BASE_URL}/Search", body) or []
    exact = [h for h in hits if (h.get("variable") or "").lower() == ref.lower()]
    if len(exact) == 1:
        return exact[0]["id"], exact[0].get("label")
    if exact:
        lines = "\n".join(f"  id={h['id']}  {h.get('variable')}  {h.get('label')}" for h in exact)
        sys.exit(f"Variablenname '{ref}' ist mehrdeutig, bitte eine ID wählen:\n{lines}")
    sys.exit(f"Keine Variable mit dem Namen '{ref}' gefunden. Bitte zuerst über die Suche die Item-ID ermitteln.")


def clean(text):
    return " ".join(str(text).split()) if text else ""


def unwrap(data):
    return data.get("VariableDetails") if isinstance(data, dict) and "VariableDetails" in data else data


def fmt_questions(rows):
    out = []
    for r in rows:
        q = r.get("QuestionText") or ""
        try:  # QuestionText is a JSON-encoded list of strings
            q = " / ".join(json.loads(q)) if q.startswith("[") else q
        except ValueError:
            pass
        out.append(f"- {r.get('ProjectName')} | {r.get('CohortName')} | Welle {r.get('Wave')} | "
                   f"Modus {r.get('Modus')} | InstrumentId {r.get('InstrumentId')}")
        out.append(f"    Frage: {clean(q)}")
        if r.get("VariableQuestion"):
            out.append(f"    Item:  {clean(r['VariableQuestion'])}")
    return out


def fmt_schema(rows):
    return [f"  {r.get('Value'):>6}  {clean(r.get('Label'))}" for r in rows]


def fmt_waves(rows):
    return [f"- {r.get('ProjectName')} | {r.get('CohortName')} (CohortId {r.get('CohortId')}): "
            f"Welle(n) {', '.join(str(w) for w in r.get('Data') or [])}" for r in rows]


def fmt_concepts(data):
    paths = data.get("ConceptPaths", []) if isinstance(data, dict) else data
    return [f"- {clean(p.get('ConceptPath')).replace('>>', ' > ')}" for p in paths]


def fmt_sufs(rows):
    return [f"- {r.get('Name')} | Datei: {r.get('Datei')} | DOI: {r.get('doi')}" for r in rows]


def fmt_references(rows):
    return [f"- [{r.get('ReferenceTypeName')}, {r.get('ReferenceStateName')}] {clean(r.get('ReferenceText'))}"
            for r in rows]


FORMATTERS = {
    "questions": fmt_questions, "schema": fmt_schema, "waves": fmt_waves,
    "concepts": fmt_concepts, "sufs": fmt_sufs, "references": fmt_references,
}


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Details zu einem Item der LIfBi-Variablensuche")
    p.add_argument("item", help="Item-ID (Feld 'id' eines Suchtreffers) oder Variablenname")
    p.add_argument("--aspect", default=",".join(ASPECTS),
                   help=f"kommagetrennt, Auswahl aus: {', '.join(ASPECTS)} (Standard: alle)")
    p.add_argument("--lang", choices=["de", "en"], default="de")
    p.add_argument("--json", action="store_true", help="Rohes JSON ausgeben")
    args = p.parse_args()

    aspects = [a.strip() for a in args.aspect.split(",") if a.strip()]
    unknown = [a for a in aspects if a not in ASPECTS]
    if unknown:
        p.error(f"unbekannte Aspekte: {', '.join(unknown)}")

    t = TITLES[args.lang]
    try:
        item_id, label = resolve_id(args.item.strip(), args.lang)
        results = {}
        for a in aspects:
            data = request(f"{BASE_URL}/Items/{item_id}/{a}?language={args.lang}")
            results[a] = unwrap(data) if data is not None else None
    except BlockedError as e:
        sys.exit(str(e))

    if args.json:
        print(json.dumps({"id": item_id, **results}, ensure_ascii=False, indent=2))
        return

    header = f"Item {item_id}" + (f" ({args.item}: {label})" if label else "")
    print(header + "\n" + "=" * len(header))
    for a in aspects:
        print(f"\n## {t[a]}")
        data = results[a]
        lines = FORMATTERS[a](data) if data else []
        print("\n".join(lines) if lines else t["empty"])


if __name__ == "__main__":
    main()
