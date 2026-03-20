# LLM Chunk Batching Strategy

To ensure high reliability and reasoning precision, the engine implements **Asynchronous Chunk Batching** for all newsletter analysis tasks.

## The Problem: Output Token Bottlenecks
While modern LLMs (Claude 3, Gemini 1.5, GPT-4o) have massive **input context windows** (200k to 2M+ tokens), they have significantly tighter **output token limits** (typically 4,096 to 8,192 tokens).

When processing a large newsletter (50+ stories) in a single request:
1.  **Truncation**: The model's structured JSON response often exceeds the 4k-8k output ceiling. The response is cut off mid-sentence, breaking the JSON parser and resulting in zero trades.
2.  **Attention Dilution**: Accuracy for extraction tasks drops as context grows. Models often miss "the middle" of very long lists (the "Lost in the Middle" phenomenon).
3.  **Latency/Timeouts**: Processing 50 items in a single sequential call can exceed the 60-second API timeout.

## The Solution: Parallel Batching
The engine splits the news chunks into smaller batches (Default: `20`) before sending them to the LLM providers.

### How it Works
1.  **Full Strategic Context**: Every batch call STILL receives the complete Portfolio Summary, Historical Learning context, and current Market Data. The "agent" never loses its global strategy or market awareness.
2.  **News Segmentation**: Only the list of new news stories is divided. 
3.  **Parallel Execution**: All batches are sent simultaneously using `asyncio.gather`, maximizing throughput and ensuring everything finishes within the timeout window.
4.  **Global Reconciliation**: After individual batches are processed, the **Consensus** and **Contrarian** stages take the *entire* combined list of results and perform high-level cross-news reasoning to identify secondary effects and contradictions.

## Trade-offs
| Batch Size | Precision | Cross-News Context | Truncation Risk |
| :--- | :--- | :--- | :--- |
| **5-10** | Very High | Low | Zero |
| **20-25** | High | Balanced | Low (Safe for most extraction) |
| **50+** | Variable | High | **CRITICAL** (Likely to fail JSON parsing) |

## Configuration
The batch size can be adjusted in `apps/engine/analyze.py` by changing the `BATCH_SIZE` constant.
