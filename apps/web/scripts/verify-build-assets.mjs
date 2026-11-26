import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = resolve(SCRIPT_DIR, '..');
const CLIENT_DIR = join(WEB_ROOT, 'dist', 'client');
const CLIENT_ASSETS_DIR = join(CLIENT_DIR, 'assets');
const SERVER_ASSETS_DIR = join(WEB_ROOT, 'dist', 'server', 'assets');

function assert(condition, message) {
    if (!condition) {
        console.error(`[verify-build-assets] ERROR: ${message}`);
        process.exit(1);
    }
}

assert(existsSync(CLIENT_ASSETS_DIR), `Missing client assets directory: ${CLIENT_ASSETS_DIR}`);
assert(existsSync(SERVER_ASSETS_DIR), `Missing server assets directory: ${SERVER_ASSETS_DIR}`);

const clientFiles = readdirSync(CLIENT_ASSETS_DIR);
const serverFiles = readdirSync(SERVER_ASSETS_DIR);

const missing = [];
const checkedAssets = new Set();

// 1. Check every asset referenced by __vite__mapDeps or direct relative dynamic imports in client JS
for (const file of clientFiles) {
    if (!file.endsWith('.js')) continue;
    const content = readFileSync(join(CLIENT_ASSETS_DIR, file), 'utf8');
    for (const mapDepsMatch of content.matchAll(
        /__vite__mapDeps[\s\S]{0,200}?m\.f\s*=\s*\[([^\]]+)\]/g,
    )) {
        for (const match of mapDepsMatch[1].matchAll(/["'](assets\/[^"']+)["']/g)) {
            const assetPath = match[1];
            checkedAssets.add(assetPath);
            if (!existsSync(join(CLIENT_DIR, assetPath))) {
                missing.push(`${file} -> ${assetPath}`);
            }
        }
    }
    for (const importMatch of content.matchAll(/\bimport\((?:"|')\.\/([^"']+\.js)(?:"|')\)/g)) {
        const assetPath = `assets/${importMatch[1]}`;
        checkedAssets.add(assetPath);
        if (!existsSync(join(CLIENT_DIR, assetPath))) {
            missing.push(`${file} -> ${assetPath}`);
        }
    }
}

// 2. Check every asset referenced in TanStack Start SSR route manifest(s)
const manifestFiles = serverFiles.filter(
    (f) => f.startsWith('_tanstack-start-manifest') && f.endsWith('.js'),
);
assert(
    manifestFiles.length > 0,
    `No _tanstack-start-manifest*.js found in ${SERVER_ASSETS_DIR}; manifest naming may have changed.`,
);

for (const file of manifestFiles) {
    const content = readFileSync(join(SERVER_ASSETS_DIR, file), 'utf8');
    for (const match of content.matchAll(/"(\/assets\/[^"]+)"/g)) {
        const assetPath = match[1].slice(1);
        checkedAssets.add(assetPath);
        if (!existsSync(join(CLIENT_DIR, assetPath))) {
            missing.push(`${file} -> ${assetPath}`);
        }
    }
}

assert(checkedAssets.size > 0, 'Found zero client assets to verify in build manifests.');
assert(
    missing.length === 0,
    `Missing referenced client build assets:\n  - ${missing.join('\n  - ')}`,
);

// 3. Enforce no dot-underscore route chunks that static hosts can drop or mishandle
const dotUnderscoreChunks = clientFiles.filter((f) => f.includes('._'));
assert(
    dotUnderscoreChunks.length === 0,
    `Dot-underscore chunk filenames detected (use nested route directories instead): ${dotUnderscoreChunks.join(', ')}`,
);

console.log(
    `[verify-build-assets] Verified ${checkedAssets.size} referenced client assets exist in ${CLIENT_ASSETS_DIR}.`,
);
