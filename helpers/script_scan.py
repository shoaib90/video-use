"""Find the places in a script where a motion graphic earns its place.

This is the decision layer. Components are useless without it: the hard part of
motion design on a talking-head script is not drawing a chip, it is noticing
that *this* line enumerates five things and *that* one states a figure, and
leaving the other two thirds of the film alone.

The taxonomy is taken from a frame-by-frame reading of a reference video
(Somrat Dutta, "If You ONLY Watch One Motion Design Video"), matching what was
on screen against what was being said at that moment:

    line enumerates ("five pillars")        -> list carousel / numbered badges
    line states a figure ("15,000 a month") -> big numeral + unit
    line contrasts ("X and Y are not the    -> two opposing chips
        same thing")
    line lists attributes ("contrast,       -> staggered sub-items
        hierarchy and balance")
    line names/defines ("I call it the      -> term card
        post-mortem method")
    line is emphatic ("nobody tells you")   -> scattered kinetic type
    nothing notable                          -> PLAIN SHOT

That last row is a real output, not the absence of one. In the reference, about
a third of sampled frames carry no graphic at all, and that restraint is what
makes the rest land. A detector that fires on everything is worse than none.

Detection is deliberately conservative and every hit carries a confidence and
the evidence that produced it, because the editor decides - this proposes.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

# -------- spelled-out numbers -------------------------------------------------
# Hard Rule 8 keeps `smart_format` off, so the ASR returns "fifteen thousand",
# not "15,000". Any figure detector has to read words.
UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}
SCALES = {"hundred": 100, "thousand": 1_000, "lakh": 100_000, "lakhs": 100_000,
          "million": 1_000_000, "crore": 10_000_000, "crores": 10_000_000,
          "billion": 1_000_000_000}
# Units that make a bare number worth putting on screen.
QUALIFIERS = {
    "rupees", "rupee", "dollars", "dollar", "dirhams", "dirham", "euros", "pounds",
    "percent", "subscribers", "views", "followers", "years", "year", "months",
    "month", "weeks", "week", "days", "day", "hours", "hour", "minutes", "minute",
    "kilometers", "kilometres", "km", "people", "clients", "projects", "times",
}
# Units whose small quantities are conversational, not claims: "give me ten
# minutes", "it took four weeks". Putting those on screen is the over-firing
# that makes a detector worse than nothing.
SOFT_UNITS = {"minutes", "minute", "hours", "hour", "weeks", "week",
              "days", "day", "months", "month", "years", "year", "times"}
HARD_UNITS = {"rupees", "rupee", "dollars", "dollar", "dirhams", "dirham",
              "euros", "pounds", "percent", "subscribers", "views",
              "followers", "people", "clients", "projects"}


# Framings that mark a quantity as conversational rather than a claim:
# "give me the next ten minutes", "in the next few minutes".
CHATTY = ("next few", "give me the next", "in the next", "a couple of",
          "a few", "for a few", "every single")
# The unit is often a time word while the SUBJECT is money ("fifteen thousand
# to forty thousand a month"). The surrounding verb is what says so.
MONEY_CTX = ("make", "makes", "making", "made", "earn", "earns", "earning",
             "pay", "pays", "paid", "charge", "charging", "charged", "cost",
             "costing", "salary", "revenue", "profit", "per project", "a month",
             "worth", "price")


def salience(value: int, unit: str | None, is_range: bool,
             context: str = "") -> float:
    """How much this figure wants to be on screen.

    Derived from the reference edit: the figures that got a graphic were an
    oddly specific proof point (12,917 dirhams) and a comparison claim
    (15k-40k a month). The ones that did not were round, conversational.

    Roundness is judged against the number's own magnitude - 13 is specific,
    150,000 is round. An earlier version computed the divisor as
    10**(len(str(v))-2), which makes every two-digit number "round" and so
    silently scored "thirteen years ago" - the spine of an entire episode - at
    zero.
    """
    s = 0.0
    div = 10 if value < 1000 else 10 ** (len(str(value)) - 2)
    if value % div:
        s += 0.45
    if value >= 1000:
        s += 0.20
    if value >= 100_000:
        s += 0.10
    if unit in HARD_UNITS:
        s += 0.35
    elif unit in SOFT_UNITS and value < 100:
        s -= 0.10
    if is_range:
        s += 0.30                       # a range is always a claim being made
    low = context.lower()
    # "N years ago" anchors a narrative - the strongest figure cue in a
    # personal essay, and the one a vlog script actually produces.
    if unit in ("years", "year", "months", "month") and " ago" in low:
        s += 0.45
    if any(c in low for c in CHATTY):
        s -= 0.45
    if unit not in HARD_UNITS and any(c in low for c in MONEY_CTX):
        s += 0.25
    return max(0.0, min(1.0, s))


ORDINALS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh",
            "eighth", "ninth", "tenth"]
COUNT_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
               "eight": 8, "nine": 9, "ten": 10}

# A count word only signals a list when it is counting *things*.
ENUM_NOUNS = (r"pillars?|principles?|steps?|stages?|lanes?|rules?|reasons?|ways?|"
              r"things?|parts?|types?|kinds?|levels?|tips?|lessons?|mistakes?|"
              r"points?|phases?|options?|choices?|layers?|elements?|factors?")

CONTRAST_PATTERNS = [
    r"\b(\w[\w\s]{0,24}?)\s+and\s+(\w[\w\s]{0,24}?)\s+are\s+not\s+the\s+same\b",
    r"\bnot\s+(\w[\w\s]{0,24}?)\s*,?\s*but\s+(\w[\w\s]{0,24}?)\b",
    r"\b(\w[\w\s]{0,20}?)\s+versus\s+(\w[\w\s]{0,20}?)\b",
    r"\binstead\s+of\s+(\w[\w\s]{0,24}?)\s*,\s*(\w[\w\s]{0,24}?)\b",
]
EMPHASIS_CUES = [
    "nobody tells you", "no one tells you", "nobody talks about",
    "what nobody", "the single reason", "the single biggest",
    "here's the truth", "here is the truth", "the honest truth",
    "the most important thing",
]
DEFINE_PATTERNS = [
    r"\bi\s+call\s+it\s+(?:the\s+)?([\w\s]{3,40}?)\s*[.,]",
    r"\bit'?s\s+called\s+(?:the\s+)?([\w\s]{3,40}?)\s*[.,]",
    r"\bthis\s+is\s+(?:what\s+i\s+call\s+)?(?:the\s+)?([\w\s]{3,40}?)\s+method\b",
]


@dataclass
class Opportunity:
    kind: str
    component: str
    confidence: float
    start: float
    end: float
    quote: str
    evidence: str
    data: dict = field(default_factory=dict)

    def as_dict(self):
        d = asdict(self)
        d["start"] = round(d["start"], 3)
        d["end"] = round(d["end"], 3)
        return d


def words_of(transcript: Path) -> list[dict]:
    return [w for w in json.loads(Path(transcript).read_text()).get("words", [])
            if w.get("type") == "word"]


def phrases(ws: list[dict], gap: float = 0.55) -> list[list[dict]]:
    """Group words into sentences. A graphic belongs to a sentence, not a word.

    Splitting on silence alone is wrong for the common case: an ALREADY EDITED
    video has had its dead air removed, so there are no gaps left to split on.
    The reference video collapsed to 11 groups for 2267 words that way, which
    made every detector fire on the same paragraph. Sentence-final punctuation
    is the reliable boundary; the gap is a secondary cue for unedited rushes.
    """
    if not ws:
        return []
    out, cur = [], [ws[0]]
    for a, b in zip(ws, ws[1:]):
        ends_sentence = a["text"].rstrip('"\'').endswith((".", "?", "!"))
        if ends_sentence or b["start"] - a["end"] >= gap:
            out.append(cur)
            cur = [b]
        else:
            cur.append(b)
    out.append(cur)
    return [g for g in out if g]


def plain(g: list[dict]) -> str:
    return " ".join(w["text"] for w in g)


def _read_number(tokens: list[str]) -> tuple[int | None, int]:
    """Parse a spelled-out number from the head of `tokens`.

    Returns (value, tokens_consumed). Handles "fifteen thousand",
    "twelve thousand nine hundred seventeen", "one and a half lakh".
    """
    total, current, used, seen = 0, 0, 0, False
    seen_scale = False
    i = 0
    while i < len(tokens):
        t = tokens[i].lower().strip(".,?!")
        if t in UNITS:
            # Indian spoken idiom: "two fifty" is 250, "one twenty" is 120 -
            # a units digit followed by a tens word is concatenation, not sum.
            nxt = tokens[i + 1].lower().strip(".,") if i + 1 < len(tokens) else ""
            if (current in range(1, 10) and UNITS.get(t, 0) >= 20
                    and UNITS[t] % 10 == 0 and not seen_scale):
                current = current * 100 + UNITS[t]
            elif (UNITS[t] < 10 and nxt in UNITS and UNITS[nxt] >= 20
                    and UNITS[nxt] % 10 == 0 and not current):
                current = UNITS[t] * 100 + UNITS[nxt]
                i += 1
            else:
                current += UNITS[t]
            seen = True
        elif t in SCALES:
            if not seen:
                if t.endswith("s"):
                    break                 # "lakhs every year" - indefinite, not a figure
                current = 1
            scale = SCALES[t]
            seen_scale = True
            if scale >= 1000:
                total += current * scale
                current = 0
            else:
                current *= scale
            seen = True
        elif t == "and" and seen and i + 1 < len(tokens) and \
                tokens[i + 1].lower().strip(".,") in UNITS:
            pass                                  # "nine hundred and seventeen"
        elif t.replace(",", "").isdigit():
            current += int(t.replace(",", ""))
            seen = True
        else:
            break
        i += 1
        used = i
        # A comma ends the number. "hundred, hundred and fifty kilometers" is
        # two alternatives, not one quantity - without this it parses as 10,050.
        if tokens[i - 1].rstrip().endswith(","):
            break
    return ((total + current) if seen else None), used


def detect(ws: list[dict], source: str = "") -> list[Opportunity]:
    found: list[Opportunity] = []
    # A "not X but Y" is only worth two chips when X and Y are things the script
    # keeps coming back to. "Motion design is not difficult, but people..." is
    # rhetorical negation; "video editing and motion design" are real topics.
    whole = " ".join(w["text"] for w in ws).lower()

    def is_topic(term: str) -> bool:
        head = term.split()[-1] if term.split() else term
        return whole.count(head) >= 2 and len(head) > 3
    for g in phrases(ws):
        text = plain(g)
        low = text.lower()
        t0, t1 = g[0]["start"], g[-1]["end"]

        def span(i, j):
            return g[max(0, i)]["start"], g[min(len(g) - 1, j)]["end"]

        # --- figures -------------------------------------------------------
        toks = [w["text"] for w in g]
        i = 0
        while i < len(toks):
            val, used = _read_number(toks[i:])
            if val is None or not used or val < 3:
                i += 1
                continue
            j = i + used
            hi, is_range = None, False
            # "fifteen thousand TO forty thousand a month" is ONE claim
            joiner = toks[j].lower().strip(".,") if j < len(toks) else ""
            prev = toks[i - 1].lower() if i else ""
            if joiner in ("to", "-") or (joiner == "and" and prev == "between"):
                hi, used2 = _read_number(toks[j + 1:])
                if hi is not None and used2 and hi > val:
                    is_range, j = True, j + 1 + used2
            tail = [t.lower().strip(".,") for t in toks[j:j + 3]]
            qual = next((q for q in tail if q in QUALIFIERS), None)
            if qual:
                j += tail.index(qual) + 1
            ctx = " ".join(toks[max(0, i - 4):j + 4])
            sal = salience(hi or val, qual, is_range, ctx)
            if sal >= 0.55:
                st, en = span(i, j - 1)
                disp = f"{val:,}" + (f"-{hi:,}" if is_range else "")
                found.append(Opportunity(
                    "figure", "big_number", round(min(0.95, 0.45 + sal / 2), 2),
                    st, en, " ".join(toks[i:j]),
                    f"parsed {disp}" + (f" {qual}" if qual else "")
                    + f" (salience {sal:.2f})",
                    {"value": val, "high": hi, "range": is_range, "unit": qual,
                     "display": disp, "label": qual or ""}))
            i = max(j, i + 1)

        # --- enumeration ---------------------------------------------------
        m = re.search(rf"\b({'|'.join(COUNT_WORDS)})\s+({ENUM_NOUNS})\b", low)
        if m:
            found.append(Opportunity(
                "enumeration", "list_carousel", 0.9, t0, t1, text,
                f"'{m.group(0)}' announces {COUNT_WORDS[m.group(1)]} items",
                {"count": COUNT_WORDS[m.group(1)], "noun": m.group(2)}))

        # --- ordinal step marker -------------------------------------------
        for n, o in enumerate(ORDINALS, start=1):
            if re.match(rf"^{o}\b[,.]", low) or re.match(rf"^(so\s+|now\s+)?{o}\b\s*[,.]", low):
                found.append(Opportunity(
                    "step", "numbered_badge", 0.75, t0, t1, text,
                    f"phrase opens on the ordinal '{o}'", {"index": n}))
                break

        # --- attribute list ("contrast, hierarchy, and balance") -----------
        m = re.search(r"\b(\w{3,}),\s+(\w{3,}),?\s+and\s+(\w{3,})\b", text)
        if (m and len(set(g.lower() for g in m.groups())) == 3
                and m.group(1).lower() not in ORDINALS):
            found.append(Opportunity(
                "attribute_list", "staggered_items", 0.7, t0, t1, text,
                f"three-item series: {', '.join(m.groups())}",
                {"items": list(m.groups())}))

        # --- contrast -------------------------------------------------------
        for pat in CONTRAST_PATTERNS:
            m = re.search(pat, low)
            if m:
                a, b = (x.strip() for x in m.groups()[:2])
                if (2 < len(a) < 30 and 2 < len(b) < 30
                        and is_topic(a) and is_topic(b)):
                    found.append(Opportunity(
                        "contrast", "opposing_chips", 0.8, t0, t1, text,
                        f"contrast between '{a}' and '{b}'",
                        {"left": a, "right": b}))
                break

        # --- naming / definition -------------------------------------------
        for pat in DEFINE_PATTERNS:
            m = re.search(pat, low)
            if m:
                found.append(Opportunity(
                    "definition", "term_card", 0.75, t0, t1, text,
                    f"names a concept: '{m.group(1).strip()}'",
                    {"term": m.group(1).strip()}))
                break

        # --- emphasis --------------------------------------------------------
        cue = next((c for c in EMPHASIS_CUES if c in low), None)
        if cue:
            found.append(Opportunity(
                "emphasis", "kinetic_type", 0.55, t0, t1, text,
                f"emphatic cue: '{cue}'", {"cue": cue}))

    # Overlapping opportunities of the SAME kind are alternatives - keep the
    # strongest. Different kinds compose: in the reference the 15k-40k figure is
    # drawn ON the two chips that the same sentence triggers, and suppressing one
    # for the other would have lost half the graphic.
    found.sort(key=lambda o: (-o.confidence, o.start))
    kept: list[Opportunity] = []
    for o in found:
        clash = any(o.kind == k.kind and not (o.end <= k.start or o.start >= k.end)
                    for k in kept)
        if not clash:
            kept.append(o)
    kept.sort(key=lambda o: o.start)
    for o in kept:
        o.data["source"] = source
    return kept


def scan_edit(edit_dir: Path, only: list[str] | None = None) -> dict:
    edit_dir = Path(edit_dir)
    out = {}
    for f in sorted((edit_dir / "transcripts").glob("*.json")):
        if only and f.stem not in only:
            continue
        ws = words_of(f)
        if not ws:
            continue
        hits = detect(ws, f.stem)
        if hits:
            out[f.stem] = [h.as_dict() for h in hits]
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("edit_dir", type=Path)
    ap.add_argument("--source", action="append", help="limit to these transcript stems")
    ap.add_argument("-o", "--output", type=Path)
    a = ap.parse_args()

    res = scan_edit(a.edit_dir, a.source)
    n = sum(len(v) for v in res.values())
    for src, hits in res.items():
        print(f"\n{src}")
        for h in hits:
            print(f"  [{h['start']:7.2f}] {h['kind']:<14} {h['component']:<16} "
                  f"p={h['confidence']:.2f}  {h['evidence']}")
            print(f"              \"{h['quote'][:88]}\"")
    print(f"\n{n} opportunities across {len(res)} sources")
    if a.output:
        json.dump(res, open(a.output, "w"), indent=1, ensure_ascii=False)
        print(f"wrote {a.output}")
