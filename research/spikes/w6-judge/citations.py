#!/usr/bin/env python3
"""W6 item 7 — the free rung for a document.

Item 4's winner on code was the rung that costs nothing: *did the change touch a
source file*. The brief asks the same question about the artifact with no test —
documentation and review output — so this is the free rung for prose.

A research document here is almost entirely claims, and most claims are not
checkable by a machine. But three kinds are addresses rather than assertions, and
this corpus is made of them:

  finding      `F193` must have exactly one definition heading in the corpus.
  question     `OQ-W6-9` must have a definition row in some workstream's table.
  citation     `orchestrator.py:172-285` must name a file that exists, and that
               file must have at least that many lines.

Nothing here reads meaning. It checks that the *addresses* resolve, which is the
part a machine can own — and it is run over the real corpus: 43 authored
documents, 1.5 MB of model-written prose that nobody has ever mechanically
checked, citing four repositories.

Two calibration notes, both of them mistakes this probe made first:

  * The corpus is not `research/*.md`. Findings F1–F61 are defined in the harness
    crates' READMEs, with `F35.` rather than `F35 —` as the separator. A checker
    run over the wrong corpus reported 40 dangling references that were all its
    own.
  * A bare basename (`orchestrator.py:43`) is not an address until a resolution
    rule is fixed. The rule here: an exact relative path wins; otherwise a
    basename unique within exactly one of the four trees wins; anything else is
    reported `ambiguous` rather than guessed.

    python citations.py
"""

from __future__ import annotations

import collections
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]

DONORS = {
    "v1": pathlib.Path(r"D:\dev\agent-battle-command-center"),
    "bcf": pathlib.Path(r"D:\dev\battle-command-forge"),
    "claudette": pathlib.Path(r"D:\dev\claudette"),
}

# Authored prose only. Preserved agent workdirs, corpus fixtures, build outputs
# and the staging copy of the Q56 import are documents nobody wrote as documents.
EXCLUDE = ("/runs/", "/target/", "/node_modules/", "/.pytest_cache/",
           "/.mypy_cache/", "/q56-staging/", "/corpus/suites/", "/.git/")

SKIP_DIRS = {".git", "target", "node_modules", "__pycache__", "dist", "build",
             ".venv", "venv", ".pytest_cache", ".mypy_cache", ".next"}

# FIVE conventions define a finding in this corpus, and the checker's yield is a
# measurement of how many of them it knows: with two it reported 40 dangling
# references and every one was its own, with three 21, with four 12. The five:
#   `### F158 — ...`   `### 🚨 F158 — ...`   `### F35. ...`
#   `## 4. F54 — ...`  `**F41. ...**`
# The last is a bold paragraph rather than a heading and is how the W8 documents
# define F41-F48; the fourth is a numbered section. At most one marker may
# precede the number, so a heading that merely *mentions* a finding does not
# count as defining one.
FINDING_DEF = re.compile(
    r"^(?:#{2,6}\s+(?:\d+\.\s+)?(?:[^\w\s]\S*\s+)?|\*\*)F(\d+)\s*[—\-.:]", re.M)
FINDING_REF = re.compile(r"\bF(\d{1,3})\b")
# Two conventions for an open question — a table row (W3, W6, W11) and a bullet
# list item (W5) — and the table row may carry a status marker before the id.
OQ_DEF = re.compile(
    r"^(?:\|\s*(?:[^\w\s]\S*\s+)?|[-*]\s+(?:~~)?(?:\*\*)?)"
    r"(OQ-W\d+-\d+)\s*(?:\||[—\-])", re.M)
OQ_REF = re.compile(r"\b(OQ-W\d+-\d+)\b")

# A citation introducing a fenced block is a *quotation*, and a quotation is
# checkable against the file in a way an address is not — but only when the block
# really is a quotation of that file. Two guards, both of them added after the
# probe manufactured defects without them: the citation must be the only one in
# the two lines above the fence, and the fence's language tag must match the
# cited file's extension. Without the tag guard, a block of illustrative *output*
# under a `.ts` citation and a block labelled `mission.rs:1139` under a
# `verifier.rs` citation were both reported as documentation errors.
FENCE = re.compile(r"```([a-zA-Z0-9_+-]*)\n(.*?)```", re.S)
TAGS = {
    "rs": {"rust"}, "py": {"python", "py"}, "ts": {"ts", "typescript"},
    "tsx": {"tsx", "typescript"}, "js": {"js", "javascript"},
    "jsx": {"jsx", "javascript"}, "mjs": {"js", "javascript", "mjs"},
    "sh": {"sh", "bash", "shell"}, "toml": {"toml"}, "json": {"json"},
    "md": {"md", "markdown"}, "yml": {"yaml", "yml"}, "yaml": {"yaml", "yml"},
}
CITE = re.compile(
    r"(?P<path>(?:[A-Za-z0-9_.\-]+/)*[A-Za-z0-9_.\-]+"
    r"\.(?:rs|py|ts|tsx|js|jsx|mjs|sh|toml|json|md|yml|yaml))"
    r":(?P<a>\d+)(?:-(?P<b>\d+))?")


def git_head(d: pathlib.Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(d), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip() or "?"
    except Exception:  # noqa: BLE001
        return "?"


def docs(root: pathlib.Path = None) -> list[pathlib.Path]:
    return sorted(p for p in (root or REPO).rglob("*.md")
                  if not any(x in p.as_posix() for x in EXCLUDE))


def index(root: pathlib.Path):
    by_name = collections.defaultdict(list)
    by_rel = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        by_name[p.name].append(p)
        by_rel[rel.as_posix()] = p
    return by_name, by_rel


def read(p: pathlib.Path) -> str:
    """A document that cannot be opened is not a document. v1's donor tree has a
    `workspace/README.md` this account cannot read; skipping it is a classified
    outcome, not a silent zero."""
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def line_count(p: pathlib.Path) -> int:
    try:
        with p.open("rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return -1


def resolve(path: str, idx):
    """(status, tree, file). See the module docstring for the rule."""
    exact = [(k, v[1][path]) for k, v in idx.items() if path in v[1]]
    if len(exact) == 1:
        tree, f = exact[0]
        # A bare basename that happens to be an exact root-relative path is NOT
        # resolved. `Cargo.toml:57` in a workspace means some crate's manifest;
        # matching it to the 23-line root manifest produced five "past EOF"
        # citations in the successor's documentation that were the rule's error,
        # not the document's.
        if "/" not in path and len(idx[tree][0].get(path, [])) > 1:
            return "ambiguous", None, None
        return "resolved", tree, f
    if len(exact) > 1:
        return "ambiguous", None, None
    base = path.split("/")[-1]
    hits = {k: v[0].get(base, []) for k, v in idx.items()}
    hits = {k: v for k, v in hits.items() if v}
    if not hits:
        return "no such file", None, None
    if len(hits) == 1:
        (tree, files), = hits.items()
        if len(files) == 1:
            return "resolved", tree, files[0]
    return "ambiguous", None, None


def quotations(text: str):
    """(path, a, b, block) for every fence whose attribution is unambiguous.

    Attribution runs from the FENCE backwards, not from the citation forwards.
    The forward rule — "the next fence within three lines" — attributed a block
    labelled `mission.rs:1139` to a `verifier.rs:26-36` citation two lines above
    it and called the document wrong; 12 of 21 "mismatches" were that bug. The
    rule here is the corpus's actual convention: the fence is introduced by the
    two lines above it, and exactly one citation may appear in them.
    """
    for m in FENCE.finditer(text):
        head = text[:m.start()].rstrip("\n")
        intro = "\n".join(head.splitlines()[-2:])
        hits = list(CITE.finditer(intro))
        if len(hits) != 1:
            continue
        c = hits[0]
        ext = c.group("path").rsplit(".", 1)[-1].lower()
        if m.group(1).lower() not in TAGS.get(ext, set()):
            continue
        a = int(c.group("a"))
        b = int(c.group("b")) if c.group("b") else a
        yield c.group("path"), a, b, m.group(2)


def quote_matches(block: str, target: pathlib.Path) -> tuple[bool, int, int]:
    """Do the block's non-trivial lines appear, in order, in the file?

    Whitespace-insensitive on the left, because documents re-indent quotations,
    and lines shorter than 8 characters are skipped — a lone `}` matches
    everything and would make the check vacuous. Elisions (`...`, `…`) are
    skipped rather than failing the block, since they are the corpus's own
    convention for cutting a quotation.
    """
    try:
        src = [l.strip() for l in
               target.read_text(encoding="utf-8", errors="replace").splitlines()]
    except OSError:
        return False, 0, 0
    want = [l.strip() for l in block.splitlines()]
    want = [l for l in want
            if len(l) >= 8 and l not in ("...", "…") and not l.endswith(("...", "…"))]
    if not want:
        return False, 0, 0
    i, hit = 0, 0
    for line in want:
        j = next((k for k in range(i, len(src)) if src[k] == line), None)
        if j is None:
            continue
        hit += 1
        i = j + 1
    return hit == len(want), hit, len(want)


def donor_pass(name: str, root: pathlib.Path) -> dict:
    """The same address check on a donor's own documentation, against itself.

    An external comparison for the yield: these are hand-maintained corpora of a
    project documenting its own code, where a stale citation is a real drift
    signal rather than a cross-repository resolution problem.
    """
    idx = {name: index(root)}
    cites, seen, quoted = [], set(), []
    for p in docs(root):
        for m in CITE.finditer(read(p)):
            path, a = m.group("path"), int(m.group("a"))
            b = int(m.group("b")) if m.group("b") else a
            if (path, a, b) in seen:
                continue
            seen.add((path, a, b))
            status, tree, f = resolve(path, idx)
            row = {"path": path, "a": a, "b": b, "status": status}
            if status == "resolved":
                n = line_count(f)
                row["lines"] = n
                row["status"] = "ok" if b <= n else "past EOF"
            cites.append(row)
    for p in docs(root):
        for path, a, b, block in quotations(
                read(p)):
            status, tree, f = resolve(path, idx)
            if status != "resolved":
                quoted.append({"path": path, "verdict": "unresolvable"})
                continue
            ok, hit, total = quote_matches(block, f)
            quoted.append({"path": path, "a": a, "b": b, "hit": hit, "lines": total,
                           "verdict": ("matches" if ok else
                                       "vacuous" if total == 0 else "differs")})
    return {
        "head": git_head(root), "docs": len(docs(root)),
        "unique_citations": len(cites),
        "by_status": dict(collections.Counter(c["status"] for c in cites)),
        "quotations": len(quoted),
        "quote_status": dict(collections.Counter(c["verdict"] for c in quoted)),
        "bad": [c for c in cites if c["status"] not in ("ok",)][:40],
    }


def main():
    trees = {"self": REPO} | DONORS
    heads = {k: git_head(v) for k, v in trees.items()}
    idx = {k: index(v) for k, v in trees.items()}

    corpus = {p: read(p) for p in docs()}

    # ── findings ─────────────────────────────────────────────────────
    defined = collections.defaultdict(list)
    refs = collections.Counter()
    ref_sites = collections.defaultdict(set)
    for p, t in corpus.items():
        rel = p.relative_to(REPO).as_posix()
        for m in FINDING_DEF.finditer(t):
            defined[int(m.group(1))].append(rel)
        for m in FINDING_REF.finditer(t):
            n = int(m.group(1))
            refs[n] += 1
            ref_sites[n].add(rel)
    dangling = {n: {"count": c, "docs": sorted(ref_sites[n])}
                for n, c in refs.items() if n not in defined}
    twice = {n: v for n, v in defined.items() if len(v) > 1}

    # ── open questions ───────────────────────────────────────────────
    oq_def = collections.defaultdict(list)
    oq_refs = collections.Counter()
    for p, t in corpus.items():
        rel = p.relative_to(REPO).as_posix()
        for m in OQ_DEF.finditer(t):
            oq_def[m.group(1)].append(rel)
        for m in OQ_REF.finditer(t):
            oq_refs[m.group(1)] += 1
    oq_dangling = {q: c for q, c in oq_refs.items() if q not in oq_def}

    # ── file:line citations ──────────────────────────────────────────
    cites, seen = [], set()
    for p, t in corpus.items():
        doc = p.relative_to(REPO).as_posix()
        for m in CITE.finditer(t):
            path, a = m.group("path"), int(m.group("a"))
            b = int(m.group("b")) if m.group("b") else a
            if (path, a, b) in seen:
                continue
            seen.add((path, a, b))
            status, tree, f = resolve(path, idx)
            row = {"doc": doc, "path": path, "a": a, "b": b,
                   "status": status, "tree": tree}
            if status == "resolved":
                n = line_count(f)
                row["lines"] = n
                row["status"] = "ok" if b <= n else "past EOF"
            cites.append(row)

    by_status = collections.Counter(c["status"] for c in cites)

    # ── quotations: the stronger free rung ───────────────────────────
    quoted = []
    for p, t in corpus.items():
        doc = p.relative_to(REPO).as_posix()
        for path, a, b, block in quotations(t):
            status, tree, f = resolve(path, idx)
            if status != "resolved":
                quoted.append({"doc": doc, "path": path, "a": a, "b": b,
                               "verdict": "unresolvable", "tree": tree})
                continue
            ok, hit, total = quote_matches(block, f)
            quoted.append({"doc": doc, "path": path, "a": a, "b": b, "tree": tree,
                           "verdict": ("matches" if ok else
                                       "vacuous" if total == 0 else "differs"),
                           "hit": hit, "lines": total})
    q_status = collections.Counter(c["verdict"] for c in quoted)
    result = {
        "heads": heads,
        "docs": len(corpus),
        "bytes": sum(len(t.encode()) for t in corpus.values()),
        "findings": {
            "defined": len(defined),
            "headings": sum(len(v) for v in defined.values()),
            "distinct_referenced": len(refs),
            "total_references": sum(refs.values()),
            "dangling": {str(k): v for k, v in sorted(dangling.items())},
            "defined_twice": {str(k): v for k, v in sorted(twice.items())},
        },
        "open_questions": {
            "defined": len(oq_def), "distinct_referenced": len(oq_refs),
            "total_references": sum(oq_refs.values()),
            "dangling": oq_dangling,
        },
        "citations": {"unique": len(cites), "by_status": dict(by_status),
                      "quoted": len(quoted), "quote_status": dict(q_status),
                      "bad": [c for c in cites if c["status"] != "ok"],
                      "quotations": quoted},
        "donor_self_citations": {k: donor_pass(k, v) for k, v in DONORS.items()},
    }
    (HERE / "citations-results.json").write_text(
        json.dumps(result, indent=1), encoding="utf-8", newline="\n")

    print(f"corpus: {result['docs']} authored documents, {result['bytes']:,} bytes")
    print(f"heads: {heads}\n")
    f = result["findings"]
    print(f"findings: {f['defined']} defined by {f['headings']} headings; "
          f"{f['distinct_referenced']} distinct referenced over "
          f"{f['total_references']} references")
    print(f"  dangling: {len(f['dangling'])} -> "
          f"{sorted(f['dangling'], key=int)}")
    print(f"  defined in two documents: {f['defined_twice']}")
    q = result["open_questions"]
    print(f"\nopen questions: {q['defined']} defined, {q['distinct_referenced']} "
          f"referenced over {q['total_references']} references")
    print(f"  dangling: {len(q['dangling'])} -> {sorted(q['dangling'])}")
    c = result["citations"]
    print(f"\nfile:line citations: {c['unique']} unique")
    for k, v in sorted(c["by_status"].items(), key=lambda kv: -kv[1]):
        print(f"  {k:<14} {v:>4}  ({100*v/c['unique']:.0f}%)")
    print(f"\nof the resolved ones, {c['quoted']} quote the code they cite:")
    for k, v in sorted(c["quote_status"].items(), key=lambda kv: -kv[1]):
        print(f"  {k:<14} {v:>4}")
    print("\nthe donors' own documentation, each resolved against its own tree:")
    for k, v in result["donor_self_citations"].items():
        print(f"  {k:<10} {v['head']}  {v['docs']:>3} docs  "
              f"{v['unique_citations']:>4} citations  {v['by_status']}")
        print(f"  {'':<10} {v['quotations']:>4} quotations  {v['quote_status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
