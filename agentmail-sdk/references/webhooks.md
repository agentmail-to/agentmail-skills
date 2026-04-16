# Webhooks

Webhooks provide real-time HTTP notifications when email events occur.

## When to use

- Production applications with public endpoints
- Serverless architectures (Lambda, Cloud Functions, Vercel)
- When you need to process events on your server
- When you need automatic retries on failure

For agents without a public URL, use WebSockets instead (see `websockets.md`).

## Setup

`event_types` is **required** — there is no "receive all events" default. Pass the full set you care about.

```python
from agentmail import AgentMail

client = AgentMail()

webhook = client.webhooks.create(
    url="https://your-server.com/webhooks",
    event_types=["message.received", "message.bounced"],
)
# webhook.webhook_id, webhook.secret

# List, get, delete
webhooks = client.webhooks.list()
webhook = client.webhooks.get(webhook_id=webhook.webhook_id)
client.webhooks.delete(webhook_id=webhook.webhook_id)
```

```typescript
const webhook = await client.webhooks.create({
    url: "https://your-server.com/webhooks",
    eventTypes: ["message.received", "message.bounced"],
});

const webhooks = await client.webhooks.list();
await client.webhooks.delete(webhook.webhookId);
```

## Event types

The SDK's typed Literal accepts these seven:

| Event | Description |
|---|---|
| `message.received` | New email received in inbox |
| `message.sent` | Email successfully sent |
| `message.delivered` | Email delivered to recipient's server |
| `message.bounced` | Email failed to deliver |
| `message.complained` | Recipient marked email as spam |
| `message.rejected` | Email rejected before sending |
| `domain.verified` | Custom domain verification completed |

The API also accepts `message.received.spam` and `message.received.blocked` at runtime, but these are not in the SDK's typed Literal, so type checkers will flag them. Pass as plain strings if you need them.

## Payload structure

```json
{
  "type": "event",
  "event_type": "message.received",
  "event_id": "evt_123abc",
  "message": {
    "inbox_id": "inbox_456def",
    "thread_id": "thd_789ghi",
    "message_id": "msg_123abc",
    "from": "Jane Doe <jane@example.com>",
    "to": ["Agent <agent@agentmail.to>"],
    "subject": "Question about my account",
    "text": "Full text body",
    "html": "<html>...</html>",
    "extracted_text": "Just the reply content",
    "labels": ["received"],
    "attachments": [
      {
        "attachment_id": "att_pqr678",
        "filename": "document.pdf",
        "content_type": "application/pdf",
        "size": 123456
      }
    ],
    "created_at": "2025-10-27T10:00:00Z"
  },
  "thread": {}
}
```

## Handling webhooks

Your endpoint must return `200 OK` quickly. Process the payload asynchronously.

### Express (TypeScript)

```typescript
import express from "express";

const app = express();
app.use(express.json());

app.post("/webhooks", (req, res) => {
    const payload = req.body;

    if (payload.event_type === "message.received") {
        // Queue for async processing
        processEmail(payload.message);
    }

    res.status(200).send("OK");
});
```

### Flask (Python)

```python
from flask import Flask, request

app = Flask(__name__)

@app.route("/webhooks", methods=["POST"])
def handle_webhook():
    payload = request.json

    if payload["event_type"] == "message.received":
        process_email(payload["message"])

    return "OK", 200
```

### FastAPI (Python)

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhooks")
async def handle_webhook(request: Request):
    payload = await request.json()

    if payload["event_type"] == "message.received":
        await process_email(payload["message"])

    return {"status": "ok"}
```

## Verifying webhook signatures

Always verify signatures in production to prevent spoofed payloads.

### Python

```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature, secret: str) -> bool:
    # compare_digest raises TypeError on None, bytes, or any non-str value.
    # Reject anything that isn't a string up front.
    if not isinstance(signature, str) or not signature:
        return False
    expected = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.route("/webhooks", methods=["POST"])
def handle_webhook():
    signature = request.headers.get("X-AgentMail-Signature")
    if not verify_signature(request.data, signature, WEBHOOK_SECRET):
        return "Invalid signature", 401

    payload = request.json
    # Safe to process
    return "OK", 200
```

### TypeScript

```typescript
import crypto from "crypto";

function verifySignature(
    payload: Buffer,
    signature: string | undefined,
    secret: string,
): boolean {
    // Reject unsigned requests before touching timingSafeEqual, which
    // throws RangeError on mismatched buffer lengths.
    if (!signature) return false;
    const expected = crypto
        .createHmac("sha256", secret)
        .update(payload)
        .digest("hex");
    const expectedBuf = Buffer.from(expected, "hex");
    const signatureBuf = Buffer.from(signature, "hex");
    if (expectedBuf.length !== signatureBuf.length) return false;
    return crypto.timingSafeEqual(expectedBuf, signatureBuf);
}

app.post("/webhooks", express.raw({ type: "application/json" }), (req, res) => {
    const signature = req.headers["x-agentmail-signature"];
    const signatureStr = Array.isArray(signature) ? signature[0] : signature;
    if (!verifySignature(req.body, signatureStr, WEBHOOK_SECRET)) {
        return res.status(401).send("Invalid signature");
    }
    const event = JSON.parse(req.body.toString("utf8"));
    // Process event...
    res.status(200).send("OK");
});
```

## Local development

Use ngrok or similar to expose your local server:

```bash
ngrok http 3000
# Use the ngrok HTTPS URL when creating the webhook
```

## Retry behavior

AgentMail automatically retries failed webhook deliveries with exponential backoff. A delivery is considered failed if your endpoint returns a non-2xx status code or does not respond within 30 seconds.
