# Gemini Interactions API: Multi-Turn, Managed Agents, and Streaming Examples

## Stateful Conversation

### Python
```python
interaction1 = client.interactions.create(
    model="gemini-3.8-flash",
    input="Hi, my name is Phil."
)
interaction2 = client.interactions.create(
    model="gemini-3.8-flash",
    input="What is my name?",
    previous_interaction_id=interaction1.id
)
print(interaction2.output_text)
```

### JavaScript/TypeScript
```typescript
const interaction1 = await client.interactions.create({
    model: "gemini-3.8-flash",
    input: "Hi, my name is Phil.",
});
const interaction2 = await client.interactions.create({
    model: "gemini-3.8-flash",
    input: "What is my name?",
    previous_interaction_id: interaction1.id,
});
console.log(interaction2.output_text);
```

## Deep Research Agent

Use `deep-research-preview-04-2026` for fast research or `deep-research-max-preview-04-2026` for maximum exhaustiveness. Agents require `background=True`.

### Python
```python
import time

interaction = client.interactions.create(
    agent="deep-research-preview-04-2026",
    input="Research the history of Google TPUs.",
    background=True
)
while True:
    interaction = client.interactions.get(interaction.id)
    if interaction.status == "completed":
        print(interaction.output_text)
        break
    elif interaction.status == "failed":
        print(f"Failed: {interaction.error}")
        break
    time.sleep(10)
```

### JavaScript/TypeScript
```typescript
import { GoogleGenAI } from "@google/genai";

const client = new GoogleGenAI({});

const initialInteraction = await client.interactions.create({
    agent: "deep-research-preview-04-2026",
    input: "Research the history of Google TPUs.",
    background: true,
});

while (true) {
    const interaction = await client.interactions.get(initialInteraction.id);
    if (interaction.status === "completed") {
        console.log(interaction.output_text);
        break;
    } else if (["failed", "cancelled"].includes(interaction.status)) {
        console.log(`Failed: ${interaction.status}`);
        break;
    }
    await new Promise(resolve => setTimeout(resolve, 10000));
}
```

## Managed Agents (`antigravity-preview-09-2026` & Custom Agents)

### Python
```python
from google import genai

client = genai.Client()

interaction = client.interactions.create(
    agent="antigravity-preview-09-2026",
    input="Write a Python script that generates the first 20 Fibonacci numbers and saves them to fibonacci.txt.",
    environment="remote",
)
print(f"Environment ID: {interaction.environment_id}")
print(interaction.output_text)

agent = client.agents.create(
    id="code-reviewer",
    base_agent="antigravity-preview-09-2026",
    system_instruction="You are a senior code reviewer. Check every file for bugs, style issues, and security vulnerabilities.",
    base_environment={
        "type": "remote",
        "sources": [{"type": "repository", "source": "https://github.com/my-org/backend", "target": "/workspace/repo"}],
    },
)

result = client.interactions.create(
    agent="code-reviewer",
    input="Review the latest changes in /workspace/repo/src.",
    environment="remote",
)
print(result.output_text)
```

### JavaScript/TypeScript
```typescript
import { GoogleGenAI } from "@google/genai";

const client = new GoogleGenAI({});

const interaction = await client.interactions.create({
    agent: "antigravity-preview-09-2026",
    input: "Write a Python script that generates the first 20 Fibonacci numbers and saves them to fibonacci.txt.",
    environment: "remote",
});
console.log(`Environment ID: ${interaction.environment_id}`);
console.log(interaction.output_text);

const agent = await client.agents.create({
    id: "code-reviewer",
    base_agent: "antigravity-preview-09-2026",
    system_instruction: "You are a senior code reviewer. Check every file for bugs, style issues, and security vulnerabilities.",
    base_environment: {
        type: "remote",
        sources: [{ type: "repository", source: "https://github.com/my-org/backend", target: "/workspace/repo" }],
    },
});

const result = await client.interactions.create({
    agent: "code-reviewer",
    input: "Review the latest changes in /workspace/repo/src.",
    environment: "remote",
});
console.log(result.output_text);
```

Manage agents with `client.agents.list()`, `client.agents.get(id=...)`, and `client.agents.delete(id=...)`.

## Streaming

Set `stream=True` to receive incremental server-sent events: `interaction.created` -> (`step.start` -> `step.delta`+ -> `step.stop`)+ -> `interaction.completed`.

### Python
```python
for event in client.interactions.create(
    model="gemini-3.8-flash",
    input="Explain quantum entanglement in simple terms.",
    stream=True,
):
    if event.event_type == "step.delta" and event.delta.type == "text":
        print(event.delta.text, end="", flush=True)
    elif event.event_type == "interaction.completed":
        print(f"\n\nTotal Tokens: {event.interaction.usage.total_tokens}")
```

### JavaScript/TypeScript
```typescript
const stream = await client.interactions.create({
    model: "gemini-3.8-flash",
    input: "Explain quantum entanglement in simple terms.",
    stream: true,
});
for await (const event of stream) {
    if (event.event_type === "step.delta" && event.delta.type === "text") {
        process.stdout.write(event.delta.text);
    } else if (event.event_type === "interaction.completed") {
        console.log(`\n\nTotal Tokens: ${event.interaction?.usage?.total_tokens}`);
    }
}
```
