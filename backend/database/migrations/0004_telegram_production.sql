-- Migration 0004: Telegram Production Support
-- Adds telegram_user_id for production elder linking (distinct from demo chat_id)
-- Run this AFTER 0002 and 0003

-- 1. Add telegram_user_id column (Telegram's numeric user ID, not chat_id)
-- This is the stable identifier from Telegram's `from.id` field
ALTER TABLE public.elder_profiles
  ADD COLUMN IF NOT EXISTS telegram_user_id bigint;

-- 2. Add unique constraint for production elders
-- Each Telegram user can only be linked to one elder profile
CREATE UNIQUE INDEX IF NOT EXISTS elder_profiles_telegram_user_id_key
  ON public.elder_profiles (telegram_user_id)
  WHERE telegram_user_id IS NOT NULL;

-- 3. Add column to track onboarding method
-- 'demo' = auto-provisioned via chat_id (recruiter demo)
-- 'production' = linked via deep-link with telegram_user_id (real elder)
ALTER TABLE public.elder_profiles
  ADD COLUMN IF NOT EXISTS onboarding_method text
  CHECK (onboarding_method IN ('demo', 'production'))
  DEFAULT 'production';

-- 4. Update existing demo elders (from migration 0003) to have onboarding_method = 'demo'
UPDATE public.elder_profiles
  SET onboarding_method = 'demo'
  WHERE telegram_chat_id IS NOT NULL
  AND telegram_user_id IS NULL;

-- 5. Index for demo lookup (chat_id) - already exists from 0003
-- Index for production lookup (user_id) - created above

-- 6. Comment for clarity
COMMENT ON COLUMN public.elder_profiles.telegram_user_id IS 'Telegram numeric user ID (from.from.id) for production elders';
COMMENT ON COLUMN public.elder_profiles.telegram_chat_id IS 'Telegram chat ID for demo elders (auto-provisioned)';
COMMENT ON COLUMN public.elder_profiles.onboarding_method IS 'demo = recruiter demo auto-provisioned; production = caregiver-onboarded via deep-link';