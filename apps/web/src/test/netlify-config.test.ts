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
