interface Env {
  GITHUB_PAT: string;
}

interface DispatchTarget {
  workflowFile: string;
  inputs?: Record<string, string>;
}

async function dispatchWorkflow(
  target: DispatchTarget,
  env: Env,
  maxRetries = 3,
  delayMs = 1000
): Promise<{ success: boolean; status: number; message: string }> {
  const workflowUrl = `https://api.github.com/repos/g-vega-cl/llm-market-bench/actions/workflows/${target.workflowFile}/dispatches`;

  const payload: { ref: string; inputs?: Record<string, string> } = { ref: 'main' };
  if (target.inputs) {
    payload.inputs = target.inputs;
  }

  let lastError = '';
  let lastStatus = 500;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
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

      if (response.ok) {
        return {
          success: true,
          status: response.status,
          message: `Dispatched ${target.workflowFile} successfully on attempt ${attempt}.`,
        };
      }

      lastStatus = response.status;
      lastError = await response.text();
      console.warn(
        `[Cron Dispatcher] Dispatch attempt ${attempt} failed with status ${lastStatus}: ${lastError}`
      );
    } catch (err: any) {
      lastStatus = 500;
      lastError = err.message || String(err);
      console.warn(`[Cron Dispatcher] Dispatch attempt ${attempt} encountered error: ${lastError}`);
    }

    if (attempt < maxRetries) {
      await new Promise((resolve) => setTimeout(resolve, delayMs * attempt));
    }
  }

  return { success: false, status: lastStatus, message: lastError };
}

function getNewYorkTime(date: Date): { hour: number; minute: number; day: number } {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    hour: 'numeric',
    minute: 'numeric',
    hour12: false,
  }).formatToParts(date);

  let hour = 0;
  let minute = 0;
  for (const part of parts) {
    if (part.type === 'hour') hour = parseInt(part.value, 10) % 24;
    if (part.type === 'minute') minute = parseInt(part.value, 10);
  }

  return { hour, minute, day: date.getUTCDay() };
}

function resolveScheduledTargets(scheduledTime: Date): DispatchTarget[] {
  const { hour: nyHour, minute: nyMinute, day } = getNewYorkTime(scheduledTime);

  if (nyMinute === 35 && (nyHour === 9 || nyHour === 11)) {
    // 9:35 AM ET & 11:35 AM ET -> Ingestion & Consensus
    return [{ workflowFile: 'ingest.yml' }];
  }

  if (nyHour === 15 && nyMinute === 30) {
    // 3:30 PM ET -> Ingestion & Consensus
    return [{ workflowFile: 'ingest.yml' }];
  }

  if (nyHour === 9 && nyMinute === 15) {
    // 9:15 AM ET -> Market open prediction & Market open newsletter
    return [
      { workflowFile: 'daily-predictor.yml', inputs: { action: 'daily-predictor' } },
      { workflowFile: 'generate-newsletter.yml', inputs: { session: 'open' } },
    ];
  }

  if (nyHour === 17 && nyMinute === 0) {
    // 5:00 PM ET -> Market close newsletter
    return [{ workflowFile: 'generate-newsletter.yml', inputs: { session: 'close' } }];
  }

  if (nyHour === 17 && nyMinute === 15) {
    // 5:15 PM ET -> Evaluate daily predictions
    return [{ workflowFile: 'daily-predictor.yml', inputs: { action: 'evaluate-daily-predictions' } }];
  }

  if (nyHour === 18 && nyMinute === 0) {
    // 6:00 PM ET on Sun (0) & Wed (3) -> Prompt autoresearch 2x a week
    if (day === 0 || day === 3) {
      return [{ workflowFile: 'daily-predictor.yml', inputs: { action: 'daily-autoresearch' } }];
    }
    return [];
  }

  // Default fallback (no action for non-matching schedule triggers)
  return [];
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
