import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from 'vitest';

test('netlify.toml has correct Lighthouse plugin configuration', () => {
    const filePath = join(__dirname, '../../netlify.toml');
    const content = readFileSync(filePath, 'utf8');

    // Assert that the lighthouse plugin is registered
    expect(content).toContain('package = "@netlify/plugin-lighthouse"');

    // Assert thresholds and fail conditions
    expect(content).toMatch(/fail_deploy_on_score_thresholds\s*=\s*true/);
    expect(content).toMatch(/performance\s*=\s*0?\.9/);
    expect(content).toMatch(/accessibility\s*=\s*0?\.9/);
    expect(content).toMatch(/best-practices\s*=\s*0?\.9/);
    expect(content).toMatch(/seo\s*=\s*0?\.9/);

    // Assert paths are configured
    expect(content).toMatch(/path\s*=\s*"\/"/);
    expect(content).toMatch(/path\s*=\s*"\/how-it-works"/);
    expect(content).toMatch(/path\s*=\s*"\/portfolios"/);
});
