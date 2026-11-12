#!/usr/bin/env python3
"""Check the filters (conditional workflows) of a LIfBi instrument against the
markup conventions (https://markup.st.lifbi.de/#bedingte-inhalte).

Standard library only. Loads GET https://variablesearch.lifbi.de/api/Instruments/{id}
(cached for a day, shared cache with instrument-details) or a local JSON file.

Usage:
  python lifbi_filter_check.py <instrument-id> [--csv out.csv] [--json] [--no-hints] [--refresh]
  python lifbi_filter_check.py --file instrument.json [...]

filterType: 1 Eingangsfilter, 2 Ausgangsfilter, 3 Automatische Wertzuweisung, 4 Wertefilter.
"""
import argparse
import csv
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request

BASE_URL = "https://variablesearch.lifbi.de/api"
TIMEOUT = 90
CACHE_DIR = os.path.join(tempfile.gettempdir(), "lifbi-variablesearch-cache")
CACHE_TTL = 24 * 3600

FILTER_TYPES = {1: "Eingangsfilter", 2: "Ausgangsfilter", 3: "Wertzuweisung", 4: "Wertefilter"}
SEVERITY_ORDER = {"Fehler": 0, "Warnung": 1, "Hinweis": 2}

DOCUMENTED_CONSTANTS = {"$FIRSTNAME$", "$LASTNAME$", "$MODE$", "$DAY$", "$MONTH$", "$YEAR$", "$NULL$",
                        "$LOOPCOUNTER$"}
LOOP_CONSTANT_RE = re.compile(r"^\$LOOPCOUNTER(_\d+)?\$$")
MODE_VALUES = {"CAWI", "CATI", "CAPI", "PAPI", "CBT"}
KEYWORDS = {"if", "autoif", "and", "or", "to", "mod"}
COMPARISON = {"==", "!=", "<>", "<=", ">=", "=", "<", ">"}

TOKEN_RE = re.compile(r"""
   (?P<ws>\s+)
  |(?P<const>\$[A-Za-z_][A-Za-z0-9_]*\$)
  |(?P<str>"[^"]*"|„[^“”"]*[“”"]|“[^”]*”|'[^']*'|‚[^‘’']*[‘’'])
  |(?P<num>\d+(?:\.\d+)?)
  |(?P<ident>[A-Za-z_][A-Za-z0-9_]*(?:\.(?:index|lag)\d*)?)
  |(?P<op>==|!=|<>|<=|>=|=|<|>|&|\||!|\+|-|\*|/)
  |(?P<punct>[(),;:])
  |(?P<other>.)
""", re.X)


# ---------------------------------------------------------------- loading

def parse_json(raw):
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
        pass
    return data


# ---------------------------------------------------------------- model

class Tok:
    __slots__ = ("kind", "text")

    def __init__(self, kind, text):
        self.kind, self.text = kind, text

    def __repr__(self):
        return f"{self.kind}:{self.text}"


def tokenize(text):
    return [Tok(m.lastgroup, m.group()) for m in TOKEN_RE.finditer(text) if m.lastgroup != "ws"]


def walk_items(chapters, path=(), episode=False):
    for c in chapters or []:
        p = path + (" ".join(str(c.get("name") or "").split()),)
        ep = episode or bool(c.get("episode"))
        for item in c.get("items") or []:
            yield item, p, ep
        yield from walk_items(c.get("chapters"), p, ep)


def build_index(instrument):
    """Variable name (lower) -> (order, itemId); all alias names of a variable are indexed."""
    index = {}
    for order, (item, _, _) in enumerate(walk_items(instrument.get("chapters"))):
        for v in item.get("variables") or []:
            for name in (v.get("name"), v.get("instrumentVariable"), v.get("sufVariable")):
                if name:
                    index.setdefault(name.lower(), (order, item.get("itemId")))
    return index


# ---------------------------------------------------------------- helpers

def split_statements(text):
    """Split at top-level ';' and line breaks. Returns [(statement, terminated_by_semicolon)]."""
    out, buf, depth = [], [], 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth <= 0 and ch in ";\r\n":
            if "".join(buf).strip() or ch == ";":
                out.append(("".join(buf).strip(), ch == ";"))
            buf = []
            depth = max(depth, 0)
            continue
        buf.append(ch)
    if "".join(buf).strip():
        out.append(("".join(buf).strip(), False))
    return [(s, t) for s, t in out if s]


def match_paren(toks, start):
    depth = 0
    for i in range(start, len(toks)):
        if toks[i].text == "(":
            depth += 1
        elif toks[i].text == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def is_operand(t):
    return t.kind in ("num", "const", "str") or (t.kind == "ident" and t.text.lower() not in KEYWORDS)


def is_value(t):
    return t.kind in ("num", "const") or (t.kind == "ident" and t.text.upper() in MODE_VALUES)


def amp_is_list(toks, i):
    """True if toks[i] ('&' or ',') separates values of a shorthand list (x & y), False for a conjunction."""
    j = i + 1
    if j < len(toks) and toks[j].text == "-":
        j += 1
    if j >= len(toks) or not is_value(toks[j]):
        return False
    after = toks[j + 1] if j + 1 < len(toks) else None
    return after is None or after.text not in COMPARISON


def unwrap(toks):
    """Remove redundant brackets around the whole expression."""
    while toks and toks[0].text == "(" and match_paren(toks, 0) == len(toks) - 1:
        toks = toks[1:-1]
    return toks


def render(toks):
    """Join tokens with conventional spacing."""
    out = []
    prev = None
    for i, t in enumerate(toks):
        s = t.text
        if prev is None:
            out.append(s)
        elif s in (")", ",", ";", ":"):
            out.append(s)
        elif prev.text == "(":
            out.append(s)
        elif s == "(" and prev.kind == "ident" and prev.text.lower() not in KEYWORDS | {"and", "or"}:
            out.append(s)  # function call / var(Label)
        elif prev.text == "-" and (i < 2 or toks[i - 2].kind in ("op", "punct") or toks[i - 2].text.lower() in KEYWORDS) \
                and t.kind == "num" and (i < 2 or toks[i - 2].text not in (")",)):
            out.append(s)  # unary minus
        elif prev.text == "!" and s == "(":
            out.append(s)
        else:
            out.append(" " + s)
        prev = t
    return "".join(out)


# ---------------------------------------------------------------- checks

class Checker:
    def __init__(self, instrument):
        self.index = build_index(instrument)

    def check(self, item, order, episode, wf):
        ftype = wf.get("filterType")
        text = wf.get("condition") or ""
        findings = []

        def add(sev, rule, msg):
            if (sev, rule, msg) not in findings:
                findings.append((sev, rule, msg))

        item_vars = {(v.get("name") or "").lower() for v in item.get("variables") or []}
        if not text.strip():
            add("Fehler", "LEER", "Filterfeld ist leer.")
            return findings, None
        if ftype not in FILTER_TYPES:
            add("Hinweis", "TYP", f"Filtertyp {ftype} ist nicht dokumentiert – nur allgemeine Prüfungen.")
        if text != text.strip() or re.search(r"[ \t]+(\r?\n|$)", text) or re.search(r"(\r?\n){2,}", text):
            add("Hinweis", "LEERRAUM", "Überflüssige Leerzeichen/Leerzeilen am Zeilenende.")

        statements = split_statements(text)
        fixed = []
        prefixed = 0
        for stmt, terminated in statements:
            toks = tokenize(stmt)
            self.generic(toks, ftype, item, order, episode, item_vars, add)
            if ftype in (1, 2):
                fx, has_prefix = self.check_condition(toks, item_vars, add)
                prefixed += has_prefix
                if has_prefix and len(statements) > 1 and not terminated:
                    add("Hinweis", "SEMIKOLON", "Mehrere variablenbezogene Bedingungen werden jeweils mit ';' abgeschlossen.")
                fixed.append(fx + (";" if has_prefix and len(statements) > 1 else ""))
            elif ftype == 3:
                fixed.append(self.check_autoif(toks, item_vars, add))
            elif ftype == 4:
                fixed.append(self.check_valuefilter(toks, add))
            else:
                fixed.append(render(self.normalize(toks)))
        if ftype in (1, 2) and len(statements) > 1 and prefixed < len(statements):
            add("Fehler", "MEHRFACH", "Mehrere Bedingungen ohne Variablen-Präfix ('variable: if (…);'). "
                                      "Bedingungen in einem Feld müssen sich auf einzelne Variablen beziehen.")
        suggestion = "\n".join(f for f in fixed if f)
        if any(r == "FREITEXT" for _, r, _ in findings):
            suggestion = "Kommentar aus dem Filterfeld entfernen (ggf. in ein Anmerkungsfeld verschieben)."
        if suggestion.strip() == text.strip():
            suggestion = None
        return findings, suggestion

    # -- checks for every filter type
    def generic(self, toks, ftype, item, order, episode, item_vars, add):
        depth = 0
        for t in toks:
            depth += (t.text == "(") - (t.text == ")")
            if depth < 0:
                break
        if depth != 0:
            add("Fehler", "KLAMMERN", "Klammern sind nicht ausgeglichen.")

        unknown_words = []
        skip = set()
        for i, t in enumerate(toks):
            if i in skip:
                continue
            nxt = toks[i + 1] if i + 1 < len(toks) else None
            if t.kind == "str":
                if t.text[0] in "„“‚‘":
                    add("Fehler", "ANFUEHRUNG", f"Textwert mit typografischen Anführungszeichen {t.text} – Textwerte "
                                                f"sind in den Konventionen nicht dokumentiert; mindestens gerade "
                                                f"Anführungszeichen verwenden.")
                    continue
                add("Fehler", "TEXTWERT", f"Textwert {t.text} – Textwerte in Anführungszeichen sind in den Konventionen "
                                          f"nicht dokumentiert (Werte als Zahlencode angeben).")
            elif t.kind == "const":
                if t.text == "$ALL$":
                    if ftype != 4:
                        add("Fehler", "KONSTANTE", "$ALL$ ist nur im Wertefilter zulässig.")
                elif t.text not in DOCUMENTED_CONSTANTS and not LOOP_CONSTANT_RE.match(t.text):
                    add("Fehler", "KONSTANTE", f"Konstante {t.text} ist in den Konventionen nicht dokumentiert.")
                if LOOP_CONSTANT_RE.match(t.text) and not episode:
                    add("Fehler", "SCHLEIFE", f"{t.text} ist nur in Kapiteln zulässig, die als Episode/Schleife markiert sind.")
            elif t.kind == "ident":
                low = t.text.lower()
                if nxt is not None and nxt.text == "(" and low not in KEYWORDS:
                    if low in self.index or low in item_vars:
                        skip.add(i + 2)  # e.g. 'Label' in var(Label)
                        add("Fehler", "LABELREF", f"'{t.text}(…)' – Label-/Eigenschaftsreferenzen sind in Filtern nicht "
                                                  f"dokumentiert (nur in Texteinblendungen als $var(Label)$).")
                    else:
                        add("Fehler", "FUNKTION", f"Funktion '{t.text}()' ist in den Konventionen nicht dokumentiert "
                                                  f"(zulässig: mod()).")
                    continue
                if low in KEYWORDS:
                    if t.text in ("AND", "OR", "MOD", "IF"):
                        add("Hinweis", "SCHREIBWEISE", f"'{t.text}' → bevorzugt '{low}'.")
                    elif t.text != low:
                        add("Hinweis", "SCHREIBWEISE", f"'{t.text}' → bevorzugt '{low}'.")
                    continue
                if "." in t.text:
                    base = t.text.split(".")[0].lower()
                    if not episode:
                        add("Fehler", "SCHLEIFE", f"'{t.text}' (index/lag) ist nur in Episoden-/Schleifenkapiteln zulässig.")
                    low = base
                if t.text.upper() in MODE_VALUES:
                    continue
                if not re.search(r"\d", low):
                    unknown_words.append(t.text)
                    continue
                if low not in self.index:
                    add("Warnung", "VARIABLE", f"Variable '{t.text}' kommt im Instrument nicht vor "
                                               f"(Tippfehler? Preload aus anderem Instrument?).")
                elif ftype in (1, 3) and self.index[low][0] > order:
                    add("Warnung", "REIHENFOLGE", f"'{t.text}' wird erst später im Instrument erhoben – "
                                                  f"der Filter kann zu diesem Zeitpunkt nicht ausgewertet werden.")
            elif t.kind == "op":
                if t.text == "<>":
                    add("Hinweis", "SCHREIBWEISE", "'<>' → bevorzugt '!='.")
                elif t.text == "|":
                    add("Hinweis", "SCHREIBWEISE", "'|' → bevorzugt 'or'.")
            elif t.kind == "other":
                add("Fehler", "ZEICHEN", f"Unzulässiges Zeichen '{t.text}'.")

        if len(unknown_words) >= 2:
            add("Fehler", "FREITEXT", f"Freitext im Filterfeld ('{' '.join(unknown_words[:4])}…') – Kommentare gehören "
                                      f"nicht in das Filterfeld.")
            return  # further syntax checks on free text are noise
        else:
            for w in unknown_words:
                add("Fehler", "BEZEICHNER", f"Unbekannter Bezeichner '{w}' – weder Variable noch dokumentierte Konstante "
                                            f"(z. B. $YEAR$).")

        # operands without operator in between (e.g. missing comma)
        for a, b in zip(toks, toks[1:]):
            if is_operand(a) and is_operand(b) and not (a.kind == "ident" and b.text == "("):
                if a.kind == "ident" and a.text.lower() in KEYWORDS:
                    continue
                add("Fehler", "OPERATOR", f"Zwischen '{a.text}' und '{b.text}' fehlt ein Operator oder Komma.")

        # shorthand value lists after comparisons
        for i, t in enumerate(toks):
            if t.kind == "op" and t.text in COMPARISON and i + 2 < len(toks):
                j = i + 1
                if toks[j].text == "-":
                    j += 1
                if j + 1 < len(toks) and toks[j + 1].text in (",", "&"):
                    sep = toks[j + 1].text
                    if not amp_is_list(toks, j + 1):
                        continue
                    if t.text in ("!=", "<>"):
                        add("Warnung", "NEGLISTE", f"'{t.text} … {sep} …' ist mehrdeutig – die Kurzformen 'x,y' und "
                                                   f"'x & y' sind nur für Gleichheit definiert. Explizit schreiben, "
                                                   f"z. B. 'v != 9 and v != 14'.")
                    elif sep == "&" and t.text in ("==", "="):
                        add("Warnung", "UNERFUELLBAR", "'== x & y' bedeutet 'gleich x UND gleich y' und kann für eine "
                                                       "Variable nie wahr sein – gemeint ist vermutlich 'x,y' (eins davon).")

    # -- normalisation for suggestions
    def normalize(self, toks, in_condition=True):
        out = []
        n = len(toks)
        for i, t in enumerate(toks):
            txt = t.text
            if t.kind == "ident" and txt.lower() in KEYWORDS:
                t = Tok("ident", txt.lower())
            elif t.kind == "op" and txt == "<>":
                t = Tok("op", "!=")
            elif t.kind == "op" and txt == "|":
                t = Tok("ident", "or")
            elif t.kind == "op" and txt == "=" and in_condition:
                t = Tok("op", "==")
            elif t.kind == "op" and txt == "&":
                if not amp_is_list(toks, i):  # conjunction, not a value shorthand
                    t = Tok("ident", "and")
                else:
                    k = i - 1  # find the comparison this value list belongs to
                    while k >= 0 and (is_value(toks[k]) or toks[k].text in ("&", ",", "-")):
                        k -= 1
                    if k >= 0 and toks[k].text in ("==", "="):
                        t = Tok("punct", ",")  # '== x & y' can never be true – 'one of' is meant
            elif t.kind == "str" and txt[0] in "„“‚‘":
                t = Tok("str", '"' + txt[1:-1] + '"')
            out.append(t)
        out = self.expand_negated_lists(out)
        # insert missing commas inside function argument lists
        fixed = []
        for a in out:
            if fixed and is_operand(fixed[-1]) and is_operand(a) and not (fixed[-1].kind == "ident" and a.text == "("):
                fixed.append(Tok("punct", ","))
            fixed.append(a)
        return fixed

    def expand_negated_lists(self, toks):
        out, i = [], 0
        while i < len(toks):
            t = toks[i]
            if t.text == "!=" and out and out[-1].kind == "ident":
                var = out[-1]
                vals, j = [], i + 1
                while j < len(toks):
                    v = [toks[j]] if toks[j].text != "-" else [toks[j], toks[j + 1]] if j + 1 < len(toks) else [toks[j]]
                    vals.append(v)
                    j += len(v)
                    if j < len(toks) and toks[j].text in (",", "&") and amp_is_list(toks, j):
                        j += 1
                        continue
                    break
                if len(vals) > 1:
                    out.pop()
                    out.append(Tok("punct", "("))
                    for k, v in enumerate(vals):
                        if k:
                            out.append(Tok("ident", "and"))
                        out += [var, Tok("op", "!=")] + v
                    out.append(Tok("punct", ")"))
                    i = j
                    continue
            out.append(t)
            i += 1
        return out

    @staticmethod
    def strip_if(toks, add, keyword="if"):
        """Remove leading keyword and redundant outer brackets; report double keywords."""
        body = list(toks)
        if body and body[0].text.lower() == keyword:
            body = body[1:]
        rest = [t for t in body if t.text.lower() == "if"]
        if rest:
            add("Fehler", "DOPPELT_IF", "'if' kommt innerhalb der Bedingung erneut vor – nur ein 'if' am Anfang.")
            body = [t for t in body if t.text.lower() != "if"]
        while body and body[0].text == "(" and match_paren(body, 0) == len(body) - 1:
            body = body[1:-1]
        return body

    def check_condition(self, toks, item_vars, add):
        prefix = None
        if len(toks) >= 2 and toks[0].kind == "ident" and toks[1].text == ":" and toks[0].text.lower() != "if":
            prefix = toks[0].text
            if prefix.lower() not in item_vars:
                add("Fehler", "PRAEFIX", f"Präfix '{prefix}:' ist keine Variable dieses Items.")
            toks = toks[2:]
        if not toks or toks[0].text.lower() != "if":
            add("Fehler", "IF_FEHLT", "Bedingung beginnt nicht mit 'if' (Format: 'if (Bedingung)').")
        elif len(toks) < 2 or toks[1].text != "(" or match_paren(toks, 1) != len(toks) - 1:
            add("Fehler", "KLAMMERFORM", "Bedingung steht nicht vollständig in einem Klammerpaar ('if (Bedingung)').")
        if any(t.text == "=" for t in toks):
            add("Hinweis", "SCHREIBWEISE", "'=' in Bedingungen → bevorzugt '=='.")
        if any(t.text == "&" and not amp_is_list(toks, i) for i, t in enumerate(toks)):
            add("Hinweis", "SCHREIBWEISE", "'&' als Verknüpfung → bevorzugt 'and'.")
        body = self.strip_if(toks, add)
        fixed = "if (" + render(unwrap(self.normalize(body))) + ")"
        return (f"{prefix}: " if prefix else "") + fixed, prefix is not None

    def check_autoif(self, toks, item_vars, add):
        if not toks or toks[0].text.lower() != "autoif":
            add("Fehler", "AUTOIF_FEHLT", "Wertzuweisung beginnt nicht mit 'autoif' (Format: 'autoif (Bedingung): variable = Wert').")
            return render(self.normalize(toks, in_condition=False))
        if len(toks) < 2 or toks[1].text != "(":
            add("Fehler", "KLAMMERFORM", "Bedingung der Wertzuweisung steht nicht in Klammern.")
            return render(self.normalize(toks, in_condition=False))
        end = match_paren(toks, 1)
        if end < 0:
            return render(self.normalize(toks, in_condition=False))
        cond, rest = toks[2:end], toks[end + 1:]
        if not rest or rest[0].text != ":":
            add("Fehler", "DOPPELPUNKT", "Nach der Bedingung fehlt der Doppelpunkt ('autoif (Bedingung): variable = Wert').")
        else:
            rest = rest[1:]
        if any(t.text == "=" for t in cond):
            add("Hinweis", "SCHREIBWEISE", "'=' in der Bedingung → bevorzugt '==' ('=' ist der Zuweisung vorbehalten).")
        if any(t.text == "&" and not amp_is_list(cond, i) for i, t in enumerate(cond)):
            add("Hinweis", "SCHREIBWEISE", "'&' als Verknüpfung → bevorzugt 'and'.")
        target = rest[0].text if rest else None
        if len(rest) < 3 or rest[1].text != "=":
            add("Fehler", "ZUWEISUNG", "Zuweisung 'variable = Wert' nach der Bedingung fehlt oder ist fehlerhaft.")
        elif target and target.lower() not in item_vars:
            add("Warnung", "ZIEL", f"Zielvariable '{target}' gehört nicht zu diesem Item.")
        cond_fix = render(unwrap(self.normalize(self.strip_if(cond, add, keyword="if"))))
        value_fix = render(self.normalize(rest, in_condition=False))
        return f"autoif ({cond_fix}): {value_fix}"

    def check_valuefilter(self, toks, add):
        if not toks or toks[0].text.lower() != "if" or len(toks) < 2 or toks[1].text != "(":
            add("Fehler", "WERTEFILTER", "Wertefilter hat nicht die Form 'if (Bedingung): variable: Werte;'.")
            return render(self.normalize(toks, in_condition=False))
        end = match_paren(toks, 1)
        rest = toks[end + 1:] if end > 0 else []
        if len(rest) < 3 or rest[0].text != ":" or rest[2].text != ":" or not (rest[1].kind == "ident" or rest[1].text == "$ALL$"):
            add("Fehler", "WERTEFILTER", "Nach der Bedingung fehlt ': variable: Werteliste' bzw. ': $ALL$: Werteliste'.")
            return render(self.normalize(toks, in_condition=False))
        cond = render(self.normalize(toks[2:end]))
        values = render(self.normalize(rest[3:], in_condition=False))
        return f"if ({cond}): {rest[1].text}: {values};"


# ---------------------------------------------------------------- report

def run(instrument, include_hints=True):
    checker = Checker(instrument)
    rows = []
    for order, (item, path, episode) in enumerate(walk_items(instrument.get("chapters"))):
        for wf in item.get("conditionalWorkflows") or []:
            findings, suggestion = checker.check(item, order, episode, wf)
            if not include_hints:
                findings = [f for f in findings if f[0] != "Hinweis"]
            if not findings:
                continue
            findings.sort(key=lambda f: SEVERITY_ORDER[f[0]])
            rows.append({
                "itemId": item.get("itemId"),
                "item": " ".join(str(item.get("label") or "").split()),
                "kapitel": " > ".join(p for p in path if p),
                "variablen": ", ".join(v.get("name") for v in item.get("variables") or []),
                "filterTyp": FILTER_TYPES.get(wf.get("filterType"), f"Typ {wf.get('filterType')}"),
                "filter": (wf.get("condition") or "").strip(),
                "schwere": findings[0][0],
                "befunde": [{"schwere": s, "regel": r, "text": t} for s, r, t in findings],
                "vorschlag": suggestion,
            })
    return rows


def md_cell(text):
    return str(text or "").replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def print_markdown(instrument, rows, total):
    print(f"# Filterprüfung Instrument {instrument.get('id')}: {' '.join(str(instrument.get('name')).split())}\n")
    counts = {s: sum(1 for r in rows if r["schwere"] == s) for s in SEVERITY_ORDER}
    print(f"{total} Filter geprüft – {counts['Fehler']} mit Fehlern, {counts['Warnung']} mit Warnungen, "
          f"{counts['Hinweis']} nur mit Hinweisen.\n")
    for title, sevs in (("Fehler und Warnungen", ("Fehler", "Warnung")), ("Nur Hinweise (Schreibweise)", ("Hinweis",))):
        sel = [r for r in rows if r["schwere"] in sevs]
        if not sel:
            continue
        print(f"## {title}\n")
        print("| Item | Kapitel | Typ | Filter | Schwere | Befunde | Vorschlag (automatisch) |")
        print("|---|---|---|---|---|---|---|")
        for r in sel:
            bef = "<br>".join(f"[{b['schwere']}/{b['regel']}] {b['text']}" for b in r["befunde"])
            print(f"| {r['itemId']}: {md_cell(r['item'])} ({md_cell(r['variablen'])}) | {md_cell(r['kapitel'])} | "
                  f"{r['filterTyp']} | `{md_cell(r['filter'])}` | {r['schwere']} | {md_cell(bef)} | "
                  f"{('`' + md_cell(r['vorschlag']) + '`') if r['vorschlag'] else '–'} |")
        print()


def write_csv(path, instrument, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Instrument", "Item-ID", "Item", "Variablen", "Kapitel", "Filtertyp", "Filter", "Schwere",
                    "Fehlerbeschreibung", "Verbesserungsvorschlag"])
        for r in rows:
            w.writerow([instrument.get("id"), r["itemId"], r["item"], r["variablen"], r["kapitel"], r["filterTyp"],
                        r["filter"], r["schwere"],
                        "\n".join(f"[{b['schwere']}] {b['text']}" for b in r["befunde"]),
                        r["vorschlag"] or ""])


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Prüft Filter (conditional workflows) eines LIfBi-Instruments")
    p.add_argument("instrument", nargs="?", type=int, help="Instrument-ID")
    p.add_argument("--file", help="Instrument-JSON aus Datei statt API")
    p.add_argument("--csv", help="Ergebnis zusätzlich als CSV (UTF-8, Semikolon) speichern")
    p.add_argument("--json", action="store_true", help="Ergebnis als JSON ausgeben")
    p.add_argument("--no-hints", action="store_true", help="Hinweise zur Schreibweise weglassen")
    p.add_argument("--refresh", action="store_true", help="Cache ignorieren")
    args = p.parse_args()
    if not args.instrument and not args.file:
        p.error("Instrument-ID oder --file angeben")

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            instrument = parse_json(f.read())
    else:
        instrument = fetch_instrument(args.instrument, args.refresh)

    total = sum(len(i.get("conditionalWorkflows") or []) for i, _, _ in walk_items(instrument.get("chapters")))
    rows = run(instrument, include_hints=not args.no_hints)
    if args.csv:
        write_csv(args.csv, instrument, rows)
    if args.json:
        print(json.dumps({"instrument": instrument.get("id"), "geprueft": total, "befunde": rows},
                         ensure_ascii=False, indent=2))
    else:
        print_markdown(instrument, rows, total)
        if args.csv:
            print(f"CSV gespeichert: {os.path.abspath(args.csv)}")


if __name__ == "__main__":
    main()
