# -*- coding: utf-8 -*-
"""What the server discards when a conversation outgrows the window, and what it costs.

    python research/tools/windowprobe.py canaries   # which region goes
    python research/tools/windowprobe.py pairs      # abcc's own shape, cut
    python research/tools/windowprobe.py orphans    # the malformation, at a size that FITS
    python research/tools/windowprobe.py cross       # F758: the brief is a variable
    python research/tools/windowprobe.py refuse     # the other door: one oversized message

Needs a loaded model. Written for F753-F755 and kept because every repair of F744
has to be re-measured against it.

THE TRAPS, in the order they cost time:

  * PROBE WITH THE SHAPE UNDER TEST (F747). A single oversized message is REFUSED
    with HTTP 400, because a rolling window has nothing to drop; a CONVERSATION of
    the same size is silently truncated at 200 OK. The loud shape is the one a
    naive probe builds first, and reading its 400 as "the server does not
    truncate" nearly withdrew a true finding.
  * THE CANARY IN THE FINAL MESSAGE IS UNRELIABLE. The model repeatedly reports a
    code word stated in the QUESTION as MISSING -- apparently declining to count it
    as one it was GIVEN. The load-bearing contrast is FIRST found vs MIDDLE
    missing, which is also what the vendor's own type describes.
  * n = 1 IS A SAMPLE (F716). A seed makes a run attributable, not reproducible:
    two byte-identical requests here returned 482 and 807 completion tokens. Every
    arm is flown at more than one seed.
  * 🚨 THE BRIEF IS A VARIABLE, AND IT INTERACTS WITH THE CUT (F758). The first
    arm flown here answered NOTHING over a cut conversation, 0 of 11, and the second --
    same 140 middle messages, a reworded system prompt and question -- answered 7 of 7.
    Change either text alone and the answer returns, 3 of 3. So never attribute an
    absence to the context without re-flying the arm with the wording changed; run
    `cross` for the 2x2.
  * ASK FOR ENOUGH max_tokens. At 300 the cut arm returned an empty reply and
    looked like F497; at 1500 the same request answered. The trace eats the budget
    first.
"""
import json
import sys
import urllib.error
import urllib.request

URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"
SEEDS = (424242, 7, 99991)

SYSTEM = (
    "You are a code assistant working through a long transcript.\n"
    "YOUR CALLSIGN IS OMEGA-31. Every reply you write must end with your callsign.\n"
    "You will be given code words during the conversation. When asked for them, "
    "repeat exactly the ones you can actually see in this conversation, and say "
    "MISSING for any you cannot find. Never guess one."
)
CANARIES = (("front", "ALPHA-7742"), ("middle", "BRAVO-1188"),
            ("late", "DELTA-9051"), ("system", "OMEGA-31"))
ASK = ("List code word one, two and three exactly as you were given them. "
       "Write MISSING for any you cannot find in this conversation.")
TOOLS = [{"type": "function", "function": {
    "name": "read_file", "description": "read a file",
    "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                   "required": ["path"]}}}]


def filler(i, kind="prose"):
    """A block of plausible source text, distinct per block."""
    if kind == "prose":
        return "\n".join(
            f"fn step_{i}_{j}(state: &mut Frame) -> Result<u32, Error> {{ "
            f"let v = state.slot({i * 97 + j}).saturating_add({j * 13}); Ok(v) }}"
            for j in range(24))
    return "\n".join(
        f"src/mod_{i}/file_{j}.rs:{j * 7}: fn handle_{i}_{j}(f: &mut Frame) -> u32 "
        f"{{ f.slot({j}) }}" for j in range(22))


def prose(blocks):
    """User/assistant turns only -- the shape that is easy to build."""
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": "CODE WORD ONE IS ALPHA-7742.\n" + filler(0)},
            {"role": "assistant", "content": "Noted. OMEGA-31"}]
    for i in range(1, blocks):
        body = filler(i)
        if i == blocks // 2:
            body = "CODE WORD TWO IS BRAVO-1188.\n" + body
        msgs.append({"role": "user", "content": body})
        msgs.append({"role": "assistant", "content": f"Read block {i}. OMEGA-31"})
    msgs.append({"role": "user", "content": "CODE WORD THREE IS DELTA-9051.\n" + ASK})
    return msgs


def pairs(n, drop_calls=(), drop_results=()):
    """abcc's own shape: assistant(tool_calls) / tool(result), n of them.

    `drop_calls` / `drop_results` build the two malformations BY HAND, so the
    structure can be tested at a size that fits.
    """
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": "CODE WORD ONE IS ALPHA-7742.\nBegin the survey."}]
    for i in range(n):
        out = filler(i, "tool")
        if i == n // 2:
            out = "CODE WORD TWO IS BRAVO-1188.\n" + out
        if i not in drop_calls:
            msgs.append({"role": "assistant", "content": "", "tool_calls": [{
                "id": f"call_{i}", "type": "function",
                "function": {"name": "read_file",
                             "arguments": json.dumps({"path": f"src/mod_{i}/file.rs"})}}]})
        if i not in drop_results:
            msgs.append({"role": "tool", "tool_call_id": f"call_{i}", "content": out})
    msgs.append({"role": "user", "content": "CODE WORD THREE IS DELTA-9051.\n" + ASK})
    return msgs


def ask(msgs, seed, budget=1500, tools=False, extra=None):
    payload = {"model": MODEL, "messages": msgs, "max_tokens": budget,
               "seed": seed, "temperature": 0.0, "stream": False}
    if tools:
        payload["tools"] = TOOLS
    if extra:
        payload.update(extra)
    req = urllib.request.Request(URL, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=1200) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read().decode()[:400]}
    ch = d["choices"][0]
    text = ch["message"].get("content") or ""
    return {"status": 200,
            "prompt": d["usage"]["prompt_tokens"],
            "completion": d["usage"]["completion_tokens"],
            "finish": ch.get("finish_reason"),
            "text": text,
            "reasoning": ch["message"].get("reasoning_content") or "",
            "found": [n for n, tok in CANARIES if tok in text.upper()]}


def flight(label, msgs, seeds=SEEDS[:2], budget=1500, tools=False, extra=None):
    chars = sum(len(json.dumps(m)) for m in msgs)
    print(f"\n--- {label}: {len(msgs)} messages, {chars} chars"
          + (f", extra={extra}" if extra else ""))
    for seed in seeds:
        r = ask(msgs, seed, budget, tools, extra)
        if r["status"] != 200:
            print(f"    seed {seed:>7}: status {r['status']}  {r['body'][:240]}")
            continue
        print(f"    seed {seed:>7}: prompt {r['prompt']:>6}  completion {r['completion']:>5}"
              f"  finish {r['finish']:<11} text {len(r['text']):>4} chars"
              f"  reasoning {len(r['reasoning']):>6}  found {r['found']}")


# 🚨 F758: the FIRST wording this session flew. Over a cut conversation it answers
# NOTHING -- 0 of 11 -- and the second wording (SYSTEM/ASK above) answers 7 of 7 over
# the identical 140 middle messages. Neither text does it alone: swap either one and
# the answer comes back, 3 of 3. Kept verbatim because the pair is the finding.
SYSTEM_A = ("You are a code assistant with tools. YOUR CALLSIGN IS OMEGA-31 and every "
            "reply ends with it. Report exactly what you can see; write MISSING for "
            "anything you cannot find. Never guess.")
ASK_A = ("List code word one, two and three exactly, MISSING for any you cannot find.")


def worded(msgs, system=None, ask=None):
    """The same conversation with the system prompt and/or the question swapped."""
    out = [dict(m) for m in msgs]
    if system:
        out[0]["content"] = system
    if ask:
        out[-1]["content"] = "CODE WORD THREE IS DELTA-9051.\n" + ask
    return out


def one_message(tokens_wanted):
    """The OTHER shape (F747): one oversized message, which is refused instead."""
    line = "fn f(state: &mut Frame) -> u32 { state.slot(7).saturating_add(13) }\n"
    # ~2.4 chars per token on dense code, measured 2026-09-13 on the champion.
    body = line * max(1, int(tokens_wanted * 2.4 / len(line)))
    return [{"role": "user", "content": "Count these:\n" + body}]


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "canaries"
    if which == "canaries":
        # F753. The control is what says the model CAN do this, so an absence in
        # the overflow arm is the server and not the model.
        flight("CONTROL, fits the window", prose(10), seeds=SEEDS[:1])
        flight("OVERFLOW, same shape", prose(60), seeds=SEEDS[:1])
        # F754. `stopAtLimit` would refuse rather than truncate, if it were read.
        flight("OVERFLOW + stopAtLimit", prose(60), seeds=SEEDS[:1],
               extra={"contextOverflowPolicy": "stopAtLimit"})
    elif which == "pairs":
        # F755. Same sizes, abcc's own request shape.
        flight("CONTROL, pairs that fit", pairs(8), tools=True)
        flight("OVERFLOW, pairs cut", pairs(70), seeds=SEEDS, tools=True)
    elif which == "orphans":
        # F755's mechanism, with the window out of the picture entirely.
        flight("INTACT pairs, fits", pairs(8), tools=True)
        flight("ORPHANED tool RESULTS, fits", pairs(8, drop_calls=(2, 3, 4, 5)), tools=True)
        flight("ORPHANED tool CALLS, fits", pairs(8, drop_results=(2, 3, 4, 5)), tools=True)
    elif which == "cross":
        # F758. The 2x2 that says the silence is an INTERACTION and not the cut.
        cut = pairs(70)
        flight("B system + B ask", cut, tools=True)
        flight("A system + B ask", worded(cut, system=SYSTEM_A), tools=True)
        flight("B system + A ask", worded(cut, ask=ASK_A), tools=True)
        flight("A system + A ask  <- the silent pair",
               worded(cut, system=SYSTEM_A, ask=ASK_A), tools=True)
    elif which == "refuse":
        for want in (45_000, 60_000):
            flight(f"ONE message, ~{want} tokens", one_message(want), seeds=SEEDS[:1], budget=64)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
