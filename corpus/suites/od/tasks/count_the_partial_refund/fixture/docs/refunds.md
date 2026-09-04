# Refunds

There are two refund kinds and both take money away from a statement total.

| kind | means |
|---|---|
| `refund` | the whole charge is returned |
| `partial_refund` | part of a charge is returned; `amount_cents` is the part |

`partial_refund` was added with the returns feature. It is not a new concept in
the ledger — it is a refund whose amount happens to be smaller than the charge
it refers to — and `statement.kinds.REFUND_KINDS` is the tuple that says so.

**A total that tests `kind == REFUND` is wrong in the worst direction.** It does
not merely omit a partial refund; it adds it, because the else branch treats
anything that is not a full refund as money coming in. A £30 partial refund
moves a total by £60.
