# Slugs

A slug is the title, lower-cased, with every run of non-alphanumeric characters
folded to a single dash, **truncated to twenty characters**.

Twenty is not ours to change. The print catalogue prints the URL and its column
is twenty characters wide; a longer slug is truncated again at the other end,
which produces a URL that does not resolve and that nobody can see is wrong
until a reader types it.

## Collisions

Truncation makes collisions **ordinary**, not exceptional. Any two titles that
begin the same way land on the same slug, and a publication that runs a series
produces those constantly.

Where a slug is already taken, the later article gets a numeric suffix: `-2`,
then `-3`. That is part of assigning a slug rather than a repair for an unlucky
case — a longer truncation only moves the collision to longer titles.
