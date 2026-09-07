#!/usr/bin/env python3
"""fread.py - extraction probe: pull every finding definition out of the prose.

Reads research/**/*.md and the memory dir, separates finding DEFINITIONS from
mere REFERENCES, and reports whether the existing prose is machine-readable
enough to back a ledger. Derived-only: writes a TSV, never touches a source.
"""
import re, sys, os, glob, csv, collections

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
MEM  = sys.argv[2] if len(sys.argv) > 2 else None
OUT  = sys.argv[3] if len(sys.argv) > 3 else "findings.tsv"

# A DEFINITION starts a line (allowing a list bullet or a table pipe) with **Fnnn**
DEF = re.compile(r'^(?P<lead>\s*(?:[-*+]\s+|\|\s*)?)\*\*F(?P<n>\d{1,4})\*\*(?P<sep>\s*[.\u2014\u2013:)\-]|\s|\s*\|)')
# Bare (unbolded) definition: "F123." / "F123)" at line start
# bare, incl. a summary-table row: '| F218 — every gate input is Measured | W6 |'
DEF_BARE = re.compile(r'^(?P<lead>\s*(?:[-*+]\s+|\|\s*)?)F(?P<n>\d{1,4})(?P<sep>[.\u2014\u2013:)])\s')
DEF_HEAD = re.compile(r'^(?P<lead>#{1,6}\s+(?:\d{1,2}[.)]\s*)?[^A-Za-z0-9]{0,12}\**)F(?P<n>\d{1,4})\**(?P<sep>\s*[.\u2014\u2013:)\-]|\s)')
# marker+bold-spanning-claim: '⚠ **F574 — the two axes are NOT orthogonal**'
# marker + bold, e.g. '⚠ **F574 — the two axes are NOT orthogonal**'. A leading '(' is
# forbidden: '(F541) — so the slot count...' is a citation on a continuation line.
DEF_MARK = re.compile(r'^(?P<lead>\s*(?:[-*+]\s+)?[^A-Za-z0-9\s(]{0,4}\s*\*\*)F(?P<n>\d{1,4})(?P<sep>\s*[.\u2014\u2013:)\-]\s|\s)')
REF = re.compile(r'\bF(\d{1,4})\b')
RANGE = re.compile(r'F(\d{1,4})\s*[\u2013\u2014-]\s*F?(\d{1,4})')
STATUS = {'\U0001F6A8':'alarm','\u26A0':'caution','\u2705':'settled',
          '\U0001F389':'win','\u25B6':'live','\u23F8':'paused'}
SUPERSEDE = re.compile(r'(do NOT credit|no longer|overtaken|supersed|retract|withdraw|'
                       r'was wrong|is wrong|corrects|replaces|inverts|kills|dead\b|'
                       r'stop being quoted|not a property)', re.I)
SHA = re.compile(r'`([0-9a-f]{7,40})`')
NUM = re.compile(r'\b\d+(?:\.\d+)?\s*(?:%|ms|s\b|GiB|MiB|bpw|of \d+)')

def files():
    out = sorted(glob.glob(os.path.join(ROOT, "research", "**", "*.md"), recursive=True))
    if MEM:
        out += sorted(glob.glob(os.path.join(MEM, "*.md")))
    return out

def title_of(text):
    m = re.search(r'\*\*(.+?)\*\*', text)
    if m and len(m.group(1)) > 12:
        return m.group(1).strip()
    s = re.split(r'(?<=[.!?])\s', text.strip(), maxsplit=1)[0]
    return s.strip()

def clean(s):
    return re.sub(r'\s+', ' ', s).strip()

rows, dupes, refs_only = [], collections.defaultdict(list), collections.Counter()
range_only = collections.Counter()
mentioned = set()
seen = {}

for path in files():
    try:
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
    except ValueError:   # different drive (memory lives on C:)
        rel = "memory/" + os.path.basename(path)
    try:
        lines = open(path, encoding="utf-8").read().split("\n")
    except Exception as e:
        print(f"!! unreadable {rel}: {e}", file=sys.stderr); continue
    i = 0
    while i < len(lines):
        line = lines[i]
        m = DEF.match(line) or DEF_HEAD.match(line) or DEF_MARK.match(line) or DEF_BARE.match(line)
        if not m:
            for a, b in RANGE.findall(line):
                a, b = int(a), int(b)
                if 0 < b - a < 200:
                    for x in range(a, b + 1):
                        range_only[x] += 1; mentioned.add(x)
            for r in REF.finditer(line):
                refs_only[int(r.group(1))] += 1; mentioned.add(int(r.group(1)))
            i += 1; continue
        n = int(m.group("n"))
        is_head  = line.lstrip().startswith("#")
        is_table = line.lstrip().startswith("|")
        body = [line[m.end():]]
        if not is_table:                       # block style: run to blank line / next def
            j = i + 1
            if is_head:
                while j < len(lines) and not lines[j].strip():
                    j += 1
            while j < len(lines) and lines[j].strip() and not (DEF.match(lines[j]) or DEF_HEAD.match(lines[j]) or DEF_MARK.match(lines[j]) or DEF_BARE.match(lines[j])):
                if re.match(r'^#{1,6}\s', lines[j]) or lines[j].lstrip().startswith("|"):
                    break
                body.append(lines[j]); j += 1
            i = j
        else:
            body = [line.strip().strip("|")]
            i += 1
        text = clean(" ".join(body))
        mentioned.add(n)
        for a, b in RANGE.findall(text):
            a, b = int(a), int(b)
            if 0 < b - a < 200:
                for x in range(a, b + 1):
                    range_only[x] += 1; mentioned.add(x)
        if len(text) < 20:
            continue
        st = next((v for k, v in STATUS.items() if k in text), "")
        cites = sorted({int(x) for x in REF.findall(text)} - {n})
        row = dict(n=n, doc=rel, line=i if is_table else i - len(body) + 1,
                   status=st, title=title_of(text)[:180],
                   supersedes=";".join(f"F{c}" for c in cites) if SUPERSEDE.search(text) else "",
                   cites=";".join(f"F{c}" for c in cites),
                   sha=";".join(sorted(set(SHA.findall(text))))[:120],
                   measures=";".join(sorted(set(NUM.findall(text))))[:120],
                   chars=len(text))
        if n in seen:
            dupes[n].append(rel)
        else:
            seen[n] = rel
        rows.append(row)

rows.sort(key=lambda r: (r["n"], r["doc"]))
with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t")
    w.writeheader(); w.writerows(rows)

# ---------- report ----------
nums = sorted({r["n"] for r in rows})
hi = max(nums)
gaps = [x for x in range(1, hi + 1) if x not in nums]
print(f"docs scanned            {len(files())}")
print(f"definitions parsed      {len(rows)}")
print(f"distinct F-numbers      {len(nums)}   (F{min(nums)}..F{hi})")
print(f"duplicate definitions   {len(dupes)}  {'' if not dupes else list(dupes)[:12]}")
print(f"missing from 1..{hi}      {len(gaps)}")
if gaps:
    rr, s = [], None
    for x in gaps + [None]:
        if s is None: s = p = x; continue
        if x == p + 1: p = x; continue
        rr.append(f"F{s}" if s == p else f"F{s}-F{p}"); s = p = x
    print(f"  gap ranges            {' '.join(rr[:14])}{' ...' if len(rr) > 14 else ''}")
undef   = [k for k in mentioned if k not in seen and 0 < k <= hi]
rng     = sorted(k for k in undef if range_only.get(k))
cite    = sorted(k for k in undef if not range_only.get(k))
absent  = [x for x in range(1, hi + 1) if x not in mentioned]
print()
print("COVERAGE of the F1..F%d space" % hi)
print(f"  defined individually  {len(seen):>5}   parseable as its own claim")
print(f"  range-covered only    {len(rng):>5}   only ever inside 'F206-F212'")
print(f"  cited, never defined  {len(cite):>5}   referenced but no definition anywhere")
print(f"  never mentioned       {len(absent):>5}   number issued but no surviving text")
print(f"  ---------------------------")
print(f"  accounted for         {len(seen)+len(rng)+len(cite):>5} of {hi}")
print()
print("status marker         count")
for k, v in collections.Counter(r["status"] or "(none)" for r in rows).most_common():
    print(f"  {k:<18} {v:>5}")
print()
print(f"with a commit sha     {sum(1 for r in rows if r['sha']):>5}")
print(f"with a measured value {sum(1 for r in rows if r['measures']):>5}")
print(f"citing another F      {sum(1 for r in rows if r['cites']):>5}")
print(f"retraction language   {sum(1 for r in rows if r['supersedes']):>5}")
print(f"median length (chars) {sorted(r['chars'] for r in rows)[len(rows)//2]:>5}")
print()
print("top docs by definitions")
for d, c in collections.Counter(r["doc"] for r in rows).most_common(10):
    print(f"  {c:>4}  {d}")
print(f"\nwrote {OUT}")
