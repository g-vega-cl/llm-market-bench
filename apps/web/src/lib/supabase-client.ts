import { createBrowserClient } from '@supabase/ssr';

export function getSupabaseBrowserClient() {
    const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
    const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

    return createBrowserClient(supabaseUrl!, supabaseAnonKey!);
}
