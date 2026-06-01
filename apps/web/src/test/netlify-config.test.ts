import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from 'vitest';

test('netlify.toml is configured correctly for TanStack Start SSR without incompatible build-time plugins', () => {
    const filePath = join(__dirname, '../../netlify.toml');
    const content = readFileSync(filePath, 'utf8');

    // Assert build and dev settings are configured correctly
    expect(content).toContain('command = "pnpm build:web"');
    expect(content).toContain('publish = "apps/web/dist/client"');

    // Assert that the incompatible build-time Lighthouse plugin is NOT used
    expect(content).not.toContain('@netlify/plugin-lighthouse');

    // Assert stealth PostHog proxy redirects remain intact
    expect(content).toContain('from = "/p/*"');
    expect(content).toContain('to = "https://us.i.posthog.com/:splat"');
});

test('netlify.toml declares long-term immutable caching for /assets/* and CDN-friendly caching for /', () => {
    const filePath = join(__dirname, '../../netlify.toml');
    const content = readFileSync(filePath, 'utf8');

    // The /assets path is fingerprinted by Vite so immutable caching is safe
    expect(content).toMatch(/\/assets\/\*[\s\S]*?max-age=31536000[\s\S]*?immutable/);

    // The root must use a CDN-friendly cache header (stale-while-revalidate allowed)
    expect(content).toMatch(/for\s*=\s*"\/"\s*[\s\S]*?(s-maxage|stale-while-revalidate)/);
});

test('public/_headers mirrors the long-term immutable caching for /assets/*', () => {
    const filePath = join(__dirname, '../../public/_headers');
    const content = readFileSync(filePath, 'utf8');

    expect(content).toMatch(/\/assets\/\*[\s\S]*?(immutable|max-age=31536000)/);
});
