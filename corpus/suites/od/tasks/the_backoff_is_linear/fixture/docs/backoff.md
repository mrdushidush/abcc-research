# Backoff

A retry waits **twice as long as the one before it**, starting at one second:

    attempt   1   2   3   4   5   6   7   8
    wait      1   2   4   8  16  32  60  60

**and never longer than `MAX_S`, which is sixty seconds.** Both halves of that
sentence are the policy. Doubling without a ceiling is how a queue that was
unhealthy for ninety seconds ends up idle for an hour: the eighth attempt of an
uncapped schedule waits over two minutes, the twelfth waits over an hour, and
nothing is wrong with the upstream by then.

The ceiling is why `MAX_S` exists, and it is the reason the schedule in the
runbook flattens at the end rather than continuing to double.
