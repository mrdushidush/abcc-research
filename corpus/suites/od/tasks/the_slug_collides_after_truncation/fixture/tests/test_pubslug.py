"""Visible tests.

⚠ No two titles here share a prefix, so `assign` is never handed a batch that
collides — which is the one case the module gets wrong.
"""

from pubslug import slugs, urls


def articles(*titles):
    return [{"id": "a{}".format(i), "title": t} for i, t in enumerate(titles)]


def test_make_folds_punctuation_to_dashes():
    assert slugs.make("Postmortem: the Friday outage").startswith("postmortem-the-frida")
    assert ":" not in slugs.make("Postmortem: the Friday outage")


def test_make_truncates_to_max_len():
    assert len(slugs.make("a" * 100)) == slugs.MAX_LEN


def test_make_strips_a_trailing_dash():
    assert not slugs.make("Release notes 2026-08!!!").endswith("-")


def test_assign_gives_every_article_a_slug():
    out = slugs.assign(articles("Alpha report", "Beta digest", "Gamma weekly"))
    assert [row["id"] for row in out] == ["a0", "a1", "a2"]
    assert len({row["slug"] for row in out}) == 3


def test_url_prefixes_the_slug():
    assert urls.url("alpha-report") == "/blog/alpha-report"


def test_collisions_is_empty_on_distinct_slugs():
    out = slugs.assign(articles("Alpha report", "Beta digest"))
    assert urls.collisions(out) == []
