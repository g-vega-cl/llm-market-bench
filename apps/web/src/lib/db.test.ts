import { createClient } from '@supabase/supabase-js';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getDbBrowserClient, getDbServerClient } from './db';

vi.mock('@supabase/supabase-js', () => ({
    createClient: vi.fn((url, key, options) => ({
        url,
        key,
        options,
    })),
}));

describe('db client (Local PostgREST Archive DB Only)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        delete process.env.ARCHIVE_DB_URL;
        delete process.env.ARCHIVE_DB_ANON_KEY;
        delete process.env.ARCHIVE_DB_SERVICE_ROLE_KEY;
        delete process.env.SUPABASE_URL;
        delete process.env.SUPABASE_ANON_KEY;
        vi.stubEnv('VITE_ARCHIVE_DB_URL', '');
        vi.stubEnv('VITE_ARCHIVE_DB_ANON_KEY', '');
        vi.stubEnv('VITE_SUPABASE_URL', '');
        vi.stubEnv('VITE_SUPABASE_ANON_KEY', '');
    });

    it('should create server db client using ARCHIVE_DB_URL and ARCHIVE_DB_ANON_KEY with auth persistence disabled', () => {
        process.env.ARCHIVE_DB_URL = 'https://benchify-archive-db.clvg.uk';
        process.env.ARCHIVE_DB_ANON_KEY = 'local-anon-jwt';

        getDbServerClient();
        expect(createClient).toHaveBeenCalledWith(
            'https://benchify-archive-db.clvg.uk',
            'local-anon-jwt',
            {
                auth: {
                    persistSession: false,
                    autoRefreshToken: false,
                    detectSessionInUrl: false,
                },
            },
        );
    });

    it('should create browser db client using VITE_ARCHIVE_DB_URL and VITE_ARCHIVE_DB_ANON_KEY with auth persistence disabled', () => {
        vi.stubEnv('VITE_ARCHIVE_DB_URL', 'https://benchify-archive-db.clvg.uk');
        vi.stubEnv('VITE_ARCHIVE_DB_ANON_KEY', 'local-anon-jwt');

        getDbBrowserClient();
        expect(createClient).toHaveBeenCalledWith(
            'https://benchify-archive-db.clvg.uk',
            'local-anon-jwt',
            {
                auth: {
                    persistSession: false,
                    autoRefreshToken: false,
                    detectSessionInUrl: false,
                },
            },
        );
    });

    it('should throw when missing ARCHIVE_DB_ANON_KEY', () => {
        process.env.ARCHIVE_DB_URL = 'https://benchify-archive-db.clvg.uk';
        expect(() => getDbServerClient()).toThrow(/Missing Archive DB credentials/);
    });
});
