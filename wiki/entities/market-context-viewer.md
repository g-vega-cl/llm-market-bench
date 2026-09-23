---
tags: [ui-component, daily-predictions, auditability]
category: entity
---

# Market Context Viewer

A collapsible, copyable pre-market context viewer embedded in the Daily Predictions page. It displays the complete `market_context` text (economic prints, options positioning, overnight gaps, newsletters) that was passed to the predictor model, with an estimated token count badge and fallback messaging for records that predate the schema amendment.

## Behavior

- **Null/empty context**: Shows a static notice explaining that context was not captured prior to September 23, 2026.
- **Populated context**: Renders a 300-character preview with a `Click to view complete pre-market briefing` note. Users can expand the full text into a scrollable `<pre>` block and copy it to clipboard.
- **Token estimation**: Displays a `~X tokens` badge derived from `charCount / 4`.
- **Copy button**: Writes the full context to clipboard, showing a temporary 'Copied!' confirmation.

## Props

| Prop | Type | Description |
|------|------|-------------|
| `context` | `string \| null` | The `market_context` content from the prediction record. |

## Related

- [[entities/daily-market-predictor]] — stores and exposes `market_context`
- [[concepts/auditability]] — full input auditability principle
