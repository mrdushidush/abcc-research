"""Visible tests — each channel's own eligibility rule, and the helper alone.

⚠ Nothing here sends a SUPPRESSED contact through a channel, which is why the
suite is green on code that mails people who asked us to stop.
"""

from outbound import model, newsletter, promo_sms, push, suppression, winback


def contact(ident, email="x@example.com", phone="+1", token="t", dnc=False, segment="active"):
    return model.Contact(
        {
            "id": ident,
            "email": email,
            "phone": phone,
            "push_token": token,
            "do_not_contact": dnc,
            "segment": segment,
        }
    )


def test_suppression_reads_the_flag():
    assert suppression.is_suppressed(contact("a", dnc=True)) is True
    assert suppression.is_suppressed(contact("a", dnc=False)) is False


def test_newsletter_needs_an_email():
    assert newsletter.audience([contact("a"), contact("b", email=None)]) == ["a"]


def test_winback_is_lapsed_only():
    people = [contact("a", segment="lapsed"), contact("b", segment="active")]
    assert winback.audience(people) == ["a"]


def test_promo_sms_needs_a_phone():
    assert promo_sms.audience([contact("a"), contact("b", phone=None)]) == ["a"]


def test_push_needs_a_token():
    assert push.audience([contact("a"), contact("b", token=None)]) == ["a"]


def test_newsletter_skips_a_suppressed_contact():
    assert newsletter.audience([contact("a", dnc=True), contact("b")]) == ["b"]
