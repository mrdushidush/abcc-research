"""Read a K-series batch into an arm table plus the right-reason discriminators.

  python research/tools/kread.py b3
  python research/tools/kread.py b2          # positive control: must reproduce the record

A verdict alone is not evidence -- batch 2 caught the champion PASSING `round` by
fixing the call site and leaving the defective function in place, with a verifier
message byte-identical to the two cells that fixed it properly. So every cell is
also diffed against its pristine fixture, and the file sets are derived from the
refsol/sham overlays rather than typed in (see kdisc.py).
"""
import collections
import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kdisc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TASKS = kdisc.TASKS


def unwrap(m):
    if isinstance(m, dict):
        if "measured" in m:
            return m["measured"]
        if "not_applicable" in m:
            return None
    return m


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def changed_files(task, workdir):
    """Files in the workdir whose bytes differ from the pristine fixture."""
    fx = os.path.join(TASKS, task, "fixture")
    if not os.path.isdir(fx) or not os.path.isdir(workdir):
        return None
    out = []
    for dirpath, dirs, names in os.walk(fx):
        dirs[:] = [d for d in dirs if not kdisc.noisy(d)]
        for n in names:
            src = os.path.join(dirpath, n)
            rel = os.path.relpath(src, fx).replace(os.sep, "/")
            if kdisc.noisy(rel):
                continue
            dst = os.path.join(workdir, rel.replace("/", os.sep))
            if not os.path.exists(dst):
                out.append(rel + " (DELETED)")
            elif digest(src) != digest(dst):
                out.append(rel)
    for dirpath, dirs, names in os.walk(workdir):
        dirs[:] = [d for d in dirs if not kdisc.noisy(d)]
        for n in names:
            rel = os.path.relpath(os.path.join(dirpath, n), workdir).replace(os.sep, "/")
            if kdisc.noisy(rel):
                continue
            if not os.path.exists(os.path.join(fx, rel.replace("/", os.sep))):
                out.append(rel + " (NEW)")
    return sorted(out)


def contains(workdir, rel, needle):
    p = os.path.join(workdir, rel.replace("/", os.sep))
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return needle in f.read()
    except OSError:
        return None


def right_reason(task, workdir, changed, verifier_msg=""):
    """Return (verdict_string, notes[])."""
    root, sham = kdisc.sets_for(task)
    bare = {c.split(" ")[0] for c in changed}
    hit_root = sorted(root & bare)
    sham_only = sorted((sham - root) & bare)
    notes = []

    if root:
        notes.append("root sites %d/%d: %s" % (len(hit_root), len(root),
                                               ", ".join(hit_root) or "NONE"))
    if sham - root:
        notes.append("sham-only edited: %s" % (", ".join(sham_only) or "no"))

    tell = kdisc.CONTENT_TELL.get(task)
    content_ok = None
    if tell:
        f, needle, why = tell
        content_ok = contains(workdir, f, needle)
        notes.append("content tell %r in %s: %s (%s)" %
                     (needle, f, {True: "YES", False: "NO", None: "file missing"}[content_ok], why))

    marker = kdisc.FORMAT_FAIL_MARKER.get(task)
    fmt_shape = False
    if marker and verifier_msg:
        needle, why = marker
        if needle in verifier_msg:
            fmt_shape = True
            notes.append("FORMAT MARKER in verifier message: %s" % why)

    if fmt_shape and len(hit_root) == len(root):
        return ("FORMAT-ONLY failure -- all %d root sites edited, verifier rejected the "
                "OUTPUT SHAPE" % len(root)), notes

    if not hit_root:
        verdict = "NO ROOT EDIT -- symptom fixed elsewhere, defect left in place"
    elif content_ok is False:
        verdict = "root file edited but CONTENT IS NOT THE CORRECT SHAPE"
    elif len(hit_root) < len(root):
        verdict = "PARTIAL: %d of %d root sites" % (len(hit_root), len(root))
    else:
        verdict = "ROOT, all %d site(s)" % len(root)
    if sham_only:
        verdict += "  [+sham site touched]"
    return verdict, notes


def load(tag):
    arms = collections.OrderedDict()
    for d in sorted(glob.glob(os.path.join(ROOT, "runs", "k-*-%s-r*" % tag))):
        base = os.path.basename(d)
        slug = base[2:base.rindex("-" + tag)]
        for jf in glob.glob(os.path.join(d, "w8-*", "cells.jsonl")):
            with open(jf, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    c = json.loads(line)
                    c["_slug"] = slug
                    c["_repeat"] = base[base.rindex("-r") + 2:]
                    arms.setdefault(slug, []).append(c)
    return arms


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "b3"
    arms = load(tag)
    if not arms:
        print("no cells.jsonl for tag %r -- it is written only at REPEAT end" % tag)
        return

    print("=" * 98)
    print("K-series %s" % tag)
    print("=" * 98)
    hdr = ("%-10s %5s %5s %5s %5s  %10s  %8s  %8s  %10s" %
           ("arm", "cells", "pass", "fail", "othr", "wall_s", "iters", "peakPT", "tokens_out"))
    print(hdr)
    print("-" * len(hdr))
    for slug, cells in arms.items():
        st = collections.Counter(c["status"] for c in cells)
        wall = sum(unwrap(c["metrics"].get("wall_clock_s")) or 0 for c in cells)
        its = [i for i in (unwrap(c["metrics"].get("iterations")) for c in cells) if i is not None]
        pk = [p for p in (unwrap(c["metrics"].get("peak_prompt_tokens")) for c in cells) if p is not None]
        to = sum(unwrap(c["metrics"].get("tokens_out")) or 0 for c in cells)
        other = len(cells) - st.get("pass", 0) - st.get("fail", 0)
        print("%-10s %5d %5d %5d %5d  %10.0f  %8.1f  %8s  %10d" %
              (slug, len(cells), st.get("pass", 0), st.get("fail", 0), other, wall,
               (sum(its) / len(its)) if its else 0,
               ("%d" % max(pk)) if pk else "-", to))
    print()
    print("peak_prompt_tokens is quantized to 1024 and every limit UNDER-reports: it is a")
    print("FLOOR. Say 'at least N', never 'N'.")

    print()
    print("=" * 98)
    print("PER-CELL, with the right-reason check (a verdict alone is not evidence)")
    print("=" * 98)
    for slug, cells in arms.items():
        print()
        print("### %s" % slug)
        for c in sorted(cells, key=lambda x: (x["task"], x["_repeat"])):
            m = c["metrics"]
            wc = unwrap(m.get("wall_clock_s"))
            print("  r%-2s %-32s %-8s wall=%-7s iters=%-4s peakPT=%-6s out=%-6s" %
                  (c["_repeat"], c["task"], c["status"],
                   ("%.0f" % wc) if wc is not None else "-",
                   unwrap(m.get("iterations")), unwrap(m.get("peak_prompt_tokens")),
                   unwrap(m.get("tokens_out"))))
            if c["status"] not in ("pass", "fail"):
                print("      timeout evidence: output_bytes=%s last_output_ms=%s"
                      % (unwrap(m.get("subject_output_bytes")),
                         unwrap(m.get("subject_last_output_ms"))))
            v = c.get("verifier") or {}
            if v.get("message"):
                print("      verifier: %s" % v["message"][:112])
            wd = (c.get("workdir") or "").replace("\\", "/")
            ch = changed_files(c["task"], wd)
            if ch is None:
                print("      workdir MISSING -- cannot check the right reason")
                continue
            verdict, notes = right_reason(c["task"], wd, ch, (v.get("message") or ""))
            print("      edits(%d): %s" % (len(ch), ", ".join(ch[:9])))
            for n in notes:
                print("        - %s" % n)
            print("      RIGHT-REASON: %s" % verdict)


if __name__ == "__main__":
    main()
