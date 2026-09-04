# The SKU migration

Canonical SKU is four digits: `1101`. Until the 2024 migration the warehouse
system prefixed everything with `OLD-`, and that spelling has not gone away —
it arrives from bookmarked links, printed catalogues, two partner feeds and the
warehouse's own adjustment API, which still emits it.

**Every SKU that enters this service from outside is in an accepted spelling,
not necessarily the canonical one.** `catalog.skus.normalize()` folds any of
them — the prefix, and case — to the canonical form. Anything that looks a SKU
up in the product index has to fold it first, because the index is keyed on the
canonical form and nothing else.

The export was written after the migration and folds. The rest of the package
was written before it and does not.
