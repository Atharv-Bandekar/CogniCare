-- Migration 0003: Telegram demo channel
-- Purpose: allow an elder profile to be resolved (or auto-provisioned) from a
-- Telegram chat, so a publicly reachable Telegram bot can serve a walk-up user
-- (e.g. a recruiter visiting the deployment) without any pre-registration.
--
-- WhatsApp-only elders keep telegram_chat_id NULL; Telegram-only demo elders keep
-- a synthetic whatsapp_number ('tg:<chat_id>') because whatsapp_number is NOT NULL
-- UNIQUE in 0002 and we don't want Telegram to depend on a real phone number.

ALTER TABLE public.elder_profiles
  ADD COLUMN IF NOT EXISTS telegram_chat_id text;

-- One elder per Telegram chat. Partial index so the many NULLs (WhatsApp elders)
-- don't collide on the UNIQUE constraint.
CREATE UNIQUE INDEX IF NOT EXISTS elder_profiles_telegram_chat_id_key
  ON public.elder_profiles (telegram_chat_id)
  WHERE telegram_chat_id IS NOT NULL;
