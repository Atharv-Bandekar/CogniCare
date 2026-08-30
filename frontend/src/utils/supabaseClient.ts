// frontend/src/utils/supabaseClient.ts
import { createClient } from '@supabase/supabase-js';

// Retrieve public Supabase variables from Next.js environment
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

if (!supabaseUrl || !supabaseAnonKey) {
  console.error("Missing Supabase environment variables on the frontend!");
}

/**
 * Supabase client instance configured for the Next.js frontend.
 * Handles user sessions, login, signup, and token management.
 *
 * If the public env vars are not configured yet, fall back to placeholder
 * values so the app still renders (auth calls will fail gracefully) instead
 * of crashing at module load with "supabaseUrl is required".
 */
export const supabase = createClient(
  supabaseUrl || 'http://localhost:54321',
  supabaseAnonKey || 'missing-anon-key'
);
