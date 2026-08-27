-- Migration 0006: Add ON DELETE CASCADE to interaction_insights foreign key
-- Purpose: Allow deleting daily_interactions to cascade to insights

-- interaction_insights.interaction_id -> daily_interactions.id
ALTER TABLE public.interaction_insights
DROP CONSTRAINT interaction_insights_interaction_id_fkey,
ADD CONSTRAINT interaction_insights_interaction_id_fkey
    FOREIGN KEY (interaction_id) REFERENCES public.daily_interactions(id) ON DELETE CASCADE;