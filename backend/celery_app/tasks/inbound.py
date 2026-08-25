"""
Background tasks for processing inbound WhatsApp messages (LEGACY - kept for reference).

This module is retained for historical purposes. The production pipeline is now
Telegram-only and uses backend.celery_app.tasks.telegram_bot with shared helpers
from backend.celery_app.tasks.shared_helpers.
"""
import logging

logger = logging.getLogger(__name__)

# This file intentionally left mostly empty for Telegram-only deployment.
# The shared pipeline logic lives in shared_helpers.py and is used by telegram_bot.py.
# If WhatsApp is re-enabled in the future, this file can be restored from git history.