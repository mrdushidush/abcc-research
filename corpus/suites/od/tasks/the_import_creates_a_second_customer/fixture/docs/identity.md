# Customer identity

One person is one customer row. The key is the **folded** email address —
`crm.keys.fold_email`, which strips surrounding whitespace and lower-cases —
and `data/store.json` is loaded under exactly that key.

The partner feed does not fold. It sends whatever the partner's own form
collected: mixed case, a trailing space, sometimes both. **Every key that goes
into the store, and every key used to look one up, has to be the folded form.**

`crm.link.check` is the integrity check that runs after every import. It is not
the place identity is decided; it is the place a decision made somewhere else
turns into an exception. Two rows for one person means lifetime value, the churn
model and the support history are all wrong for both of them, which is why it
raises rather than warning.
