-- Migration 0005: Add ON DELETE CASCADE to elder_profiles foreign keys
-- Purpose: Allow deleting an elder profile to cascade and clean up all related data

-- 1. daily_interactions.elder_id -> elder_profiles.id
ALTER TABLE public.daily_interactions
DROP CONSTRAINT daily_interactions_elder_id_fkey,
ADD CONSTRAINT daily_interactions_elder_id_fkey
    FOREIGN KEY (elder_id) REFERENCES public.elder_profiles(id) ON DELETE CASCADE;

-- 2. memories.elder_id -> elder_profiles.id
ALTER TABLE public.memories
DROP CONSTRAINT memories_elder_id_fkey,
ADD CONSTRAINT memories_elder_id_fkey
    FOREIGN KEY (elder_id) REFERENCES public.elder_profiles(id) ON DELETE CASCADE;

-- 3. recommendations.elder_id -> elder_profiles.id
ALTER TABLE public.recommendations
DROP CONSTRAINT recommendations_elder_id_fkey,
ADD CONSTRAINT recommendations_elder_id_fkey
    FOREIGN KEY (elder_id) REFERENCES public.elder_profiles(id) ON DELETE CASCADE;

-- 4. weekly_reports.elder_id -> elder_profiles.id
ALTER TABLE public.weekly_reports
DROP CONSTRAINT weekly_reports_elder_id_fkey,
ADD CONSTRAINT weekly_reports_elder_id_fkey
    FOREIGN KEY (elder_id) REFERENCES public.elder_profiles(id) ON DELETE CASCADE;