"""Product catalogue.

Unit prices carry FOUR decimal places on purpose. Several lines are priced per
unit in fractions of a penny (cable by the metre, print by the sheet), and
rounding the catalogue price to the cent would change what a bulk order costs.
That is why a line total needs rounding and a unit price does not.
"""


class Entry:
    def __init__(self, sku, description, unit_price, category):
        self.sku = sku
        self.description = description
        self.unit_price = unit_price
        self.category = category

    def __repr__(self):
        return "Entry(%s, %.4f)" % (self.sku, self.unit_price)


CATALOG = {
    e.sku: e
    for e in [
        Entry("CBL-CAT6-M", "Cat6 cable, per metre", 0.8725, "cable"),
        Entry("CBL-FIB-M", "OM4 fibre, per metre", 2.1450, "cable"),
        Entry("PRN-A4-SH", "A4 print, per sheet", 0.0375, "print"),
        Entry("PRN-A3-SH", "A3 print, per sheet", 0.0725, "print"),
        Entry("SW-8P-GB", "8-port gigabit switch", 47.9900, "hardware"),
        Entry("SW-24P-GB", "24-port gigabit switch", 189.5000, "hardware"),
        Entry("PSU-150W", "150W power supply", 33.3300, "hardware"),
        Entry("RACK-1U", "1U rack shelf", 21.6650, "hardware"),
        Entry("LIC-SEAT-YR", "Seat licence, per year", 119.9900, "licence"),
        Entry("SUP-HR", "Support, per hour", 74.5000, "service"),
        Entry("INST-CALL", "Installation call-out", 95.0000, "service"),
        Entry("CONN-RJ45", "RJ45 connector", 0.2150, "cable"),
    ]
}


def get(sku):
    return CATALOG.get(sku)


def all_entries():
    return [CATALOG[k] for k in sorted(CATALOG)]


def by_category(category):
    return [e for e in all_entries() if e.category == category]


def categories():
    return sorted({e.category for e in CATALOG.values()})
