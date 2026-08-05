interface Env {
  GITHUB_PAT: string;
}

async function dispatchWorkflow(action: string, env: Env): Promise<{ success: boolean; status: number; message: string }> {
  const workflowUrl =
    'https://api.github.com/repos/g-vega-cl/llm-market-bench/actions/workflows/daily-predictor.yml/dispatches';

  const response = await fetch(workflowUrl, {
    method: 'POST',
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${env.GITHUB_PAT}`,
      'User-Agent': 'Cloudflare-Cron-Dispatcher',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ref: 'main',
      inputs: { action },
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    return { success: false, status: response.status, message: errorText };
  }

  return { success: true, status: response.status, message: `Dispatched ${action} successfully.` };
}

export default {
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    const scheduledTime = new Date(event.scheduledTime);
    const hour = scheduledTime.getUTCHours();

    let action = 'daily-predictor';
    if (hour === 21) {
      action = 'evaluate-daily-predictions';
    } else if (hour === 22) {
      action = 'daily-autoresearch';
    }

    console.log(`[Cron Dispatcher] Triggering '${action}' at scheduled time: ${scheduledTime.toISOString()}`);
    const result = await dispatchWorkflow(action, env);

    if (!result.success) {
      console.error(`[Cron Dispatcher] Error: ${result.message}`);
      throw new Error(`GitHub Workflow dispatch failed (${result.status}): ${result.message}`);
    }

    console.log(`[Cron Dispatcher] Successfully dispatched '${action}' (HTTP ${result.status})`);
  },

  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const action = url.searchParams.get('action') || 'daily-predictor';

    const result = await dispatchWorkflow(action, env);
    if (!result.success) {
      return new Response(JSON.stringify({ error: result.message, status: result.status }), {
        status: result.status,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(
      JSON.stringify({
        message: `Successfully dispatched GitHub workflow '${action}'`,
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
