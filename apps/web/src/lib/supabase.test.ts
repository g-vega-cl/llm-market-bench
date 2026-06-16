import { setCookie } from '@tanstack/react-start/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getSupabaseServerClient } from './supabase';

vi.mock('@supabase/ssr', () => ({
    createServerClient: vi.fn((url, key, options) => ({
        url,
        key,
        options,
    })),
}));

vi.mock('@tanstack/react-start/server', () => ({
    getCookies: vi.fn(() => ({})),
    setCookie: vi.fn(),
}));

interface MockServerClient {
    options: {
        cookies: {
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

describe('getSupabaseServerClient', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        process.env.SUPABASE_URL = 'https://mock-supabase.supabase.co';
        process.env.SUPABASE_ANON_KEY = 'mock-anon-key';
    });

    it('should pass cookie options (path, maxAge, etc.) to setCookie', () => {
        const client = getSupabaseServerClient() as unknown as MockServerClient;
        expect(client.options.cookies).toBeDefined();

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
});
