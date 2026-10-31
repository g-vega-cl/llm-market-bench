import { createClient } from '@supabase/supabase-js';

export const DEFAULT_ARCHIVE_DB_URL = 'https://benchify-archive-db.clvg.uk';

const STATELESS_DB_OPTIONS = {
    auth: {
        persistSession: false,
        autoRefreshToken: false,
        detectSessionInUrl: false,
    },
};

function ensureEnvLoaded() {
    if (process.env.NODE_ENV === 'test' || process.env.VITEST) {
        return;
    }
    if (typeof process !== 'undefined' && typeof process.loadEnvFile === 'function') {
        if (!process.env.ARCHIVE_DB_SERVICE_ROLE_KEY) {
            try {
                process.loadEnvFile('.env');
            } catch {
                try {
                    process.loadEnvFile('apps/web/.env');
                } catch {
                    // Ignored in environments without local .env files (e.g. Netlify/CI)
                }
            }
        }
    }
}

export function getDbAdminClient() {
    ensureEnvLoaded();
    const dbUrl =
        process.env.ARCHIVE_DB_URL || process.env.VITE_ARCHIVE_DB_URL || DEFAULT_ARCHIVE_DB_URL;
    const serviceRoleKey =
        process.env.ARCHIVE_DB_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!serviceRoleKey) {
        throw new Error(
            'Missing Archive DB service role key (ARCHIVE_DB_SERVICE_ROLE_KEY). Privileged operations require service_role access.',
        );
    }

    return createClient(dbUrl, serviceRoleKey, STATELESS_DB_OPTIONS);
}

export function getDbServerClient(options?: { useServiceRole?: boolean }) {
    if (options?.useServiceRole) {
        return getDbAdminClient();
    }

    ensureEnvLoaded();
    const dbUrl =
        process.env.ARCHIVE_DB_URL || process.env.VITE_ARCHIVE_DB_URL || DEFAULT_ARCHIVE_DB_URL;
    const anonKey =
        process.env.ARCHIVE_DB_ANON_KEY ||
        process.env.VITE_ARCHIVE_DB_ANON_KEY ||
        process.env.SUPABASE_ANON_KEY ||
        process.env.VITE_SUPABASE_ANON_KEY;

    if (!dbUrl || !anonKey) {
        throw new Error('Missing Archive DB credentials (ARCHIVE_DB_ANON_KEY)');
    }

    return createClient(dbUrl, anonKey, STATELESS_DB_OPTIONS);
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
