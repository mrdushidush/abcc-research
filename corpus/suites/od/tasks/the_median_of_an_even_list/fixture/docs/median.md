# Median, in the reporting standard

For an odd number of values the median is the middle one.

For an **even** number it is the midpoint of the two middle values, **rounded
half up**. Both halves matter and both are the standard finance reconciles
against:

* Taking the upper of the two middles is not a median. It is the 75th-ish
  percentile of a four-element cohort and it reads high on every even month.
* Truncating the midpoint biases every even-sized cohort **downward by half a
  cent**. Over a reconciliation of thousands of cohorts that is a real number
  and it is always in the same direction, which is what makes it visible.

Everything here is integer cents. There is no float in the reporting path.
