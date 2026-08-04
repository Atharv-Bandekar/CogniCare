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
 */
export const supabase = createClient(supabaseUrl, supabaseAnonKey);