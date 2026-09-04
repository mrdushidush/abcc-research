# Contact policy

`contacts.do_not_contact` is set when someone tells us to stop. Legal's wording,
and it is deliberately short:

> When a contact sets do-not-contact we stop sending them marketing. Not less
> often, not on a different channel. We stop.

Transactional mail — receipts, password resets, security notices — is not
marketing and is not covered. Nothing in `outbound/` is transactional; every
module under it is a marketing channel.

`outbound.suppression.is_suppressed(contact)` is the check. It exists so that no
channel has to hold the policy in its head. It predates three of the four
channels in this package.
