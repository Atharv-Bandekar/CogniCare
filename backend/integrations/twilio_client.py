"""
Twilio WhatsApp integration.

Uses the Twilio REST API directly over `requests` + HTTP basic auth, matching the
pattern already used by weather.py / agents/base.py / agents/embeddings.py. This
keeps the dependency surface small (no twilio SDK required).

Env vars:
    TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN
    TWILIO_WHATSAPP_FROM   e.g. "whatsapp:+14155238886"
"""
import os
import base64
import hashlib
import hmac
import logging

import requests

logger = logging.getLogger(__name__)

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"
REQUEST_TIMEOUT = 15


def _credentials():
    """Returns (account_sid, auth_token) or (None, None) if not configured."""
    return os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")


def _normalize_whatsapp(number: str) -> str:
    """Ensures the number carries Twilio's required 'whatsapp:' channel prefix."""
    number = (number or "").strip()
    if not number:
        return ""
    return number if number.startswith("whatsapp:") else f"whatsapp:{number}"


def send_whatsapp_message(to_number: str, body: str) -> dict | None:
    """
    Sends a WhatsApp message via Twilio.

    Args:
        to_number (str): Destination number, with or without the 'whatsapp:' prefix.
        body (str): Message text.

    Returns:
        dict | None: Twilio's JSON response (contains 'sid'), or None on failure.

    WHY: Returns None instead of raising so callers (Celery tasks) can decide
    whether a send failure is retryable without unwinding the whole pipeline.
    """
    account_sid, auth_token = _credentials()
    from_number = _normalize_whatsapp(os.getenv("TWILIO_WHATSAPP_FROM", ""))

    if not account_sid or not auth_token or not from_number:
        logger.error("Twilio is not configured (missing SID/token/from). Message not sent.")
        return None

    if not body or not body.strip():
        logger.warning("Refusing to send an empty WhatsApp message.")
        return None

    url = f"{TWILIO_API_BASE}/Accounts/{account_sid}/Messages.json"
    payload = {
        "To": _normalize_whatsapp(to_number),
        "From": from_number,
        "Body": body,
    }

    try:
        response = requests.post(
            url, data=payload, auth=(account_sid, auth_token), timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        logger.info("WhatsApp message sent (sid=%s).", data.get("sid"))
        return data
    except Exception as exc:
        logger.error("Failed to send WhatsApp message: %s", exc)
        return None


def download_media(media_url: str) -> bytes | None:
    """
    Downloads a media attachment (e.g. a WhatsApp voice note) from Twilio.

    Twilio media URLs require the same basic auth as the REST API.

    Args:
        media_url (str): The MediaUrl0 value from the inbound webhook.

    Returns:
        bytes | None: Raw media bytes, or None on failure.
    """
    account_sid, auth_token = _credentials()
    if not media_url:
        return None
    if not account_sid or not auth_token:
        logger.error("Twilio is not configured; cannot download media.")
        return None

    try:
        # allow_redirects: Twilio 307-redirects media URLs to signed storage URLs.
        response = requests.get(
            media_url, auth=(account_sid, auth_token), timeout=REQUEST_TIMEOUT, allow_redirects=True
        )
        response.raise_for_status()
        return response.content
    except Exception as exc:
        logger.error("Failed to download Twilio media: %s", exc)
        return None


def validate_twilio_signature(url: str, params: dict, signature: str) -> bool:
    """
    Verifies Twilio's X-Twilio-Signature header so we only trust genuine webhooks.

    Twilio's scheme: concatenate the full request URL with each POST parameter
    sorted by key (key then value, no separators), HMAC-SHA1 it with the auth
    token, and base64-encode the digest.

    Args:
        url (str): The exact webhook URL Twilio requested (including scheme/host).
        params (dict): The POST form parameters.
        signature (str): Value of the X-Twilio-Signature header.

    Returns:
        bool: True if the signature is valid.

    WHY implemented here instead of via the twilio SDK: the SDK isn't a dependency,
    and this is ~10 lines of stdlib hmac.
    """
    _, auth_token = _credentials()
    if not auth_token:
        logger.error("TWILIO_AUTH_TOKEN missing; cannot validate signature.")
        return False
    if not signature:
        return False

    payload = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    digest = hmac.new(auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode("utf-8")

    # Constant-time comparison to avoid leaking timing information.
    return hmac.compare_digest(expected, signature)
