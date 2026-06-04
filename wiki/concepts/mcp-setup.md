---
tags: [mcp, configuration, tools, cli]
category: concept
---

# Model Context Protocol (MCP) Setup

This document describes how Model Context Protocol (MCP) servers are configured, managed, and cached in the Antigravity environment.

## 1. Workspace Configuration

MCP servers can be configured locally for a specific repository so that they are discovered automatically by workspace-based editors:

*   **Claude Code**: Looks for `.mcp.json` at the workspace root.
*   **Opencode / Codex**: Looks for `.ai/mcp/mcp.json`.

### Format (.mcp.json / .ai/mcp/mcp.json)
```json
{
  "mcpServers": {
    "knowledge-rag": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "tsx",
        "./packages/mcp-knowledge-rag/src/index.ts"
      ]
    }
  }
}
```

Workspace-defined servers configured in this way are active when the agent is running inside that specific repository.

## 2. Global Configuration

Global MCP servers are available across all workspaces and sessions. They are configured in `mcp_config.json` files within the system configuration directories.

* **Paths**:
  - `~/.gemini/antigravity-cli/mcp_config.json` (Primary configuration path for CLI)
  - `~/.gemini/config/mcp_config.json` (Shared configuration directory)
* **Format**:
  Matches the standard JSON structure used in workspace configuration.
  ```json
  {
    "mcpServers": {}
  }
  ```

If a server is configured globally, it will load automatically on CLI startup regardless of the current workspace.

## 3. MCP Plugins

In the Antigravity/Gemini CLI (`agy`), local MCP servers are registered as workspace-level plugins via the plugin manager.

* **Install local plugin**:
  ```bash
  agy plugin install ./packages/mcp-knowledge-rag
  ```
  *(Reads the `plugin.json` and `mcp_config.json` files inside the package directory and registers the server. Since it uses relative execution paths, it only executes when `agy` is launched from the project root).*

* **Uninstall plugin**:
  ```bash
  agy plugin uninstall knowledge-rag
  ```

* **Plugin Command Reference**:
  - `agy plugin list`: List all imported and active plugins.
  - `agy plugin install <target>`: Install a new plugin from a marketplace or local package.
  - `agy plugin uninstall <name>`: Uninstall a plugin.
  - `agy plugin enable <name>`: Enable a disabled plugin.
  - `agy plugin disable <name>`: Disable a plugin.

Plugins store their files under `~/.gemini/antigravity-cli/plugins/`. Uninstalling a plugin via the CLI removes it from active plugins but might leave the physical folder structure. If necessary, you can clean it up manually with:
```bash
rm -rf ~/.gemini/antigravity-cli/plugins/<pluginName>
```

## 4. Cached Tool Schemas

To improve performance and support lazy loading, the CLI caches tool schemas and metadata for active servers.

* **Path**: `~/.gemini/antigravity-cli/mcp/<serverName>`

If an MCP server or plugin is uninstalled or removed from `mcp_config.json`, the CLI may still display it if cached schemas are present. In these cases, clean up the cache by deleting the folder:
```bash
rm -rf ~/.gemini/antigravity-cli/mcp/<serverName>
```
