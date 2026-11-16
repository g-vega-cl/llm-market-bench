import { execFileSync, spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { expect, test } from 'vitest';

const NETLIFY_TOML_PATH = join(__dirname, '../../netlify.toml');

function extractIgnoreCommand(tomlContent: string): string {
    const match = tomlContent.match(/^\s*ignore\s*=\s*"((?:[^"\\]|\\.)*)"/m);
    if (!match) {
        throw new Error('Missing [build] ignore command in apps/web/netlify.toml');
    }
    return match[1].replace(/\\"/g, '"').replace(/\\\\/g, '\\');
}

function sanitizedGitEnv(overrides: Record<string, string> = {}): NodeJS.ProcessEnv {
    const env: NodeJS.ProcessEnv = { ...process.env };
    for (const key of Object.keys(env)) {
        if (key.startsWith('GIT_')) {
            delete env[key];
        }
    }
    return { ...env, ...overrides };
}

function gitCommitFiles(repoDir: string, files: Record<string, string>, message: string): string {
    for (const [relPath, content] of Object.entries(files)) {
        const fullPath = join(repoDir, relPath);
        mkdirSync(dirname(fullPath), { recursive: true });
        writeFileSync(fullPath, content, 'utf8');
    }
    const env = sanitizedGitEnv({
        GIT_AUTHOR_NAME: 'Test',
        GIT_AUTHOR_EMAIL: 'test@example.com',
        GIT_COMMITTER_NAME: 'Test',
        GIT_COMMITTER_EMAIL: 'test@example.com',
    });
    execFileSync('git', ['add', '--all'], { cwd: repoDir, env, stdio: 'pipe' });
    execFileSync('git', ['commit', '-m', message], { cwd: repoDir, env, stdio: 'pipe' });
    return execFileSync('git', ['rev-parse', 'HEAD'], {
        cwd: repoDir,
        env,
        encoding: 'utf8',
    }).trim();
}

function runIgnoreCommand(
    ignoreCmd: string,
    repoDir: string,
    cachedCommitRef: string,
    commitRef: string,
): number | null {
    const result = spawnSync('sh', ['-c', ignoreCmd], {
        cwd: repoDir,
        env: sanitizedGitEnv({
            CACHED_COMMIT_REF: cachedCommitRef,
            COMMIT_REF: commitRef,
        }),
        encoding: 'utf8',
    });
    return result.status;
}

test('netlify.toml is configured correctly for TanStack Start SSR without incompatible build-time plugins', () => {
    const content = readFileSync(NETLIFY_TOML_PATH, 'utf8');

    // Assert build and dev settings are configured correctly
    expect(content).toContain('command = "pnpm build:web"');
    expect(content).toContain('publish = "apps/web/dist/client"');

    // Assert that the incompatible build-time Lighthouse plugin is NOT used
    expect(content).not.toContain('@netlify/plugin-lighthouse');

    // Assert stealth PostHog proxy redirects remain intact
    expect(content).toContain('from = "/p/*"');
    expect(content).toContain('to = "https://us.i.posthog.com/:splat"');

    // Assert immutable caching header for hashed JS/CSS assets
    expect(content).toContain('for = "/assets/*"');
    expect(content).toContain('Cache-Control = "public, max-age=31536000, immutable"');
});

test('netlify.toml [build] ignore skips backend/docs-only commits while preserving web and manual builds', () => {
    const content = readFileSync(NETLIFY_TOML_PATH, 'utf8');
    const ignoreCmd = extractIgnoreCommand(content);

    const repoDir = mkdtempSync(join(tmpdir(), 'netlify-ignore-test-'));
    try {
        execFileSync('git', ['init'], { cwd: repoDir, env: sanitizedGitEnv(), stdio: 'pipe' });
        const baseSha = gitCommitFiles(repoDir, { 'README.md': 'init\n' }, 'init');
        const engineOnlySha = gitCommitFiles(
            repoDir,
            {
                'apps/engine/main.py': 'print("hi")\n',
                'wiki/index.md': '# Wiki\n',
                'ROADMAP.md': '# Roadmap\n',
            },
            'backend and docs only',
        );
        const webAndWikiSha = gitCommitFiles(
            repoDir,
            {
                'apps/web/src/app.tsx': 'export const x = 1;\n',
                'wiki/entities/web-app.md': '# Web\n',
            },
            'web and wiki',
        );
        const mixedSha = gitCommitFiles(
            repoDir,
            {
                'apps/engine/main.py': 'print("v2")\n',
                'packages/ui-design-system/src/index.ts': 'export const y = 2;\n',
                'supabase/migrations/001.sql': 'SELECT 1;\n',
            },
            'mixed engine and shared ui',
        );

        // 1. Empty CACHED_COMMIT_REF (first build or cleared cache) must run build (exit 1)
        expect(runIgnoreCommand(ignoreCmd, repoDir, '', engineOnlySha)).toBe(1);

        // 2. Identical CACHED_COMMIT_REF and COMMIT_REF (manual UI redeploy) must run build (exit 1)
        expect(runIgnoreCommand(ignoreCmd, repoDir, engineOnlySha, engineOnlySha)).toBe(1);

        // 3. Backend/docs/roadmap-only commit must skip build (exit 0)
        expect(runIgnoreCommand(ignoreCmd, repoDir, baseSha, engineOnlySha)).toBe(0);

        // 4. Web + Wiki commit must run build (exit 1)
        expect(runIgnoreCommand(ignoreCmd, repoDir, engineOnlySha, webAndWikiSha)).toBe(1);

        // 5. Mixed engine + packages + supabase commit must run build (exit 1)
        expect(runIgnoreCommand(ignoreCmd, repoDir, webAndWikiSha, mixedSha)).toBe(1);
    } finally {
        rmSync(repoDir, { recursive: true, force: true });
    }
});
