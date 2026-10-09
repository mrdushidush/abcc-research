# Contributing

This repository is a research record, so the most useful contribution is a
**check**: a finding that does not reproduce, a number that does not match the
document it comes from, or a citation that does not resolve.

## A finding that doesn't hold

Open an issue with the **"A finding doesn't reproduce"** template. What makes a
report useful:

- **Which finding**, and what `python research/tools/fledger.py show F753` says
  about it. A later finding may already have corrected it.
- **What you ran**: the command or script, and the commit of this repository.
- **Your stack**: GPU and VRAM, OS, the serving runtime and its version
  (LM Studio, llama.cpp, ollama), and the model file with its quant.
- **What the finding says, and what you got.**

Every measurement here was taken on one machine, so a result that differs on
other hardware is worth reporting even when it is not a contradiction.

## How a correction lands

Nothing here is rewritten after the fact. If a report holds, the correction is
recorded as a new finding that links to the old one, in
[`research/findings-authored.tsv`](research/findings-authored.tsv), so the old
claim stays readable next to what replaced it.

## Pull requests

- **A typo or a broken link:** send one.
- **Anything that changes what a finding says:** open an issue first. Findings
  are corrected by new findings, not edited.

Security problems in claudette or abcc go to those repositories' private
vulnerability reporting, not here.

## Licence

Code (`corpus/`, `harness/` and every source file) is `MIT OR Apache-2.0`; prose
and data are [CC BY 4.0](LICENSE-CC-BY-4.0). By contributing, you agree your
contribution is licensed the same way.
