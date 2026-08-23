"""
Tests for the Twilio webhook handler (Phase 3B).

The handler must stay fast and dumb: authenticate the request, hand the payload to
Celery, and return TwiML immediately. Anything slow belongs in the worker.
"""
import asyncio
from unittest.mock import patch

from backend.webhooks.twilio_webhook import twilio_inbound, twilio_status, EMPTY_TWIML

MODULE = "backend.webhooks.twilio_webhook"


class FakeRequest:
    """Stands in for a Starlette Request with an awaitable .form()."""

    def __init__(self, form=None, url="https://cognicare.example/twilio/inbound"):
        self._form = form or {}
        self.url = url

    async def form(self):
        return self._form


FORM = {
    "From": "whatsapp:+919000000001",
    "Body": "I had a lovely morning.",
    "MessageSid": "SM123",
}


def _post(signature="sig", form=None, **overrides):
    """Invokes the handler the way FastAPI would, and returns the Response."""
    request = FakeRequest(form if form is not None else FORM)
    kwargs = {
        "request": request,
        "From": FORM["From"],
        "Body": FORM["Body"],
        "MediaUrl0": None,
        "MessageSid": FORM["MessageSid"],
        "x_twilio_signature": signature,
    }
    kwargs.update(overrides)
    return asyncio.run(twilio_inbound(**kwargs))


def test_valid_signature_queues_the_message_and_returns_twiml():
    with patch(f"{MODULE}.validate_twilio_signature", return_value=True), \
         patch(f"{MODULE}.process_inbound_message") as m_task:
        response = _post()

    assert response.status_code == 200
    assert response.content == EMPTY_TWIML
    assert response.media_type == "application/xml"

    m_task.apply_async.assert_called_once()
    payload = m_task.apply_async.call_args.kwargs["args"][0]
    assert payload == {
        "From": FORM["From"],
        "Body": FORM["Body"],
        "MediaUrl0": None,
        "MessageSid": "SM123",
    }
    assert m_task.apply_async.call_args.kwargs["queue"] == "inbound"


def test_invalid_signature_is_rejected_with_403():
    """403 (not 200) so Twilio stops retrying a request we will never accept."""
    with patch(f"{MODULE}.validate_twilio_signature", return_value=False), \
         patch(f"{MODULE}.process_inbound_message") as m_task:
        response = _post(signature="forged")

    assert response.status_code == 403
    m_task.apply_async.assert_not_called()


def test_missing_signature_header_is_rejected():
    with patch(f"{MODULE}.validate_twilio_signature", return_value=False) as m_validate, \
         patch(f"{MODULE}.process_inbound_message") as m_task:
        response = _post(x_twilio_signature=None)

    assert response.status_code == 403
    # A missing header must still reach the validator as an empty string, not None.
    assert m_validate.call_args.args[2] == ""
    m_task.apply_async.assert_not_called()


def test_signature_is_checked_against_the_configured_public_url():
    """Behind a tunnel or proxy, request.url is not the URL Twilio signed."""
    with patch.dict("os.environ", {"TWILIO_WEBHOOK_URL": "https://public.example/twilio/inbound"}), \
         patch(f"{MODULE}.validate_twilio_signature", return_value=True) as m_validate, \
         patch(f"{MODULE}.process_inbound_message"):
        _post()

    assert m_validate.call_args.args[0] == "https://public.example/twilio/inbound"


def test_all_form_fields_are_signed_not_just_the_declared_ones():
    """Twilio signs every POST field, so the whole form must go to the validator."""
    form = {**FORM, "AccountSid": "ACxxx", "NumMedia": "0"}
    with patch(f"{MODULE}.validate_twilio_signature", return_value=True) as m_validate, \
         patch(f"{MODULE}.process_inbound_message"):
        _post(form=form)

    assert m_validate.call_args.args[1] == {k: str(v) for k, v in form.items()}


def test_validation_can_be_disabled_for_local_tunnel_testing():
    with patch.dict("os.environ", {"TWILIO_VALIDATE_SIGNATURE": "false"}), \
         patch(f"{MODULE}.validate_twilio_signature") as m_validate, \
         patch(f"{MODULE}.process_inbound_message") as m_task:
        response = _post(signature=None)

    assert response.status_code == 200
    m_validate.assert_not_called()
    m_task.apply_async.assert_called_once()


def test_validation_is_enabled_by_default():
    """Fail closed: an unset env var must mean signatures ARE checked."""
    with patch.dict("os.environ", {}, clear=False), \
         patch(f"{MODULE}.validate_twilio_signature", return_value=False) as m_validate, \
         patch(f"{MODULE}.process_inbound_message"):
        import os
        os.environ.pop("TWILIO_VALIDATE_SIGNATURE", None)
        response = _post()

    m_validate.assert_called_once()
    assert response.status_code == 403


def test_status_callback_always_acknowledges():
    request = FakeRequest({"MessageSid": "SM123", "MessageStatus": "delivered"})
    response = asyncio.run(twilio_status(request))
    assert response.status_code == 200
