/**
 * Fail-closed Pi tool_call shim delegating bash checks to apps/engine/agent_pre_tool_gate.py.
 * Discovered automatically from .pi/extensions/ across the main checkout and .worktrees/<slug>.
 */
import { execFileSync } from 'node:child_process';
import { realpathSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const EXT_DIR = dirname(realpathSync(fileURLToPath(import.meta.url)));
const GATE_SCRIPT = resolve(EXT_DIR, '../../apps/engine/agent_pre_tool_gate.py');

export default function registerBenchGate(pi: {
    on: (
        event: string,
        handler: (ev: Record<string, unknown>) => Promise<{ block: boolean; reason?: string } | undefined>,
    ) => void;
}): void {
    pi.on('tool_call', async (event) => {
        const toolName = String(event.toolName ?? event.name ?? '');
        if (toolName !== 'bash') {
            return undefined;
        }
        try {
            const stdout = execFileSync('python3', [GATE_SCRIPT], {
                input: JSON.stringify(event),
                encoding: 'utf8',
                timeout: 5000,
            });
            const verdict = JSON.parse(stdout) as { decision?: string; reason?: string };
            if (verdict.decision !== 'allow') {
                return {
                    block: true,
                    reason: verdict.reason ?? 'Blocked by agent_pre_tool_gate.py',
                };
            }
            return undefined;
        } catch (err) {
            return {
                block: true,
                reason: `Safety gate failed closed: ${String(err)}`,
            };
        }
    });
}
