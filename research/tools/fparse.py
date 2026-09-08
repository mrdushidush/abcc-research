#!/usr/bin/env python3
"""fparse.py - the finding grammar, in one place.

Extracted verbatim from `fread.py` so the ledger builder and the coverage probe
cannot drift apart. **The six definition shapes below are the expensive part of
this archive** - shape 4 (a heading with a section number first) was worth 58
findings on its own and took the parse from 15% to 88.5%; shape 5 (bold spanning
the whole claim) was worth 65. Do not "tidy" them without re-running
`fread.py` and comparing the coverage block.

Derived-only, like everything downstream: this module reads markdown and returns
records. It never writes to a source document.
"""
import re, os, sys, glob

# ---------------------------------------------------------------- the shapes
# 1. bolded number heading a paragraph, a list item, or a table row:
#       **F664** - claim   /   - **F620** - claim   /   | **F123** | claim |
DEF = re.compile(r'^(?P<lead>\s*(?:[-*+]\s+|\|\s*)?)\*\*F(?P<n>\d{1,4})\*\*(?P<sep>\s*[.—–:)\-]|\s|\s*\|)')
# 6. bare (unbolded) definition, including a summary-table row:
#       F123. claim   /   | F218 - every gate input is Measured | W6 |
DEF_BARE = re.compile(r'^(?P<lead>\s*(?:[-*+]\s+|\|\s*)?)F(?P<n>\d{1,4})(?P<sep>[.—–:)])\s')
# 3 + 4. a heading, optionally with a section number and/or emoji before it:
#       ### F600 - the method   /   ## 3. F633 - the announcement is on the wire
DEF_HEAD = re.compile(r'^(?P<lead>#{1,6}\s+(?:\d{1,2}[.)]\s*)?[^A-Za-z0-9]{0,12}\**)F(?P<n>\d{1,4})\**(?P<sep>\s*[.—–:)\-]|\s)')
# 5. a marker plus bold spanning the whole claim:
#       (warning) **F574 - the two axes are NOT orthogonal**
#    A leading '(' is FORBIDDEN: '(F541) - so the slot count...' is a citation on
#    a continuation line, and excluding it is what keeps precision up.
DEF_MARK = re.compile(r'^(?P<lead>\s*(?:[-*+]\s+)?[^A-Za-z0-9\s(]{0,4}\s*\*\*)F(?P<n>\d{1,4})(?P<sep>\s*[.—–:)\-]\s|\s)')

REF   = re.compile(r'\bF(\d{1,4})\b')
RANGE = re.compile(r'F(\d{1,4})\s*[–—-]\s*F?(\d{1,4})')
SHA   = re.compile(r'`([0-9a-f]{7,40})`')
NUM   = re.compile(r'\b\d+(?:\.\d+)?\s*(?:%|ms|s\b|GiB|MiB|bpw|of \d+)')

STATUS = {'\U0001F6A8': 'alarm', '⚠': 'caution', '✅': 'settled',
          '\U0001F389': 'win', '▶': 'live', '⏸': 'paused'}

# Kept ONLY to reproduce the over-asserting heuristic that F669 measured at +76%.
# It is never a source of truth for supersession - the authored edge file is.
SUPERSEDE = re.compile(r'(do NOT credit|no longer|overtaken|supersed|retract|withdraw|'
                       r'was wrong|is wrong|corrects|replaces|inverts|kills|dead\b|'
                       r'stop being quoted|not a property)', re.I)


def is_def(line):
    """The match for any of the six shapes, or None."""
    return (DEF.match(line) or DEF_HEAD.match(line)
            or DEF_MARK.match(line) or DEF_BARE.match(line))


def title_of(text):
    m = re.search(r'\*\*(.+?)\*\*', text)
    if m and len(m.group(1)) > 12:
        return m.group(1).strip()
    s = re.split(r'(?<=[.!?])\s', text.strip(), maxsplit=1)[0]
    return s.strip()


def clean(s):
    return re.sub(r'\s+', ' ', s).strip()


def md_files(root, mem=None):
    """Every research doc, then every memory file."""
    out = sorted(glob.glob(os.path.join(root, "research", "**", "*.md"), recursive=True))
    if mem:
        out += sorted(glob.glob(os.path.join(mem, "*.md")))
    return out


def relpath(path, root):
    """Repo-relative, or `memory/x.md` when the file lives on another drive."""
    try:
        return os.path.relpath(path, root).replace("\\", "/")
    except ValueError:
        return "memory/" + os.path.basename(path)


def walk(lines):
    """Yield the document in order as ('plain', i, line) and ('def', ...) events.

    A definition event is (kind, n, line_no, is_table, text, consumed) where
    `line_no` is 1-based and points at the line the definition starts on, and
    `consumed` is how many lines the block ate. Every line is reported exactly
    once, by exactly one event, so a caller can reproduce a single-pass scan.
    """
    i = 0
    while i < len(lines):
        line = lines[i]
        m = is_def(line)
        if not m:
            yield ('plain', i + 1, line)
            i += 1
            continue
        n = int(m.group("n"))
        is_head = line.lstrip().startswith("#")
        is_table = line.lstrip().startswith("|")
        body = [line[m.end():]]
        if not is_table:                     # block style: run to blank / next def
            j = i + 1
            if is_head:
                while j < len(lines) and not lines[j].strip():
                    j += 1
            while j < len(lines) and lines[j].strip() and not is_def(lines[j]):
                if re.match(r'^#{1,6}\s', lines[j]) or lines[j].lstrip().startswith("|"):
                    break
                body.append(lines[j])
                j += 1
            start_line = j - len(body) + 1   # fread's convention, preserved exactly
            i = j
        else:
            body = [line.strip().strip("|")]
            start_line = i + 1
            i += 1
        yield ('def', n, start_line, is_table, clean(" ".join(body)), len(body))
