import { createClient } from '@supabase/supabase-js';

export const DEFAULT_ARCHIVE_DB_URL = 'https://benchify-archive-db.clvg.uk';

const STATELESS_DB_OPTIONS = {
    auth: {
        persistSession: false,
        autoRefreshToken: false,
        detectSessionInUrl: false,
    },
};

export function getDbServerClient(options?: { useServiceRole?: boolean }) {
    const dbUrl =
        process.env.ARCHIVE_DB_URL || process.env.VITE_ARCHIVE_DB_URL || DEFAULT_ARCHIVE_DB_URL;
    const anonKey =
        process.env.ARCHIVE_DB_ANON_KEY ||
        process.env.VITE_ARCHIVE_DB_ANON_KEY ||
        process.env.SUPABASE_ANON_KEY ||
        process.env.VITE_SUPABASE_ANON_KEY;
    const serviceRoleKey =
        process.env.ARCHIVE_DB_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;

    const dbKey = options?.useServiceRole ? serviceRoleKey || anonKey : anonKey;

    if (!dbUrl || !dbKey) {
        throw new Error('Missing Archive DB credentials (ARCHIVE_DB_ANON_KEY)');
    }

    return createClient(dbUrl, dbKey, STATELESS_DB_OPTIONS);
}

export function getDbBrowserClient() {
    const dbUrl = import.meta.env.VITE_ARCHIVE_DB_URL || DEFAULT_ARCHIVE_DB_URL;
    const dbAnonKey =
        import.meta.env.VITE_ARCHIVE_DB_ANON_KEY || import.meta.env.VITE_SUPABASE_ANON_KEY;

    if (!dbUrl || !dbAnonKey) {
        throw new Error('Missing Archive DB credentials (VITE_ARCHIVE_DB_ANON_KEY)');
    }

    return createClient(dbUrl, dbAnonKey, STATELESS_DB_OPTIONS);
}
