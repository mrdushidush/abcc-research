#!/usr/bin/env python3
"""mojibake.py - text whose bytes were decoded once too few times, found.

Double-encoded UTF-8: a character's UTF-8 bytes were read back as latin-1 or
cp1252 and then encoded as UTF-8 again, so the file holds `C3 B0 C2 9F C2 9A
C2 A8` where it means the four bytes `F0 9F 9A A8` and renders as `ð¨`
instead of a siren. Nothing compiles differently, no tool complains, and the
file looks fine in a diff that is not looking for it. It sat in abcc's
`StateEndings` doc block for nine days and in seventeen `od` task files for ten.

  TRY BOTH CODECS OR MISS THE CLASS. The first version of this looked only for
the latin-1 round trip, whose characters stay inside U+0080..U+00FF, and
reported 5 occurrences across both repositories. cp1252 maps 0x9F to U+0178 and
0x9A to U+0161, OUTSIDE that range, so a `[\u0080-\u00ff]+` run breaks in the
middle of every cp1252 case and finds none of them. With both codecs the count
was 55. An instrument that under-reports looks exactly like a clean result.

  AND IT OVER-REPORTS, SO A HUMAN READS EVERY HIT. `8.71x-17.66x` written with
a real multiplication sign and an en dash is `D7 96` in cp1252, which is valid
UTF-8 for a Hebrew zayin. It is ordinary text. There is no way to tell that from
a real hit by arithmetic -- only by reading the line -- so this prints and never
repairs.

  DO NOT REPAIR A RECORDED ARTIFACT. `research/spikes/w6-judge/census-out.txt`
holds 23 of these and keeps them: it is what a program printed, and editing a
record to make it prettier is falsifying it. `--check` asserts those 23 are
still there, which is one control doing two jobs -- the detector still detects,
and nobody has tidied the artifact.

Usage:
    mojibake.py <root> [--ext .rs,.md,.toml] [--quiet]
    mojibake.py --check
"""

import argparse
import pathlib
import sys

# cp1252's own assignments for 0x80-0x9F, which is the whole reason a run cannot
# be defined as "characters in U+0080..U+00FF".
CP1252_EXTRA = set(
    "\u20ac\u201a\u0192\u201e\u2026\u2020\u2021\u02c6\u2030\u0160"
    "\u2039\u0152\u017d\u2018\u2019\u201c\u201d\u2022\u2013\u2014"
    "\u02dc\u2122\u0161\u203a\u0153\u017e\u0178"
)
DEFAULT_EXT = ".rs,.md,.toml,.py,.txt,.tsv,.json"
SKIP_DIRS = {"target", ".git", "node_modules", "__pycache__"}

# The counts `--check` pins, measured 2026-09-14 after abcc 2453d92 and
# abcc-research d849131 repaired everything repairable.
EXPECT = {"census-out.txt": 23, "w4-estimator/README.md": 1}


def is_run_char(c):
    return 0x80 <= ord(c) <= 0xFF or c in CP1252_EXTRA


def runs(line):
    """Maximal stretches that could be a re-encoded character's bytes."""
    out, cur = [], []
    for c in line + "\0":
        if c != "\0" and is_run_char(c):
            cur.append(c)
            continue
        if cur:
            out.append("".join(cur))
            cur = []
    return out


def demangle(s):
    """What `s` means if it is double-encoded, else None."""
    for codec in ("cp1252", "latin-1"):
        try:
            dec = s.encode(codec).decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            continue
        # A real hit shrinks, and does not land back in the C1 block -- which
        # would mean the round trip mangled legitimate text rather than
        # recovering it.
        if len(dec) < len(s) and all(not (0x80 <= ord(c) <= 0x9F) for c in dec):
            return dec
    return None


def scan(root, exts):
    hits = []
    for p in sorted(pathlib.Path(root).rglob("*")):
        if not p.is_file() or p.suffix not in exts:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for run in runs(line):
                dec = demangle(run)
                if dec is not None:
                    hits.append((p, i, run, dec, line.strip()))
    return hits


def report(hits, quiet):
    print(f"{len(hits)} occurrence(s) in {len({h[0] for h in hits})} file(s)")
    for p, i, run, dec, ctx in hits:
        print(f"  {p}:{i}  {run!r} -> {dec!r}")
        if not quiet:
            print(f"    {ctx[:100]}")


def check():
    """Both repositories, against the counts the repair left behind.

    ⚠ The roots are this file's own neighbours rather than arguments, so the
    control cannot be pointed somewhere convenient and made to pass.
    """
    research = pathlib.Path(__file__).resolve().parents[2]
    abcc = research.parent / "abcc"
    exts = set(DEFAULT_EXT.split(","))
    failures = []

    hits = scan(abcc / "crates", exts)
    if hits:
        failures.append(f"abcc/crates: expected 0, found {len(hits)}: {hits[:3]}")

    found = {}
    for p, _, _, _, _ in scan(research / "research", exts):
        for key in EXPECT:
            if p.as_posix().endswith(key):
                found[key] = found.get(key, 0) + 1
    for key, want in EXPECT.items():
        got = found.get(key, 0)
        if got != want:
            # 🚨 Too FEW is the interesting direction: it means somebody
            # repaired a recorded artifact, or this detector stopped working.
            failures.append(f"{key}: expected {want}, found {got}")

    corpus = scan(research / "corpus", exts)
    if corpus:
        failures.append(f"corpus: expected 0, found {len(corpus)}")

    for line in failures:
        print(f"FAIL  {line}")
    if failures:
        return 1
    print(f"ok  abcc/crates 0 · corpus 0 · {' · '.join(f'{k} {v}' for k, v in EXPECT.items())}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", nargs="?", help="directory to scan")
    ap.add_argument("--ext", default=DEFAULT_EXT, help="comma-separated suffixes")
    ap.add_argument("--quiet", action="store_true", help="one line per hit")
    ap.add_argument("--check", action="store_true", help="assert the pinned counts")
    args = ap.parse_args()
    if args.check:
        return check()
    if not args.root:
        ap.error("a root, or --check")
    hits = scan(args.root, set(args.ext.split(",")))
    report(hits, args.quiet)
    # ▶ Never a non-zero exit on a hit: over-reporting is a property of this
    # detector, so a hit is something to READ and not something to fail a build.
    return 0


if __name__ == "__main__":
    sys.exit(main())
