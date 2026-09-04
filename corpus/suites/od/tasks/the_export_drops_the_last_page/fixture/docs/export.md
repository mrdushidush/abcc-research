# The nightly export

The result set is cut into pages of ten because the downstream loader takes one
page per request, and because a single un-paged body took it down in March.

**The last page is usually short.** A result set is not a multiple of the page
size except by accident, and the final page is the one that carries whatever is
left over.

## The audit

`expo.audit.check` compares the rows the export was **asked** for against the
rows that reached the sink. That is the only comparison worth making: a check
that compares the sink against something derived from the sink passes on an
empty export, which is the failure it exists to catch.
