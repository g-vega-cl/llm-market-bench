interface Env {
  GITHUB_PAT: string;
}

interface DispatchTarget {
  workflowFile: string;
  inputs?: Record<string, string>;
}

async function dispatchWorkflow(
  target: DispatchTarget,
  env: Env
): Promise<{ success: boolean; status: number; message: string }> {
  const workflowUrl = `https://api.github.com/repos/g-vega-cl/llm-market-bench/actions/workflows/${target.workflowFile}/dispatches`;

  const payload: { ref: string; inputs?: Record<string, string> } = { ref: 'main' };
  if (target.inputs) {
    payload.inputs = target.inputs;
  }

  const response = await fetch(workflowUrl, {
    method: 'POST',
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${env.GITHUB_PAT}`,
      'User-Agent': 'Cloudflare-Cron-Dispatcher',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    return { success: false, status: response.status, message: errorText };
  }

  return {
    success: true,
    status: response.status,
    message: `Dispatched ${target.workflowFile} successfully.`,
  };
}

function resolveScheduledTargets(scheduledTime: Date): DispatchTarget[] {
  const hour = scheduledTime.getUTCHours();
  const minute = scheduledTime.getUTCMinutes();

  if (minute === 35) {
    // 9:35 AM ET (13:35 UTC), 10:35 AM ET (14:35 UTC), 11:35 AM ET (15:35 UTC)
    return [{ workflowFile: 'ingest.yml' }];
  }

  if (hour === 18 && minute === 0) {
    // 2:00 PM ET (18:00 UTC)
    return [{ workflowFile: 'ingest.yml' }];
  }

  if (hour === 13 && minute === 0) {
    // 9:00 AM ET (13:00 UTC) -> Market open prediction & Market open newsletter
    return [
      { workflowFile: 'daily-predictor.yml', inputs: { action: 'daily-predictor' } },
      { workflowFile: 'generate-newsletter.yml', inputs: { session: 'open' } },
    ];
  }

  if (hour === 21 && minute === 0) {
    // 5:00 PM ET (21:00 UTC) -> Market close newsletter
    return [{ workflowFile: 'generate-newsletter.yml', inputs: { session: 'close' } }];
  }

  if (hour === 21 && minute === 15) {
    // 5:15 PM ET (21:15 UTC)
    return [{ workflowFile: 'daily-predictor.yml', inputs: { action: 'evaluate-daily-predictions' } }];
  }

  if (hour === 22 && minute === 0) {
    // 6:00 PM ET (22:00 UTC)
    return [{ workflowFile: 'daily-predictor.yml', inputs: { action: 'daily-autoresearch' } }];
  }

  // Default fallback
  return [{ workflowFile: 'daily-predictor.yml', inputs: { action: 'daily-predictor' } }];
}

export default {
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    const scheduledTime = new Date(event.scheduledTime);
    const targets = resolveScheduledTargets(scheduledTime);

    for (const target of targets) {
      console.log(
        `[Cron Dispatcher] Triggering '${target.workflowFile}' (${JSON.stringify(
          target.inputs || {}
        )}) at scheduled time: ${scheduledTime.toISOString()}`
      );

      const result = await dispatchWorkflow(target, env);

      if (!result.success) {
        console.error(`[Cron Dispatcher] Error: ${result.message}`);
        throw new Error(`GitHub Workflow dispatch failed (${result.status}): ${result.message}`);
      }

      console.log(`[Cron Dispatcher] Successfully dispatched '${target.workflowFile}' (HTTP ${result.status})`);
    }
  },

  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const action = url.searchParams.get('action');
    const session = url.searchParams.get('session') || 'open';
    const targetParam = url.searchParams.get('target') || url.searchParams.get('workflow');

    let target: DispatchTarget;
    if (targetParam === 'ingest' || targetParam === 'ingest.yml' || action === 'ingest') {
      target = { workflowFile: 'ingest.yml' };
    } else if (
      targetParam === 'generate-newsletter' ||
      targetParam === 'generate-newsletter.yml' ||
      action === 'generate-newsletter'
    ) {
      target = { workflowFile: 'generate-newsletter.yml', inputs: { session } };
    } else {
      target = {
        workflowFile: 'daily-predictor.yml',
        inputs: { action: action || 'daily-predictor' },
      };
    }

    const result = await dispatchWorkflow(target, env);
    if (!result.success) {
      return new Response(JSON.stringify({ error: result.message, status: result.status }), {
        status: result.status,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(
      JSON.stringify({
        message: `Successfully dispatched GitHub workflow '${target.workflowFile}'`,
        inputs: target.inputs || null,
        status: result.status,
        timestamp: new Date().toISOString(),
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  },
};
