"""Read the tap: one line per chat call, and each call's reasoning / answer text on disk.

    python research/tools/llm_tapread.py <tap-dir>   summary table; writes NNNN.reasoning.txt / NNNN.answer.txt
"""
import glob
import json
import os
import sys

D = sys.argv[1]
for req in sorted(glob.glob(os.path.join(D, "*.req.json"))):
    stem = req[: -len(".req.json")]
    head, _, body = open(req, "rb").read().partition(b"\n")
    meta = json.loads(head)
    if "chat/completions" not in meta["path"]:
        continue
    b = json.loads(body)
    msgs = b.get("messages", [])
    task = ""
    for m in msgs:
        c = m.get("content") or ""
        if isinstance(c, str) and "## The task" in c:
            task = c.split("## The task", 1)[1].strip().split("\n", 1)[0]
    reasoning, answer, calls, finish, usage = [], [], [], None, None
    try:
        raw = open(stem + ".resp.txt", encoding="utf-8", errors="replace").read()
    except FileNotFoundError:
        raw = ""
    for line in raw.splitlines():
        if not line.startswith("data: ") or line == "data: [DONE]":
            continue
        try:
            ev = json.loads(line[6:])
        except json.JSONDecodeError:
            continue
        if ev.get("usage"):
            usage = ev["usage"]
        for ch in ev.get("choices", []):
            d = ch.get("delta") or {}
            reasoning.append(d.get("reasoning_content") or d.get("reasoning") or "")
            answer.append(d.get("content") or "")
            for tc in d.get("tool_calls") or []:
                fn = tc.get("function") or {}
                if fn.get("name"):
                    calls.append(fn["name"])
            finish = ch.get("finish_reason") or finish
    r, a = "".join(reasoning), "".join(answer)
    open(stem + ".reasoning.txt", "w", encoding="utf-8").write(r)
    open(stem + ".answer.txt", "w", encoding="utf-8").write(a)
    print(f"{os.path.basename(stem)}  {task[:12]:<12} msgs={len(msgs):>2} seed={b.get('seed')} "
          f"max={b.get('max_tokens') or b.get('max_completion_tokens')} finish={finish} "
          f"reasoning={len(r):>6} answer={len(a):>5} calls={','.join(calls)} "
          f"completion={(usage or {}).get('completion_tokens')}")
