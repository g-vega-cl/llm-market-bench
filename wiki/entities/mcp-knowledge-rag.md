---
tags: [mcp, rag, semantic-search, gemini, supabase]
category: entity
---

# MCP Knowledge RAG Server

A workspace-local Model Context Protocol (MCP) server that provides semantic search (RAG) against an external Supabase database (`misc`). It generates 768-dimension embeddings via Gemini's `gemini-embedding-001` model and queries pgvector's `match_emails` RPC function to retrieve relevant email records. Designed for use with AI coding assistants (Antigravity/Gemini CLI, Claude Code, Opencode) to ground responses in curated external knowledge.

## Architecture

The server runs as a stdio-based MCP tool exposing a single `query_knowledge_base` tool. It auto-loads environment variables from `apps/engine/.env` or the process directory, requiring `GEMINI_API_KEY`, `MISC_SUPABASE_URL`, and `MISC_SUPABASE_KEY`.

### Tool: `query_knowledge_base`

- **Input**: Natural language query string, optional `limit` (default 5), optional `threshold` (default 0.5)
- **Output**: Formatted list of matching email records with sender, subject, date, body, and similarity score
- **Pipeline**: Query → Gemini embedding → Supabase `match_emails` RPC → formatted results

## Configuration

### Workspace Discovery

- **Claude Code**: `.mcp.json` at workspace root
- **Opencode / Codex**: `.ai/mcp/mcp.json`

### Antigravity CLI Plugin

Registered via `plugin.json` and `mcp_config.json` in the package directory. Install with:

```bash
agy plugin install ./packages/mcp-knowledge-rag
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key for embedding generation |
| `MISC_SUPABASE_URL` | Yes | Supabase project URL for the external knowledge DB |
| `MISC_SUPABASE_KEY` | Yes | Supabase anon/service key for the external knowledge DB |

## Package Structure

```
packages/mcp-knowledge-rag/
  package.json          # @llm-market-bench/mcp-knowledge-rag
  plugin.json           # Antigravity CLI plugin metadata
  mcp_config.json       # MCP server configuration
  tsconfig.json         # TypeScript strict mode, ESNext modules
  src/
    index.ts            # MCP server implementation + query logic
    index.test.ts       # Vitest unit tests with mocked SDKs
    test-client.ts      # Standalone CLI test client
```

## Related

- [[concepts/mcp-setup]] — MCP configuration, plugin management, and caching
- [[entities/engine]] — Environment variable definitions
- [[entities/database]] — Supabase pgvector infrastructure
