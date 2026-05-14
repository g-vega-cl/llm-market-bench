import { createBrowserClient } from '@supabase/ssr';

export function getSupabaseBrowserClient() {
    const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
    const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
    if (!supabaseUrl || !supabaseAnonKey) {
        throw new Error('Missing Supabase environment variables');
    }

    return createBrowserClient(supabaseUrl, supabaseAnonKey);
}
