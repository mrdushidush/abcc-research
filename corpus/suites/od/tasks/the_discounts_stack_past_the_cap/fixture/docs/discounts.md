# Discounts

Discount percentages **add**. A 20% seasonal code and a 10% loyalty code are
30% off, which is what both codes say on the tin and what the customer expects
when they read them next to each other in the basket.

They do not compound. Applying 20% and then 10% of what is left is 28%, which
is a number nobody promised and which changes if the codes are applied in a
different order.

## The cap

**`MAX_TOTAL_PCT` is the floor margin finance set: no order goes out at more
than 50% off, whatever the codes add up to.** It is a cap on the TOTAL, not a
limit per code, and it is the reason the codes can be generous individually.

Compounding hides the cap by accident — three 25% codes compound to 58% off,
which never reaches 50% of the subtotal and so never trips anything — which is
how a rule can be missing from the code for a year without anybody noticing.
