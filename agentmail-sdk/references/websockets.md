# WebSockets

WebSockets provide real-time, low-latency email event streaming over a persistent connection. No public URL required.

## When to use

- AI agents that need instant email notifications
- Local development (no ngrok needed)
- Client-side applications
- When you need bidirectional communication

For production servers with public endpoints, webhooks may be simpler (see `webhooks.md`).

## Comparison

| Feature | WebSocket | Webhook |
|---|---|---|
| Public URL required | No | Yes |
| Connection | Persistent | HTTP request per event |
| Latency | Lowest (streaming) | HTTP round-trip |
| Firewall | Outbound only | Must expose port |
| Retries | You handle reconnection | AgentMail retries automatically |
| Best for | Agents, bots, local dev | Servers, serverless |

## Python SDK

### Sync usage

```python
from agentmail import AgentMail, Subscribe, Subscribed, MessageReceivedEvent

client = AgentMail()

with client.websockets.connect() as socket:
    # Subscribe to inboxes
    socket.send_subscribe(Subscribe(inbox_ids=["agent@agentmail.to"]))

    # Process events
    for event in socket:
        if isinstance(event, Subscribed):
            print(f"Subscribed to: {event.inbox_ids}")
        elif isinstance(event, MessageReceivedEvent):
            print(f"From: {event.message.from_}")
            print(f"Subject: {event.message.subject}")
            print(f"Body: {event.message.extracted_text}")
```

### Async usage

```python
import asyncio
from agentmail import AsyncAgentMail, Subscribe, MessageReceivedEvent

client = AsyncAgentMail()

async def main():
    async with client.websockets.connect() as socket:
        await socket.send_subscribe(Subscribe(inbox_ids=["agent@agentmail.to"]))

        async for event in socket:
            if isinstance(event, MessageReceivedEvent):
                print(f"New: {event.message.subject}")
                await process_email(event.message)

asyncio.run(main())
```

### Event handler pattern

```python
import threading
from agentmail import AgentMail, Subscribe, EventType

client = AgentMail()

with client.websockets.connect() as socket:
    socket.on(EventType.OPEN, lambda _: print("Connected"))
    socket.on(EventType.MESSAGE, lambda msg: print("Received:", msg))
    socket.on(EventType.CLOSE, lambda _: print("Disconnected"))
    socket.on(EventType.ERROR, lambda err: print("Error:", err))

    socket.send_subscribe(Subscribe(inbox_ids=["agent@agentmail.to"]))

    # Run listener in background thread
    listener = threading.Thread(target=socket.start_listening, daemon=True)
    listener.start()
    listener.join()
```

## TypeScript SDK

### Basic usage

```typescript
import { AgentMailClient, AgentMail } from "agentmail";

const client = new AgentMailClient({ apiKey: process.env.AGENTMAIL_API_KEY });

async function main() {
    const socket = await client.websockets.connect();

    socket.on("open", () => {
        console.log("Connected");
        socket.sendSubscribe({
            type: "subscribe",
            inboxIds: ["agent@agentmail.to"],
        });
    });

    socket.on("message", (event: AgentMail.MessageReceivedEvent) => {
        if (event.type === "message.received") {
            console.log("From:", event.message.from_);
            console.log("Subject:", event.message.subject);
        }
    });

    socket.on("close", (event) => console.log("Disconnected:", event.code));
    socket.on("error", (error) => console.error("Error:", error));
}

main();
```

### React hook

```typescript
import { useEffect, useState } from "react";
import { AgentMailClient, AgentMail } from "agentmail";

function useAgentMailWebSocket(apiKey: string, inboxIds: string[]) {
    const [lastMessage, setLastMessage] = useState<AgentMail.MessageReceivedEvent | null>(null);
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        const client = new AgentMailClient({ apiKey });
        let socket: Awaited<ReturnType<typeof client.websockets.connect>>;

        async function connect() {
            socket = await client.websockets.connect();
            socket.on("open", () => {
                setIsConnected(true);
                socket.sendSubscribe({ type: "subscribe", inboxIds });
            });
            socket.on("message", (event) => {
                if (event.type === "message.received") {
                    setLastMessage(event);
                }
            });
            socket.on("close", () => setIsConnected(false));
        }

        connect();
        return () => socket?.close();
    }, [apiKey, inboxIds.join(",")]);

    return { lastMessage, isConnected };
}
```

## Subscribe options

Filter events by inbox, pod, or event type.

```python
# By inboxes
Subscribe(inbox_ids=["inbox1@agentmail.to", "inbox2@agentmail.to"])

# By pods
Subscribe(pod_ids=["pod_123", "pod_456"])

# By event types
Subscribe(
    inbox_ids=["agent@agentmail.to"],
    event_types=["message.received", "message.sent"],
)
```

```typescript
socket.sendSubscribe({
    type: "subscribe",
    inboxIds: ["agent@agentmail.to"],
    eventTypes: ["message.received", "message.sent"],
});

// By pods
socket.sendSubscribe({
    type: "subscribe",
    podIds: ["pod_123"],
});
```

## Event types

| Event | Python Class | TypeScript Type |
|---|---|---|
| Subscription confirmed | `Subscribed` | `AgentMail.Subscribed` |
| New email received | `MessageReceivedEvent` | `AgentMail.MessageReceivedEvent` |
| Email sent | `MessageSentEvent` | `AgentMail.MessageSentEvent` |
| Email delivered | `MessageDeliveredEvent` | `AgentMail.MessageDeliveredEvent` |
| Email bounced | `MessageBouncedEvent` | `AgentMail.MessageBouncedEvent` |
| Spam complaint | `MessageComplainedEvent` | `AgentMail.MessageComplainedEvent` |
| Email rejected | `MessageRejectedEvent` | `AgentMail.MessageRejectedEvent` |
| Domain verified | `DomainVerifiedEvent` | `AgentMail.DomainVerifiedEvent` |

## Message properties

The `event.message` object on received events:

| Property | Description |
|---|---|
| `inbox_id` | Inbox that received the email |
| `message_id` | Unique message ID |
| `thread_id` | Conversation thread ID |
| `from_` | Sender email address |
| `to` | Recipients list |
| `subject` | Subject line |
| `text` | Plain text body |
| `html` | HTML body |
| `extracted_text` | Reply content only, quoted history stripped |
| `attachments` | List of attachments |
| `labels` | List of labels |

## Error handling

```python
import asyncio
from agentmail import AsyncAgentMail, Subscribe, MessageReceivedEvent
from agentmail.core.api_error import ApiError

client = AsyncAgentMail()

async def process_email(message) -> None:
    # Your inbound email handler goes here.
    print(f"New message from {message.from_}: {message.subject}")

async def main():
    try:
        async with client.websockets.connect() as socket:
            await socket.send_subscribe(Subscribe(inbox_ids=["agent@agentmail.to"]))
            async for event in socket:
                if isinstance(event, MessageReceivedEvent):
                    await process_email(event.message)
    except ApiError as e:
        print(f"API error: {e.status_code} - {e.body}")
    except Exception as e:
        print(f"Connection error: {e}")

asyncio.run(main())
```

```typescript
import { AgentMailError } from "agentmail";

try {
    const socket = await client.websockets.connect();
    // ...
} catch (err) {
    if (err instanceof AgentMailError) {
        console.error(`API error: ${err.statusCode} - ${err.message}`);
    } else {
        console.error("Connection error:", err);
    }
}
```

## Reconnection

The SDK does not auto-reconnect. Implement reconnection with exponential backoff:

```python
import asyncio
from agentmail import AsyncAgentMail, Subscribe, MessageReceivedEvent

async def listen_with_reconnect(inbox_ids: list[str]):
    client = AsyncAgentMail()
    backoff = 1

    while True:
        try:
            async with client.websockets.connect() as socket:
                await socket.send_subscribe(Subscribe(inbox_ids=inbox_ids))
                backoff = 1  # reset on successful connection

                async for event in socket:
                    if isinstance(event, MessageReceivedEvent):
                        await process_email(event.message)

        except Exception as e:
            print(f"Disconnected: {e}. Reconnecting in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
```
