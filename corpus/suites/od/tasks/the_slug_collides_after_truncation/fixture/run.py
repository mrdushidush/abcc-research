"""Assign slugs to the August articles.

    python run.py

The line shapes are read by the catalogue build. They are a contract.
"""

import json
import sys

from pubslug import slugs, urls

DATA = "data/articles.json"


def main(argv):
    with open(DATA, encoding="utf-8") as handle:
        articles = json.load(handle)

    assigned = slugs.assign(articles)
    by_id = {row["id"]: row["slug"] for row in assigned}
    clashes = urls.collisions(assigned)

    print("SLUG RUN")
    print("articles: {}".format(len(assigned)))
    print("distinct_slugs: {}".format(len({row["slug"] for row in assigned})))
    print("collisions: {}".format(len(clashes)))
    print("longest_slug: {}".format(max(len(row["slug"]) for row in assigned)))
    print("slug_a1: {}".format(by_id["a1"]))
    print("slug_a4: {}".format(by_id["a4"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
