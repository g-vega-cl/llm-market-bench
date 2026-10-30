import { createBrowserClient, createServerClient } from '@supabase/ssr';
import { setCookie } from '@tanstack/react-start/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getAuthBrowserClient, getAuthServerClient } from './auth';

vi.mock('@supabase/ssr', () => ({
    createServerClient: vi.fn((url, key, options) => ({
        url,
        key,
        options,
    })),
    createBrowserClient: vi.fn((url, key) => ({
        url,
        key,
    })),
}));

vi.mock('@tanstack/react-start/server', () => ({
    getCookies: vi.fn(() => ({ 'sb-token': 'abc' })),
    setCookie: vi.fn(),
}));

interface MockServerClient {
    url: string;
    key: string;
    options: {
        cookies: {
            getAll: () => { name: string; value: string }[];
            setAll: (
                cookies: {
                    name: string;
                    value: string;
                    options?: Record<string, unknown>;
                }[],
            ) => void;
        };
    };
}

describe('auth client (Supabase Cloud Only)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        delete process.env.SUPABASE_AUTH_URL;
        delete process.env.SUPABASE_AUTH_ANON_KEY;
        delete process.env.SUPABASE_URL;
        delete process.env.SUPABASE_ANON_KEY;
        vi.stubEnv('VITE_SUPABASE_AUTH_URL', '');
        vi.stubEnv('VITE_SUPABASE_AUTH_ANON_KEY', '');
        vi.stubEnv('VITE_SUPABASE_URL', '');
        vi.stubEnv('VITE_SUPABASE_ANON_KEY', '');
    });

    it('should create server auth client using SUPABASE_AUTH_URL and pass cookie options to setCookie', () => {
        process.env.SUPABASE_AUTH_URL = 'https://mock-auth-project.supabase.co';
        process.env.SUPABASE_AUTH_ANON_KEY = 'cloud-anon-key';

        const client = getAuthServerClient() as unknown as MockServerClient;
        expect(createServerClient).toHaveBeenCalledWith(
            'https://mock-auth-project.supabase.co',
            'cloud-anon-key',
            expect.any(Object),
        );
        expect(client.options.cookies.getAll()).toEqual([{ name: 'sb-token', value: 'abc' }]);

        const cookiesToSet = [
            {
                name: 'sb-access-token',
                value: 'token-value',
                options: { path: '/', maxAge: 3600 },
            },
        ];

        client.options.cookies.setAll(cookiesToSet);

        expect(setCookie).toHaveBeenCalledWith('sb-access-token', 'token-value', {
            path: '/',
            maxAge: 3600,
        });
    });

    it('should reject archive-db URL in getAuthServerClient to prevent PGRST125 auth misrouting', () => {
        process.env.SUPABASE_AUTH_URL = 'https://benchify-archive-db.clvg.uk';
        process.env.SUPABASE_AUTH_ANON_KEY = 'local-key';

        expect(() => getAuthServerClient()).toThrow(
            /Invalid Auth URL.*points to the local PostgREST archive database/,
        );
    });

    it('should create browser auth client using VITE_SUPABASE_AUTH_URL', () => {
        vi.stubEnv('VITE_SUPABASE_AUTH_URL', 'https://mock-auth-project.supabase.co');
        vi.stubEnv('VITE_SUPABASE_AUTH_ANON_KEY', 'cloud-anon-key');

        getAuthBrowserClient();
        expect(createBrowserClient).toHaveBeenCalledWith(
            'https://mock-auth-project.supabase.co',
            'cloud-anon-key',
        );
    });

    it('should reject archive-db URL in getAuthBrowserClient to prevent PGRST125 auth misrouting', () => {
        vi.stubEnv('VITE_SUPABASE_AUTH_URL', 'https://benchify-archive-db.clvg.uk');
        vi.stubEnv('VITE_SUPABASE_AUTH_ANON_KEY', 'local-key');

        expect(() => getAuthBrowserClient()).toThrow(
            /Invalid Auth URL.*points to the local PostgREST archive database/,
        );
    });
});
