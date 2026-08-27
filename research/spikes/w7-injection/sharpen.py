import re
src = open(r"D:/dev/claudette/crates/claudette/src/redact.rs", encoding="utf-8").read()
body = src[src.index("RULES.get_or_init"):src.index("/// Mask credential-shaped")]
rx = [re.compile(p) for p in re.findall(r'r\(r#?"(.*?)"#?\)', body, re.S)]
def red(s):
    for r in rx: s = r.sub("<REDACTED>", s)
    return s
pairs = [
 ("backstop name anchoring", "API_KEY=AbCdEf0123456789AbCd", "XAI_API_KEY=AbCdEf0123456789AbCd"),
 ("backstop separator",      "api-key=iHhK7yt72eXyYndmyQJ3u9pVw", "--api-key iHhK7yt72eXyYndmyQJ3u9pVw"),
 ("AWS: id vs secret",       "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
]
for label, a, b in pairs:
    print(f"{label}:")
    for s in (a, b):
        o = red(s)
        print(f"   {'MASKED' if o!=s else 'LEAKED'}  {s!r:52s} -> {o}")
