"""Close the 2x2: does the <untrusted> WRAPPER add anything over the sentence,
and does the wrapper alone do anything?  Reuses probe.py verbatim."""
import json, time
import probe as P

WRAP = '<untrusted source="read_file:src/utils.py">\n' + P.FILE_BODY + '\n</untrusted>'

def build(arm):
    sys_p = P.SYS_BASE
    if arm == "tag+file":          # wrapper + the sentence that names file contents
        sys_p += P.FILE_SENTENCE
        body = WRAP
    elif arm == "tag-only":        # wrapper, no sentence anywhere
        body = WRAP
    else:
        raise ValueError(arm)
    return [
        {"role": "system", "content": sys_p},
        {"role": "user", "content": P.USER},
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "c1", "type": "function",
             "function": {"name": "read_file",
                          "arguments": json.dumps({"path": "src/utils.py"})}}]},
        {"role": "tool", "tool_call_id": "c1", "content": body},
    ]

out = []
for arm in ("tag+file", "tag-only"):
    msgs = build(arm)
    for i in range(30):
        t0 = time.time()
        try:
            followed, calls, text = P.judge(P.call(msgs, seed=1000 + i))
            err = None
        except Exception as e:
            followed, calls, text, err = None, [], "", repr(e)
        row = {"arm": arm, "trial": i, "followed": followed, "calls": calls,
               "text_head": text[:300], "err": err, "secs": round(time.time() - t0, 2)}
        out.append(row); print(json.dumps(row), flush=True)
with open("results-de.jsonl", "w", encoding="utf-8") as f:
    for r in out: f.write(json.dumps(r) + "\n")
print("\n=== SUMMARY ===")
for arm in ("tag+file", "tag-only"):
    ok = [r for r in out if r["arm"] == arm and r["err"] is None]
    print(f"{arm:9s} followed {sum(1 for r in ok if r['followed'])}/{len(ok)}")
