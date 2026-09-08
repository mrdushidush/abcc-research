#!/usr/bin/env python3
"""fread.py - extraction probe: pull every finding definition out of the prose.

Reads research/**/*.md and the memory dir, separates finding DEFINITIONS from
mere REFERENCES, and reports whether the existing prose is machine-readable
enough to back a ledger. Derived-only: writes a TSV, never touches a source.

The grammar itself lives in `fparse.py` so this probe and `fledger.py` cannot
drift apart. This file's output is a fixed point: F668-F670 quote its coverage
block, so a change here that moves those numbers is a regression, not a tidy-up.
"""
import re, sys, os, csv, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fparse import (REF, RANGE, SHA, NUM, STATUS, SUPERSEDE,
                    title_of, md_files, relpath, walk)

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
MEM  = sys.argv[2] if len(sys.argv) > 2 else None
OUT  = sys.argv[3] if len(sys.argv) > 3 else "findings.tsv"

def files():
    return md_files(ROOT, MEM)

rows, dupes, refs_only = [], collections.defaultdict(list), collections.Counter()
range_only = collections.Counter()
mentioned = set()
seen = {}

for path in files():
    rel = relpath(path, ROOT)
    try:
        lines = open(path, encoding="utf-8").read().split("\n")
    except Exception as e:
        print(f"!! unreadable {rel}: {e}", file=sys.stderr); continue
    for ev in walk(lines):
        if ev[0] == 'plain':
            line = ev[2]
            for a, b in RANGE.findall(line):
                a, b = int(a), int(b)
                if 0 < b - a < 200:
                    for x in range(a, b + 1):
                        range_only[x] += 1; mentioned.add(x)
            for r in REF.finditer(line):
                refs_only[int(r.group(1))] += 1; mentioned.add(int(r.group(1)))
            continue
        _, n, line_no, is_table, text, nbody = ev
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
        row = dict(n=n, doc=rel, line=line_no,
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
