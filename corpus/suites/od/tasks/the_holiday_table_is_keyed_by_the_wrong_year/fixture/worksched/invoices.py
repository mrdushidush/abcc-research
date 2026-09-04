"""Payment due dates, on the same calendar."""

from . import businessdays


def due(invoice):
    return businessdays.add_business_days(
        businessdays.parse(invoice["issued"]), invoice["terms_days"]
    )


def due_dates(invoices):
    return [(i["id"], due(i)) for i in invoices]
