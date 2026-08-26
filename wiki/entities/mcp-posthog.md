---
tags: [mcp, posthog, analytics, plugin]
category: entity
---

# PostHog MCP Server Plugin

A local plugin wrapper (`packages/mcp-posthog/`) that integrates the hosted PostHog MCP server into the project. It allows agents to query PostHog analytics data (e.g., dashboards, insights, cohorts) via the MCP protocol.

## Configuration

The plugin packages two connection options in `mcp_config.json`:

- **Hosted SSE** (browser-based login):
  ```json
  "args": ["-y", "mcp-remote@latest", "https://mcp.posthog.com/mcp"]
  ```
- **Personal API key**:
  ```json
  "args": ["-y", "@posthog/mcp-server"]
  "env": { "POSTHOG_API_TOKEN": "<KEY>" }
  ```

## Installation

```bash
agy plugin install ./packages/mcp-posthog
```

## Querying Pageviews via HogQL

PostHog analytics can be queried via HogQL to analyze traffic patterns and optimize navigation:

```sql
SELECT
    properties.$pathname AS pathname,
    count() AS total_views,
    count(DISTINCT distinct_id) AS unique_visitors
FROM events
WHERE event = '$pageview'
GROUP BY pathname
ORDER BY total_views DESC
```

This data is used to optimize navbar routing layout (`apps/web/src/routes/__root.tsx`) to prioritize high-traffic destinations.

## Related

- [[concepts/mcp-setup]]
- [[concepts/posthog-stealth-proxy]]
