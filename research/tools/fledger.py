#!/usr/bin/env python3
"""fledger.py - the findings ledger: a DERIVED SQLite index over the prose.

    python research/tools/fledger.py build [--memory DIR]
    python research/tools/fledger.py show F673
    python research/tools/fledger.py search "clippy"
    python research/tools/fledger.py gaps | contested | candidates | chain F655

THE RULING THIS FILE IMPLEMENTS (settled, do not re-derive):

  * **Markdown stays the source of truth.** This database is regenerable from
    the prose at any time, and that is the whole safety argument - an index that
    can be rebuilt can never be the thing that loses data. Never let it become
    the only copy of anything, and never write back to a document from here.
  * **Supersession is the ONE field that is AUTHORED.** F669 measured the
    obvious keyword rule at +76% over the truth (67 asserted edges against 38
    real ones, one row claiming ten) because it degenerates into *(a retraction
    word appears in this block)* x *(every finding the block cites)*, and
    findings cite each other in 289 of 999 rows. The corpus also argues in the
    NEGATIVE - "F531 is not retracted", "F83 is not retracted and is not the
    authority here" - which no keyword rule resolves in either direction.
    So the heuristic is kept in `edge_candidate`, never in `edge`, and `state`
    is computed only from the authored file.
  * **`state` is DERIVED, never authored.** An authored state and an authored
    edge are two things that can disagree.

The grammar lives in `fparse.py`; `fread.py` is the coverage probe whose numbers
F668-F670 quote. All three share one definition of what a finding looks like.
"""
import argparse, collections, csv, os, re, sqlite3, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fparse import (REF, RANGE, SHA, NUM, STATUS, SUPERSEDE,
                    title_of, md_files, relpath, walk)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DEFAULT_MEM = os.path.expanduser(
    "~/.claude/projects/D--dev-ABCC-20-powerd-by-claudette/memory")
DEFAULT_DB = "research/findings.sqlite"
DEFAULT_EDGES = "research/findings-authored.tsv"
# `answers` is not decoration: the corpus says "F606 IS ANSWERED", "F637 is
# ANSWERED", "F38 IS ANSWERED" far more often than it says "superseded", and an
# answered finding is resolved, not wrong. `not-an-edge` is the other half of
# F669's lesson - the prose argues in the negative ("This does not retract
# F531"), and a negative has to be storable or the next heuristic re-asserts it.
EDGE_KINDS = ("supersedes", "retracts", "refines", "answers")
NON_EDGE = "not-an-edge"
# The second authored fact, and the only other one: WHICH of a finding's several
# definitions is the real one. Derived date-then-length gets 664 of 673 right on
# its own; this pins the rest, so a contested row becomes a decision on the
# record rather than a flag nobody ever clears.
CANONICAL = "canonical"

# A definition block may carry its own edge, which is the convention that makes
# this cheap going forward: one exact line, on the finding that does the work.
#     Supersedes: F649 (the door was taken with nobody offering it)
INLINE = re.compile(r'(?:^|\s)(Supersedes|Retracts|Refines|Answers|Not-an-edge):\s*'
                    r'F(\d{1,4})\s*(?:\(([^)]*)\))?', re.I)


# ------------------------------------------------------------------ classing
def doc_class(doc):
    """research < spike < decisions < memory. The winner supplies the text.

    A spike README is working notes and the research document is the write-up,
    so when the same W8 work is written up twice on the same day the research
    doc is the home. Safe because **no finding is defined only in a spike** -
    checked, 11 spike definitions, 0 exclusive. An ADR *consumes* findings and
    cites them in passing, which is why decisions sit below both.
    """
    if doc.startswith("memory/"):
        return "memory"
    if "/decisions/" in doc:
        return "decisions"
    if "/spikes/" in doc:
        return "spike"
    return "research"


CLASS_RANK = {"research": 1, "spike": 2, "decisions": 3, "memory": 4}


def workstream(doc):
    """W6, ADR, DEBUG, CONSOLE, spike, memory - taken from where it lives."""
    if doc.startswith("memory/"):
        return "memory"
    if "/decisions/" in doc:
        return "ADR"
    if "/spikes/" in doc:
        parts = doc.split("/")
        return "spike:" + parts[parts.index("spikes") + 1]
    base = os.path.basename(doc)
    m = re.match(r'^([A-Za-z]+\d*)-', base)
    return m.group(1).upper() if m else base.replace(".md", "")


# --------------------------------------------------------------- git dating
def blame_dates(root, docs):
    """{(doc, line): (iso_date, sha)} for tracked files. Untracked -> absent.

    The memory directory lives under ~/.claude and is not a git repository, so
    memory-sourced findings carry no date. That is recorded, not papered over.
    """
    out = {}
    for doc in docs:
        path = os.path.join(root, doc)
        if doc.startswith("memory/") or not os.path.exists(path):
            continue
        try:
            raw = subprocess.run(["git", "blame", "--line-porcelain", "--", doc],
                                 cwd=root, capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=120)
        except Exception:
            continue
        if raw.returncode != 0:
            continue
        sha = lineno = when = None
        for ln in raw.stdout.split("\n"):
            m = re.match(r'^([0-9a-f]{40}) \d+ (\d+)', ln)
            if m:
                sha, lineno = m.group(1)[:7], int(m.group(2))
            elif ln.startswith("author-time "):
                when = int(ln.split()[1])
            elif ln.startswith("\t") and lineno is not None:
                if when:
                    out[(doc, lineno)] = (
                        time.strftime("%Y-%m-%d", time.localtime(when)), sha)
                lineno = None
    return out


# --------------------------------------------------------------- detectors
# TWO candidate detectors, and the difference between them is the whole of F669.
#
#   co-occurrence: a retraction word anywhere in a block x every finding it
#                  cites. Measured here at 79 pairs for ~6 real edges.
#   directed:      the finding number must be the grammatical OBJECT of a
#                  correction verb, or the SUBJECT of a correction predicate,
#                  inside one line. Measured here at 34 hits for ~17 real edges.
#
# Neither is ever written to `edge`. They are reading prompts.
DIRECTED = [
    (r'(?:corrects?|supersed\w*|overtak\w*|retracts?|replaces?|withdraw\w*|'
     r'revises?|repeals?|kills?|invalidat\w*|answers?|closes?)\s+'
     r'(?:the\s+)?(?:findings?\s+)?F(\d{1,4})', 'verb->F'),
    (r'F(\d{1,4})\s+(?:is|was|are|were|has been|have been)\s+(?:now\s+)?'
     r'(?:\*\*)?(?:wrong|retracted|superseded|overtaken|corrected|answered|'
     r'dead|obsolete|withdrawn|repealed|invalid|repaired)', 'F->predicate'),
    (r'F(\d{1,4})\s+(?:no longer|does not hold|does not stand|'
     r'is out of date|must not be quoted)', 'no-longer'),
    (r'(?:do\s+NOT\s+credit|stop\s+quoting|do\s+not\s+quote)\s+F(\d{1,4})',
     'do-not-quote'),
]
# The corpus argues in the negative, and a hit inside one of these is NOT a
# candidate - it is evidence that somebody already considered and rejected it.
NEGATED = re.compile(
    r'F\d{1,4}\s+(?:is|was)\s+(?:\*\*)?(?:not|NOT)\s+'
    r'(?:retracted|superseded|wrong|dead)|does not retract F\d|'
    r'does\s+not\s+close\s+F\d', re.I)


# ------------------------------------------------------------------ scanning
def scan(root, mem):
    defs, cites, ranges, refs = [], [], collections.Counter(), collections.Counter()
    mentioned = set()
    inline, directed = [], []
    for path in md_files(root, mem):
        doc = relpath(path, root)
        try:
            lines = open(path, encoding="utf-8").read().split("\n")
        except Exception as e:
            print(f"!! unreadable {doc}: {e}", file=sys.stderr)
            continue
        owner, cur = {}, None
        for ev in walk(lines):
            if ev[0] == "def":
                cur = ev[1]
                for k in range(ev[2], ev[2] + max(ev[5], 1)):
                    owner[k] = cur
            else:
                owner[ev[1]] = cur
        fenced = False
        for i, line in enumerate(lines, 1):
            # 🚨 A fenced block is an EXAMPLE, not an assertion. Caught the hard
            # way: LEDGER-P1's own code block showing the convention
            # (`Supersedes: F649 (...)`) was read as a real edge and moved F649
            # to `superseded` in the very document warning about F670's trap.
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue
            for m in INLINE.finditer(line):
                inline.append(dict(src=owner.get(i), dst=int(m.group(2)),
                                   kind=m.group(1).lower(),
                                   reason=(m.group(3) or "").strip(),
                                   evidence="%s:%d" % (doc, i)))
            for pat, shape in DIRECTED:
                for m in re.finditer(pat, line, re.I):
                    if NEGATED.search(line[max(0, m.start() - 70):m.end() + 70]):
                        continue
                    dst = int(m.group(1))
                    if owner.get(i) != dst:
                        directed.append((owner.get(i), dst, doc, i, shape))
        for ev in walk(lines):
            if ev[0] == "plain":
                line = ev[2]
                for a, b in RANGE.findall(line):
                    a, b = int(a), int(b)
                    if 0 < b - a < 200:
                        for x in range(a, b + 1):
                            ranges[x] += 1
                            mentioned.add(x)
                for r in REF.finditer(line):
                    refs[int(r.group(1))] += 1
                    mentioned.add(int(r.group(1)))
                continue
            _, n, line_no, is_table, text, _ = ev
            mentioned.add(n)
            for a, b in RANGE.findall(text):
                a, b = int(a), int(b)
                if 0 < b - a < 200:
                    for x in range(a, b + 1):
                        ranges[x] += 1
                        mentioned.add(x)
            if len(text) < 20:
                continue
            cited = sorted({int(x) for x in REF.findall(text)} - {n})
            defs.append(dict(
                n=n, doc=doc, line=line_no, text=text,
                title=title_of(text)[:180],
                marker=next((v for k, v in STATUS.items() if k in text), ""),
                sha=";".join(sorted(set(SHA.findall(text))))[:120],
                measures=";".join(sorted(set(NUM.findall(text))))[:120],
                chars=len(text), cites=cited,
                retraction_words=bool(SUPERSEDE.search(text))))
            for c in cited:
                cites.append((n, c, doc, line_no))
    return defs, cites, ranges, refs, mentioned, inline, directed


def choose_canonical(group, dates, pin=None):
    """Lowest class wins, then the EARLIEST statement, then the fullest.

    Date first, because a finding is defined when it is first written down and
    everything after that is a restatement. Length alone gets F83 wrong by ten
    characters: `DEBUG-P6`'s 272-character description of a parse bug beats
    `W2-serving`'s 262-character definition, and the description is the one
    about the archive rather than about the world.

    Length still decides between same-day rivals, and it is what separates a
    definition from a quotation when no date exists - the `DEBUG-P6` hit on F531
    is 40 characters against `ACCEPTANCE-C`'s 497. `contested` marks the rows
    where neither separated cleanly, so a human can read them.
    """
    for r in group:
        r["date"] = (dates.get((r["doc"], r["line"])) or ("9999-99-99",))[0]
    if pin:                              # an authored pin ends the argument
        for r in group:
            if "%s:%d" % (r["doc"], r["line"]) == pin:
                return r, False, True
    best = min(CLASS_RANK[doc_class(r["doc"])] for r in group)
    pool = sorted([r for r in group if CLASS_RANK[doc_class(r["doc"])] == best],
                  key=lambda r: (r["date"], -r["chars"], r["doc"], r["line"]))
    rival = pool[1] if len(pool) > 1 else None
    contested = bool(rival and rival["doc"] != pool[0]["doc"]
                     and rival["date"] == pool[0]["date"]
                     and rival["chars"] >= 0.75 * pool[0]["chars"])
    return pool[0], contested, False


# --------------------------------------------------------------------- edges
def load_edges(path):
    """The one authored input. A missing file is not an error - it is day one.

    `src` may be blank: not every correction in this archive is made BY a
    numbered finding. Some are editorial ("Do not quote F488's raw 26.71 GiB"),
    and pretending an author was a finding would be a fabricated fact.
    """
    if not os.path.exists(path):
        return [], [], {}, "absent (" + path + ")"
    rows, nots, pins, bad = [], [], {}, []
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader((l for l in fh if not l.startswith("#")),
                                delimiter="\t")
        for i, r in enumerate(reader, 2):
            raw_src = (r.get("src") or "").strip()
            try:
                src = int(raw_src.lstrip("Ff")) if raw_src else None
                dst = int(str(r["dst"]).strip().lstrip("Ff"))
            except (ValueError, KeyError, TypeError, AttributeError):
                bad.append("line %d: unreadable src/dst" % i)
                continue
            kind = (r.get("kind") or "supersedes").strip().lower()
            row = dict(src=src, dst=dst, kind=kind,
                       reason=(r.get("reason") or "").strip(),
                       evidence=(r.get("evidence") or "").strip())
            if kind == NON_EDGE:
                nots.append(row)
            elif kind == CANONICAL:
                if not row["evidence"]:
                    bad.append("line %d: canonical pin needs doc:line evidence" % i)
                else:
                    pins[dst] = row["evidence"]
            elif kind in EDGE_KINDS:
                rows.append(row)
            else:
                bad.append("line %d: unknown kind %r" % (i, kind))
    return rows, nots, pins, ("ok" if not bad else "; ".join(bad))


SCHEMA = """
CREATE TABLE finding (
  n          INTEGER PRIMARY KEY,
  workstream TEXT NOT NULL,
  title      TEXT NOT NULL,
  claim      TEXT NOT NULL,
  doc        TEXT NOT NULL,
  line       INTEGER NOT NULL,
  date       TEXT,
  commit_sha TEXT,
  marker     TEXT,
  state      TEXT NOT NULL,
  defs       INTEGER NOT NULL,
  contested  INTEGER NOT NULL,
  pinned     INTEGER NOT NULL,
  evidence_sha  TEXT,
  evidence_nums TEXT,
  chars      INTEGER NOT NULL
);
CREATE TABLE mention (
  n INTEGER NOT NULL, doc TEXT NOT NULL, line INTEGER NOT NULL,
  kind TEXT NOT NULL, chars INTEGER, date TEXT, commit_sha TEXT,
  canonical INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE edge (
  src INTEGER, dst INTEGER NOT NULL, kind TEXT NOT NULL,
  reason TEXT, evidence TEXT, authored_in TEXT NOT NULL
);
CREATE TABLE non_edge (
  src INTEGER, dst INTEGER NOT NULL, reason TEXT, evidence TEXT
);
CREATE TABLE edge_candidate (
  src INTEGER, dst INTEGER NOT NULL, doc TEXT, line INTEGER,
  shape TEXT NOT NULL, confirmed INTEGER NOT NULL DEFAULT 0,
  refused INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE cite (src INTEGER NOT NULL, dst INTEGER NOT NULL,
                   doc TEXT, line INTEGER);
CREATE TABLE doc (
  path TEXT PRIMARY KEY, class TEXT NOT NULL, workstream TEXT,
  defs INTEGER NOT NULL, first_date TEXT, last_date TEXT
);
CREATE TABLE gap (n INTEGER PRIMARY KEY, why TEXT NOT NULL);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE INDEX mention_n  ON mention (n);
CREATE INDEX cite_dst   ON cite (dst);
CREATE INDEX edge_dst   ON edge (dst);
CREATE INDEX finding_ws ON finding (workstream);
"""


def build(args):
    root = args.root
    defs, cites, ranges, refs, mentioned, inline, directed = scan(root, args.memory)
    docs = sorted({d["doc"] for d in defs})
    dates = {} if args.no_dates else blame_dates(root, docs)

    by = collections.defaultdict(list)
    for d in defs:
        by[d["n"]].append(d)

    edges, nots, pins, edge_status = load_edges(args.edges)
    for e in edges:
        e["authored_in"] = "tsv"
    for e in inline:                      # the `Supersedes: F649 (reason)` line
        if e["kind"] == NON_EDGE:
            nots.append(e)
        else:
            e["authored_in"] = "inline"
            edges.append(e)
    known = set(by)
    dangling = [e for e in edges
                if (e["src"] is not None and e["src"] not in known)
                or e["dst"] not in known]
    self_edges = [e for e in edges if e["src"] is not None and e["src"] == e["dst"]]

    # DERIVED, never authored: an authored state and an authored edge are two
    # things that can disagree. Precedence is strongest claim first.
    RANK = {"retracted": 3, "superseded": 2, "answered": 1, "live": 0}
    verb = {"retracts": "retracted", "supersedes": "superseded",
            "answers": "answered", "refines": "live"}
    state = {n: "live" for n in by}
    for e in edges:
        if e["dst"] in state and e["src"] != e["dst"]:
            new = verb.get(e["kind"], "live")
            if RANK[new] > RANK[state[e["dst"]]]:
                state[e["dst"]] = new

    db = args.out
    if os.path.exists(db):
        os.remove(db)          # derived: rebuilt whole, never migrated
    con = sqlite3.connect(db)
    con.executescript(SCHEMA)

    hi = max(by)
    n_contested = n_pinned = 0
    bad_pins = []
    for n, group in sorted(by.items()):
        best, contested, pinned = choose_canonical(group, dates, pins.get(n))
        if pins.get(n) and not pinned:
            bad_pins.append("F%d -> %s" % (n, pins[n]))
        n_contested += contested
        n_pinned += pinned
        date, sha = dates.get((best["doc"], best["line"]), (None, None))
        con.execute(
            "INSERT INTO finding VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (n, workstream(best["doc"]), best["title"], best["text"],
             best["doc"], best["line"], date, sha, best["marker"], state[n],
             len(group), int(contested), int(pinned), best["sha"],
             best["measures"], best["chars"]))
        for d in group:
            dd, ss = dates.get((d["doc"], d["line"]), (None, None))
            con.execute("INSERT INTO mention VALUES (?,?,?,?,?,?,?,?)",
                        (n, d["doc"], d["line"], "definition", d["chars"],
                         dd, ss, int(d is best)))

    for src, dst, doc, line in cites:
        con.execute("INSERT INTO cite VALUES (?,?,?,?)", (src, dst, doc, line))
    for e in edges:
        con.execute("INSERT INTO edge VALUES (?,?,?,?,?,?)",
                    (e["src"], e["dst"], e["kind"], e["reason"], e["evidence"],
                     e["authored_in"]))
    for e in nots:
        con.execute("INSERT INTO non_edge VALUES (?,?,?,?)",
                    (e["src"], e["dst"], e["reason"], e["evidence"]))

    authored = {(e["src"], e["dst"]) for e in edges}
    refused = {(e["src"], e["dst"]) for e in nots}
    # A target that already carries an authored edge or refusal has been READ,
    # whoever the detector guessed the source was. Detector sources are often
    # None - the correcting sentence lives in prose outside any definition
    # block - so pairing on (src, dst) alone would re-list settled targets.
    read_dst = {e["dst"] for e in edges} | {e["dst"] for e in nots}
    seen_cand, cand = set(), collections.Counter()

    def candidate(src, dst, doc, line, shape):
        if (src, dst) in seen_cand:
            return
        seen_cand.add((src, dst))
        ok = int((src, dst) in authored or (dst, src) in authored
                or dst in read_dst or src in read_dst)
        con.execute("INSERT INTO edge_candidate VALUES (?,?,?,?,?,?,?)",
                    (src, dst, doc, line, shape, ok,
                     int((src, dst) in refused)))
        cand[shape] += 1

    for src, dst, doc, line, shape in directed:
        candidate(src, dst, doc, line, shape)
    for d in defs:                       # F669's +76% rule, kept as a foil
        if not d["retraction_words"]:
            continue
        for c in d["cites"]:
            candidate(d["n"], c, d["doc"], d["line"], "co-occurrence")

    dcount = collections.Counter(d["doc"] for d in defs)
    for doc in docs:
        ds = [dates[k] for k in dates if k[0] == doc]
        con.execute("INSERT INTO doc VALUES (?,?,?,?,?,?)",
                    (doc, doc_class(doc), workstream(doc), dcount[doc],
                     min((x[0] for x in ds), default=None),
                     max((x[0] for x in ds), default=None)))

    rng = sorted(k for k in mentioned
                 if k not in by and ranges.get(k) and 0 < k <= hi)
    cit = sorted(k for k in mentioned
                 if k not in by and not ranges.get(k) and 0 < k <= hi)
    absent = [x for x in range(1, hi + 1) if x not in mentioned]
    for n in rng:
        con.execute("INSERT INTO gap VALUES (?,?)", (n, "range-covered only"))
    for n in cit:
        con.execute("INSERT INTO gap VALUES (?,?)", (n, "cited, never defined"))
    for n in absent:
        con.execute("INSERT INTO gap VALUES (?,?)", (n, "never mentioned"))

    corpus = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                            capture_output=True, text=True)
    head = corpus.stdout.strip()[:12] if corpus.returncode == 0 else ""
    dated = sum(1 for n in by
                if dates.get((by[n][0]["doc"], by[n][0]["line"])))
    for k, v in [
            ("built_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
            ("corpus_commit", head),
            ("docs_scanned", str(len(md_files(root, args.memory)))),
            ("definitions_parsed", str(len(defs))),
            ("findings", str(len(by))),
            ("highest", "F%d" % hi),
            ("authored_edges", str(len(edges))),
            ("authored_non_edges", str(len(nots))),
            ("authored_canonical_pins", str(len(pins))),
            ("edge_file", args.edges),
            ("edge_file_status", edge_status),
            ("heuristic_candidates", str(sum(cand.values()))),
            ("edge_recall", "UNKNOWN. F669 counted 38 correction edges in the "
                            "prose by hand; the authored file holds what has "
                            "been read and evidenced, which is fewer. Do not "
                            "quote the edge count as the archive's total."),
            ("contested_canonical", str(n_contested)),
            ("source_of_truth",
             "the markdown. This file is derived and may be deleted."),
    ]:
        con.execute("INSERT INTO meta VALUES (?,?)", (k, v))
    con.commit()

    print("corpus            %s" % head)
    print("docs scanned      %d" % len(md_files(root, args.memory)))
    print("definitions       %d parsed -> %d findings (F1..F%d)"
          % (len(defs), len(by), hi))
    print("  contested pick  %d   (%d pinned by hand)" % (n_contested, n_pinned))
    if bad_pins:
        print("  !! pin matches no parsed definition: %s" % ", ".join(bad_pins))
    print("  dated by blame  %d   (memory files are not in git and get no date)"
          % dated)
    print("coverage          %d defined + %d range-only + %d cited-never-defined"
          " + %d never-mentioned = %d of %d"
          % (len(by), len(rng), len(cit), len(absent),
             len(by) + len(rng) + len(cit) + len(absent), hi))
    print("citations         %d" % len(cites))
    print("authored edges    %d  [%s]  (%d from the tsv, %d inline)"
          % (len(edges), edge_status,
             sum(1 for e in edges if e["authored_in"] == "tsv"),
             sum(1 for e in edges if e["authored_in"] == "inline")))
    if dangling:
        print("  !! dangling     %d: %s" % (
            len(dangling),
            ", ".join("F%s->F%d" % (e["src"], e["dst"]) for e in dangling[:8])))
    if self_edges:
        print("  !! self-edges   %d" % len(self_edges))
    for st in ("superseded", "retracted", "answered"):
        print("  %-14s  %d" % (st, sum(1 for v in state.values() if v == st)))
    print("authored NON-edges %d  (\"this does not retract F531\" - stored so "
          "the next heuristic cannot re-assert it)" % len(nots))
    print("candidates        %s   [reading prompts, NEVER state]"
          % ", ".join("%s %d" % (k, v) for k, v in cand.most_common()))
    print("\nwrote %s" % db)
    con.close()


# ------------------------------------------------------------------ queries
def connect(args):
    if not os.path.exists(args.out):
        sys.exit("no ledger at %s - run `fledger.py build` first" % args.out)
    con = sqlite3.connect(args.out)
    con.row_factory = sqlite3.Row
    return con


def num(s):
    return int(str(s).lstrip("Ff"))


def cmd_show(args):
    con = connect(args)
    n = num(args.finding)
    r = con.execute("SELECT * FROM finding WHERE n=?", (n,)).fetchone()
    if not r:
        g = con.execute("SELECT why FROM gap WHERE n=?", (n,)).fetchone()
        sys.exit("F%d: %s" % (n, g["why"]) if g
                 else "F%d: not in the archive" % n)
    print("F%d  [%s]  %s  %s  %s  %s:%d"
          % (n, r["state"], r["marker"] or "-", r["workstream"],
             r["date"] or "undated", r["doc"], r["line"]))
    print("\n%s\n" % r["title"])
    print(r["claim"])
    if r["evidence_sha"]:
        print("\nevidence sha   %s" % r["evidence_sha"])
    if r["evidence_nums"]:
        print("measured       %s" % r["evidence_nums"])
    if r["defs"] > 1:
        print("\nrestated in %d other place(s)%s"
              % (r["defs"] - 1,
                 "  [CONTESTED canonical pick]" if r["contested"] else ""))
        for m in con.execute(
                "SELECT * FROM mention WHERE n=? AND canonical=0 ORDER BY doc",
                (n,)):
            print("  %s:%d  (%d chars)" % (m["doc"], m["line"], m["chars"]))
    for e in con.execute("SELECT * FROM edge WHERE src=?", (n,)):
        print("\n%s F%d: %s   [%s]"
              % (e["kind"].upper(), e["dst"], e["reason"], e["evidence"]))
    for e in con.execute("SELECT * FROM edge WHERE dst=?", (n,)):
        who = "F%d" % e["src"] if e["src"] is not None else "the archive"
        print("\n!! %s %s this one: %s   [%s]"
              % (who, e["kind"], e["reason"], e["evidence"]))
    for e in con.execute("SELECT * FROM non_edge WHERE dst=? OR src=?", (n, n)):
        who = "F%s" % e["src"] if e["src"] is not None else "the archive"
        print("\n(non-edge) %s does NOT correct F%d: %s   [%s]"
              % (who, e["dst"], e["reason"], e["evidence"]))
    cited_by = [str(x["src"]) for x in con.execute(
        "SELECT DISTINCT src FROM cite WHERE dst=? ORDER BY src", (n,))]
    if cited_by:
        print("\ncited by       %d: %s%s"
              % (len(cited_by), " ".join("F" + c for c in cited_by[:24]),
                 " ..." if len(cited_by) > 24 else ""))


def cmd_search(args):
    con = connect(args)
    rows = con.execute(
        "SELECT n, state, workstream, date, title FROM finding "
        "WHERE claim LIKE ? ORDER BY n", ("%" + args.text + "%",)).fetchall()
    for r in rows:
        print("F%-4d %-10s %-12s %s  %s"
              % (r["n"], r["state"], r["workstream"],
                 r["date"] or "----------", r["title"][:88]))
    print("\n%d findings mention %r" % (len(rows), args.text))


def cmd_gaps(args):
    con = connect(args)
    for (why,) in con.execute("SELECT DISTINCT why FROM gap"):
        ns = [str(r[0]) for r in con.execute(
            "SELECT n FROM gap WHERE why=? ORDER BY n", (why,))]
        print("%-24s %3d  %s" % (why, len(ns), " ".join("F" + x for x in ns)))


def cmd_contested(args):
    con = connect(args)
    for r in con.execute("SELECT * FROM finding WHERE contested=1 ORDER BY n"):
        print("F%d  canonical -> %s:%d (%d chars)"
              % (r["n"], r["doc"], r["line"], r["chars"]))
        for m in con.execute(
                "SELECT * FROM mention WHERE n=? AND canonical=0 "
                "ORDER BY -chars", (r["n"],)):
            print("      rival -> %s:%d (%d chars)"
                  % (m["doc"], m["line"], m["chars"]))


def cmd_candidates(args):
    con = connect(args)
    rows = con.execute(
        "SELECT * FROM edge_candidate WHERE confirmed=0 AND refused=0 "
        "ORDER BY shape='co-occurrence', src, dst").fetchall()
    for r in rows:
        print("F%-5s -?-> F%-5d %-14s %s:%d"
              % (r["src"], r["dst"], r["shape"], r["doc"], r["line"]))
    done = con.execute("SELECT COUNT(*) FROM edge_candidate "
                       "WHERE confirmed=1 OR refused=1").fetchone()[0]
    print("\n%d unread candidates (%d already resolved as edges or non-edges)."
          "\nThe `co-occurrence` shape is F669's +76%% rule and is mostly "
          "citations; `verb->F` and the rest require the number to be the "
          "object of a correction verb. Both are reading prompts, not edges."
          % (len(rows), done))


def cmd_next(args):
    """What is the next free finding number.

    Worth a command: the memory index has carried a stale answer more than once,
    and the number is cheap to get wrong by one. A number is TAKEN if it is
    defined, range-covered, or cited anywhere - anything else re-issues it.
    """
    con = connect(args)
    hi = max(con.execute("SELECT MAX(n) FROM finding").fetchone()[0],
             con.execute("SELECT COALESCE(MAX(n), 0) FROM gap").fetchone()[0])
    taken = {r[0] for r in con.execute("SELECT n FROM finding")}
    taken |= {r[0] for r in con.execute("SELECT n FROM gap")}
    free = [x for x in range(1, hi + 1) if x not in taken]
    print("highest issued   F%d" % hi)
    print("next free        F%d" % (hi + 1))
    if free:
        print("unused below it  %s" % " ".join("F%d" % x for x in free[:20]))
    else:
        print("unused below it  none - F1..F%d are all accounted for" % hi)


def cmd_chain(args):
    con = connect(args)
    n, seen = num(args.finding), []
    while True:
        r = con.execute("SELECT src, kind, reason FROM edge WHERE dst=?",
                        (n,)).fetchone()
        f = con.execute("SELECT title, state FROM finding WHERE n=?",
                        (n,)).fetchone()
        print("F%d  [%s]  %s" % (n, f["state"] if f else "?",
                                 f["title"][:78] if f else "?"))
        if not r or r["src"] is None or r["src"] in seen:
            if r and r["src"] is None:
                print("   ^-- %s by the archive: %s" % (r["kind"], r["reason"]))
            break
        seen.append(n)
        print("   ^-- %s by F%d: %s" % (r["kind"], r["src"], r["reason"]))
        n = r["src"]


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--root", default=".")
    p.add_argument("--memory", default=DEFAULT_MEM)
    p.add_argument("--out", default=DEFAULT_DB)
    p.add_argument("--edges", default=DEFAULT_EDGES)
    sub = p.add_subparsers(dest="cmd")
    b = sub.add_parser("build")
    b.add_argument("--no-dates", action="store_true")
    s = sub.add_parser("show")
    s.add_argument("finding")
    q = sub.add_parser("search")
    q.add_argument("text")
    sub.add_parser("gaps")
    sub.add_parser("contested")
    sub.add_parser("candidates")
    sub.add_parser("next")
    c = sub.add_parser("chain")
    c.add_argument("finding")
    a = p.parse_args()
    if a.cmd in (None, "build"):
        a.no_dates = getattr(a, "no_dates", False)
        return build(a)
    return dict(show=cmd_show, search=cmd_search, gaps=cmd_gaps,
                contested=cmd_contested, candidates=cmd_candidates,
                next=cmd_next, chain=cmd_chain)[a.cmd](a)


if __name__ == "__main__":
    main()
