# raw/ — Source Documents

This directory holds immutable source documents that feed the wiki. The LLM
reads from here but never modifies anything.

## How to Add a Source

1. Drop a file here — any format: markdown, PDF, web article (via Obsidian Web Clipper), etc.
2. Tell the agent: "ingest raw/my-article.md"
3. The agent will:
   - Read the source
   - Discuss key takeaways with you
   - Write/update a relevant wiki page (entity, concept, or overview)
   - Update `wiki/index.md`
   - Append to `wiki/log.md`

## Tips

- **Obsidian Web Clipper** converts web articles to markdown
- Files here are never modified — the wiki layer is the synthesis
- Prefer ingesting one source at a time — stay involved in what gets extracted
