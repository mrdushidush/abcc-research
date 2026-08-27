"""Extract redact.rs's patterns FROM SOURCE (no hand transcription) and test
them against credential shapes this project actually handles."""
import re, sys
src = open(r"D:/dev/claudette/crates/claudette/src/redact.rs", encoding="utf-8").read()
body = src[src.index("RULES.get_or_init"):src.index("/// Mask credential-shaped")]
pats = re.findall(r'r\(r#?"(.*?)"#?\)', body, re.S)
print(f"extracted {len(pats)} patterns from source\n")
compiled = []
for p in pats:
    try:
        compiled.append((p, re.compile(p)))
    except re.error as e:
        print(f"  [python cannot compile, skipped] {p[:50]}… ({e})")

CASES = [
  ("Anthropic key (env line)",      "ANTHROPIC_API_KEY=sk-ant-api03-AbCdEf0123456789_-XyZaBcDeFgHi"),
  ("xAI/Grok key (env line)",       "XAI_API_KEY=xai-AbCdEf0123456789AbCdEf0123456789AbCd"),
  ("OpenAI key (env line)",         "OPENAI_API_KEY=sk-proj-AbCdEf0123456789AbCdEfGh"),
  ("GitHub classic PAT",            "GITHUB_TOKEN=ghp_ABCDEFGHIJKLMNOP0123456789"),
  ("AWS secret ACCESS KEY value",   "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
  ("AWS access key id",             "aws_access_key_id = AKIAIOSFODNN7EXAMPLE"),
  ("HuggingFace token",             "HF_TOKEN=hf_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"),
  ("LM Studio / llama-server key",  "--api-key iHhK7yt72eXyYndmyQJ3u9pVw-bpgJ2P_NiPaoM2l9Q"),
  ("Postgres URL w/ password",      "DATABASE_URL=postgres://app:s3cr3tp4ssw0rd@db.internal:5432/prod"),
  ("Generic .env password line",    "DB_PASSWORD=hunter2hunter2hunter2"),
  ("Telegram bot token",            "TELEGRAM_BOT_TOKEN=8012345678:AAH1a2B3c4D5e6F7g8H9i0JkLmNoPqRsTuV"),
  ("Bearer header",                 "Authorization: Bearer abc123DEF456ghi789jkl"),
  ("JWT",                           "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r"),
]

def redact(s):
    for p, rx in compiled:
        s = rx.sub("<REDACTED>", s)
    return s

miss = []
for label, sample in CASES:
    out = redact(sample)
    hit = out != sample
    print(f"{'MASKED  ' if hit else 'LEAKED  '} {label:32s} -> {out}")
    if not hit:
        miss.append(label)
print(f"\n{len(miss)} of {len(CASES)} leak: " + ", ".join(miss))
