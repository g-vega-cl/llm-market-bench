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

Verify with `agy plugin list`. The server appears as `posthog` in the MCP ecosystem.

## Related

- [[concepts/mcp-setup]]
