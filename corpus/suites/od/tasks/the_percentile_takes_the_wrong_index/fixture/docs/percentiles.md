# Percentiles

**Nearest rank, one-indexed.** The p-th percentile of n sorted observations is
the one at rank `ceil(p × n)`, counting from 1. There is no interpolation: the
number we report is always a number somebody's request actually took.

Written as a zero-based index that is `ceil(p × n) - 1`.

⚠ `int(p × n)` is that rank only when `p × n` lands exactly on a whole number,
and is one short of it every other time. On a twenty-sample window at p95 the
product is 19.0 and a zero-based `int` gives index 19 — the last element, which
is the maximum and not a percentile at all. Subtracting one from `int(p × n)`
fixes that window and is wrong on every window where the product is not whole:
seven samples at p95 is 6.65, whose rank is 7 and whose `int`-minus-one is 5.
