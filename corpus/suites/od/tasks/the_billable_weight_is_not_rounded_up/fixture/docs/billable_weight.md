# Billable weight

Weights are integers in tenths of a kilo, so nothing in the money path is a
float. `22` is 2.2 kg.

The carrier bills in **half-kilo steps, rounded up**. Any part of a step is a
whole step: 2.1 kg is billed as 2.5, and so is 2.4, and so is 2.5. There is no
tolerance, no grace and no rounding to nearest — those are all things this
service invented at various points and all of them cost money, because every one
of them quotes at or below what the carrier charges and the difference is ours.

`shiprate.weights.billable` is where that rule lives, and it is the only place
in the service that decides it.
