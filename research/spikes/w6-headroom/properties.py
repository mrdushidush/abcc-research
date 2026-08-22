"""The property-test rung, priced at its ceiling rather than at its average.

`gentests.py` measures what the champion writes. This measures what a competent
engineer writes with the repository's own documentation open and no sight of the
reference solution — which is the most a property-based rung can be worth on
these three tasks. Both numbers are needed: the ceiling says whether the rung is
worth building at all, and the generated arm says whether the machine can reach
it.

Every invariant below is quoted, in the test's own docstring, from a sentence
that is already in the fixture -- a module docstring or `docs/`. None of them
was written by looking at the reference solution or at the verifier.

Scored exactly like a generated test: red on the unfixed tree, red on the sham,
green on the reference solution, or it does not discriminate.

    python properties.py
"""

import json

import common as C
import gentests as G

OUT = C.HERE / "properties-results.json"


T1 = '''
"""Properties for the job-status vocabulary.

  * status.py: "A job in a terminal status will not change again. Nothing
    should be waiting on it, charging for it as if it were still going, or
    retrying it."
  * summary.py: "Every status the system can produce needs its own bucket -- a
    status that lands in `other` is a status nobody looks at."
"""

from hypothesis import given, settings as hyp_settings, strategies as gen

from jobs import charges, model, retry, sla, status as st, summary

NOW = 100000


def a_job(status_pool=st.ALL):
    return gen.builds(
        model.Job,
        job_id=gen.just("J-000"),
        customer=gen.just("acme"),
        kind=gen.sampled_from(["render", "transcode", "index", "report", "train"]),
        status=gen.sampled_from(list(status_pool)),
        queued_at=gen.integers(min_value=0, max_value=90000),
        started_at=gen.integers(min_value=0, max_value=95000),
        ended_at=gen.integers(min_value=0, max_value=99000),
        cpu_seconds=gen.integers(min_value=0, max_value=5000),
        sla_seconds=gen.integers(min_value=60, max_value=7200),
        attempts=gen.integers(min_value=1, max_value=4),
    )


@given(a_job())
@hyp_settings(max_examples=200, deadline=None)
def test_a_terminal_job_stops_accruing(job):
    """Nothing should be waiting on a terminal job (status.py)."""
    if not job.is_terminal or job.ended_at is None:
        return
    assert sla.finished_at(job, NOW) == job.ended_at


@given(a_job())
@hyp_settings(max_examples=200, deadline=None)
def test_a_terminal_job_is_not_charged_as_if_running(job):
    """Nothing should be charging for it as if it were still going (status.py).

    The narrow, uncontroversial half: a job the operator cancelled produced
    nothing the customer asked to keep.
    """
    if job.status != st.CANCELLED:
        return
    assert charges.is_chargeable(job) is False


@given(a_job())
@hyp_settings(max_examples=200, deadline=None)
def test_a_terminal_job_is_not_retried(job):
    """Nothing should be retrying it (status.py)."""
    if job.status != st.CANCELLED:
        return
    assert retry.should_retry(job) is False


@given(gen.lists(a_job(), min_size=1, max_size=12))
@hyp_settings(max_examples=200, deadline=None)
def test_every_known_status_has_its_own_bucket(jobs):
    """A status that lands in `other` is a status nobody looks at (summary.py)."""
    c = summary.counts(jobs)
    assert sum(c.values()) == len(jobs)
    assert c.get("other", 0) == 0
'''


T2 = '''
"""Properties for invoice rounding.

  * invoice.py, `reconciles`: "A customer doing this by hand is the most common
    source of billing queries, so it must hold for every invoice we issue."
  * the ticket: "every invoice it prints must be internally consistent -- the
    per-line amounts it shows must add up to the total it shows."
"""

from hypothesis import given, settings as hyp_settings, strategies as gen

from billing import catalog, invoice, money, tax

SKUS = sorted(catalog.CATALOG)
REGIONS = sorted(tax.RATES)


def an_order():
    item = gen.fixed_dictionaries({
        "sku": gen.sampled_from(SKUS),
        "qty": gen.integers(min_value=1, max_value=40),
        "discount_rate": gen.sampled_from([0.0, 0.05, 0.1, 0.125, 0.2]),
    })
    return gen.fixed_dictionaries({
        "number": gen.just("INV-9999"),
        "customer": gen.just("acme"),
        "region": gen.sampled_from(REGIONS),
        "items": gen.lists(item, min_size=1, max_size=8),
    })


@given(an_order())
@hyp_settings(max_examples=300, deadline=None)
def test_printed_lines_add_up_to_the_printed_total(order):
    """It must hold for every invoice we issue (invoice.py)."""
    inv = invoice.build(order)
    assert inv.reconciles(), (
        "lines print %.2f, total prints %.2f"
        % (inv.displayed_sum, inv.total)
    )


@given(an_order())
@hyp_settings(max_examples=300, deadline=None)
def test_the_total_is_a_chargeable_amount(order):
    """money.py: to_cents is the only correct way to reduce a computed amount."""
    inv = invoice.build(order)
    assert abs(inv.total - money.from_cents(money.to_cents(inv.total))) < 1e-9
'''


T3 = '''
"""Properties for ingest accounting.

  * ingest.py: "Every rejection is counted against a reason code ... A silent
    drop here is the worst failure mode this pipeline has: the numbers
    downstream stay plausible."
  * the ticket: "the report it prints must account for every usable sample in
    the input file -- not merely avoid crashing."
"""

from hypothesis import given, settings as hyp_settings, strategies as gen

from pipeline import config, constants, ingest

SETTINGS = config.load()


def a_record():
    return gen.fixed_dictionaries({
        "ts": gen.integers(min_value=0, max_value=60000),
        "channel": gen.sampled_from(list(constants.KNOWN_CHANNELS) + ["gremlin"]),
        "value": gen.floats(min_value=-100, max_value=2000, allow_nan=False,
                            allow_infinity=False),
        "flag": gen.sampled_from(["ok", "warn", "bad", "OK", "stale"]),
    })


@given(gen.lists(a_record(), min_size=1, max_size=60))
@hyp_settings(max_examples=200, deadline=None)
def test_every_record_is_either_kept_or_counted(records):
    """A silent drop is the worst failure mode this pipeline has (ingest.py)."""
    accepted = ingest.accept(records, SETTINGS)
    assert len(accepted) + accepted.total_dropped() == len(records), (
        "%d in, %d kept, %d counted as dropped"
        % (len(records), len(accepted), accepted.total_dropped())
    )


@given(gen.lists(a_record(), min_size=1, max_size=60))
@hyp_settings(max_examples=200, deadline=None)
def test_no_drop_is_filed_under_an_unnamed_reason(records):
    """The report prints these verbatim, so they are part of the contract."""
    accepted = ingest.accept(records, SETTINGS)
    for reason in accepted.drops:
        assert reason in constants.DROP_REASONS
'''


FILES = {
    "finish_the_cancelled_status": T1,
    "round_at_the_line_not_the_total": T2,
    "trace_dropped_samples": T3,
}


def main():
    rows = []
    for task_id, src in FILES.items():
        res, disc = G.score(task_id, src.strip() + "\n")
        rows.append({"task": task_id, "scores": res, "discriminates": disc,
                     "source": src})
        v = {k: res[k]["verdict"] for k in res}
        print("%-34s unfixed=%-6s sham=%-6s refsol=%-6s disc=%s"
              % (task_id, v.get("unfixed", "-"), v.get("sham", "-"),
                 v.get("refsol", "-"), disc), flush=True)
        for k in ("unfixed", "sham", "refsol"):
            if k in res:
                print("    %-8s %s" % (k, res[k]["detail"][:120]))
    OUT.write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
