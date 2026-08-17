-- Migration 0002: CogniCare V2 Schema
-- Purpose: Introduces the core tables for the WhatsApp-first cognitive engagement loop,
-- including elder profiles, daily interactions, pgvector memories, and caregiver recommendations.

-- 1. Elder Profile: Replaces bare user linkage and holds core configuration
CREATE TABLE public.elder_profiles (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  caregiver_user_id uuid NOT NULL REFERENCES auth.users(id),
  name text NOT NULL,
  whatsapp_number text NOT NULL UNIQUE,
  preferred_language text NOT NULL DEFAULT 'en',
  preferred_interaction_time time NOT NULL,
  timezone text NOT NULL DEFAULT 'Asia/Kolkata',
  proximity text NOT NULL CHECK (proximity IN ('remote','live_in','nearby')),
  mobility_constraints jsonb DEFAULT '[]', -- e.g. ["uses_cane","seated_only"]
  personal_context jsonb DEFAULT '{}', -- grandchildren, hometown, hobbies, etc.
  cycle_day int NOT NULL DEFAULT 1, -- 1-7 rotation pointer
  created_at timestamptz DEFAULT now()
);

-- 2. Daily Interaction: Extends and replaces the old conversations table
CREATE TABLE public.daily_interactions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  elder_id uuid NOT NULL REFERENCES elder_profiles(id),
  interaction_date date NOT NULL DEFAULT current_date,
  domain text NOT NULL, -- episodic_memory, semantic_memory, etc.
  question text NOT NULL,
  twilio_message_sid text UNIQUE, -- Used for webhook idempotency
  raw_response text,
  transcript_source text CHECK (transcript_source IN ('text','voice')),
  language text,
  created_at timestamptz DEFAULT now()
);

-- 3. Interaction Insights: Granular ML evaluation scores
CREATE TABLE public.interaction_insights (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  interaction_id uuid REFERENCES daily_interactions(id),
  sentiment_label text,
  sentiment_score numeric,
  engagement_level text, -- low/medium/high
  engagement_score numeric,
  response_depth text,
  topics jsonb DEFAULT '[]',
  safety_flag boolean DEFAULT false, -- True if manual caregiver check-in is advised
  created_at timestamptz DEFAULT now()
);

-- 4. Memory Store (RAG): Vector embeddings for context collision
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE public.memories (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  elder_id uuid NOT NULL REFERENCES elder_profiles(id),
  source_interaction_id uuid REFERENCES daily_interactions(id),
  category text, -- people/places/events/hobbies/family_stories
  content text NOT NULL,
  embedding vector(384), -- Dimension matches HF microsoft/deberta-v3-small / MiniLM
  created_at timestamptz DEFAULT now()
);
-- Index for faster cosine similarity searches
CREATE INDEX ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 5. Recommendations: Actionable tasks generated for the caregiver
CREATE TABLE public.recommendations (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  elder_id uuid NOT NULL REFERENCES elder_profiles(id),
  interaction_id uuid REFERENCES daily_interactions(id),
  recommendation_text text NOT NULL,
  reason text,
  status text DEFAULT 'pending' CHECK (status IN ('pending','done','dismissed','timed_out')),
  created_at timestamptz DEFAULT now(),
  resolved_at timestamptz
);

-- 6. Family Interactions: Captures caregiver dashboard interactions
CREATE TABLE public.family_interactions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  recommendation_id uuid REFERENCES recommendations(id),
  caregiver_user_id uuid REFERENCES auth.users(id),
  reaction text, -- done/dismiss
  caregiver_suggestion text,
  incorporated_into_interaction_id uuid REFERENCES daily_interactions(id),
  created_at timestamptz DEFAULT now()
);

-- 7. Weekly Reports: Aggregated summaries generated every 7 days
CREATE TABLE public.weekly_reports (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  elder_id uuid NOT NULL REFERENCES elder_profiles(id),
  cycle_start date NOT NULL,
  cycle_end date NOT NULL,
  engagement_trend jsonb,
  domains_completed jsonb,
  recurring_topics jsonb,
  emotional_trend jsonb,
  family_engagement jsonb,
  created_at timestamptz DEFAULT now()
);

-- Enable Row Level Security (RLS) on all new tables
ALTER TABLE elder_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE interaction_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_reports ENABLE ROW LEVEL SECURITY;


-- Function to perform pgvector cosine similarity searches for memories
CREATE OR REPLACE FUNCTION match_memories (
  query_embedding vector(384),
  target_elder_id uuid,
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  content text,
  category text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    memories.id,
    memories.content,
    memories.category,
    1 - (memories.embedding <=> query_embedding) AS similarity
  FROM memories
  WHERE memories.elder_id = target_elder_id
    AND 1 - (memories.embedding <=> query_embedding) > match_threshold
  ORDER BY memories.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;