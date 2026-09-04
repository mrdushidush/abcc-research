"""Visible tests.

⚠ Every email in the incoming records built here is already folded, so the
importer is never asked what it does with the spelling the partner feed sends.
`fold_email` is covered directly and is correct.
"""

from crm import keys, link, merge, store as store_mod


def store():
    s = store_mod.Store()
    s.by_key["ana@example.com"] = store_mod.Customer("c1", "ana@example.com", "Ana")
    s.by_key["bo@example.com"] = store_mod.Customer("c2", "bo@example.com", "Bo")
    return s


def record(order, email):
    return {"order": order, "email": email, "amount_cents": 100}


def test_fold_email_strips_and_lowers():
    assert keys.fold_email(" Ana@Example.com ") == "ana@example.com"
    assert keys.fold_email("ana@example.com") == "ana@example.com"


def test_merge_attaches_an_order_to_a_known_customer():
    s = store()
    assert merge.merge(s, [record("x1", "ana@example.com")]) == []
    assert s.get("ana@example.com").orders == ["x1"]


def test_merge_creates_a_customer_for_a_new_address():
    s = store()
    created = merge.merge(s, [record("x1", "di@example.com")])
    assert len(created) == 1
    assert s.get("di@example.com").orders == ["x1"]


def test_link_check_counts_distinct_people():
    assert link.check(store()) == 2


def test_link_check_counts_a_new_row_too():
    s = store()
    merge.merge(s, [record("x1", "di@example.com")])
    assert link.check(s) == 3
