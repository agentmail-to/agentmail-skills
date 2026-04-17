# Webhooks

Webhooks provide real-time HTTP notifications when email events occur. Use webhooks when you have a public URL endpoint.

## When to Use

- Production applications with public endpoints
- Event-driven architectures
- When you need to process events on your server

For local development without a public URL, use [websockets.md](websockets.md) instead.

## Setup

Register a webhook endpoint to receive events.

`eventTypes` / `event_types` is **required** — you must pass the list of events the webhook should receive.

```typescript
import { AgentMailClient } from "agentmail";

const client = new AgentMailClient({ apiKey: "YOUR_API_KEY" });

// Create webhook
const webhook = await client.webhooks.create({
  url: "https://your-server.com/webhooks",
  eventTypes: ["message.received"],
});

// List webhooks
const webhooks = await client.webhooks.list();

// Delete webhook
await client.webhooks.delete(webhook.webhookId);
```

```python
from agentmail import AgentMail
client = AgentMail(api_key="YOUR_API_KEY")

# Create webhook
webhook = client.webhooks.create(
    url="https://your-server.com/webhooks",
    event_types=["message.received"],
)

# List webhooks
webhooks = client.webhooks.list()

# Delete webhook
client.webhooks.delete(webhook_id=webhook.webhook_id)
```

## Event Types

| Event                | Description                           |
| -------------------- | ------------------------------------- |
| `message.received`   | New email received in inbox           |
| `message.sent`       | Email successfully sent               |
| `message.delivered`  | Email delivered to recipient's server |
| `message.bounced`    | Email failed to deliver               |
| `message.complained` | Recipient marked email as spam        |
| `message.rejected`   | Email rejected before sending         |
| `domain.verified`    | Custom domain verification completed  |

## Payload Structure

All webhook payloads follow this structure:

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
    "labels": ["received"],
    "attachments": [
      {
        "attachment_id": "att_pqr678",
        "filename": "document.pdf",
        "content_type": "application/pdf",
        "size": 123456
      }
    ],
    "created_at": "2023-10-27T10:00:00Z"
  },
  "thread": {}
}
```

## Handling Webhooks

Your endpoint should:

1. Return `200 OK` immediately
2. Process the payload asynchronously

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

  res.status(200).send("OK"); // Return immediately
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
        # Queue for async processing
        process_email.delay(payload["message"])

    return "OK", 200  # Return immediately
```

## Webhook Verification

Verify webhook signatures to ensure requests are from AgentMail.

### TypeScript

```typescript
import crypto from "crypto";
import express from "express";

function verifySignature(
  payload: Buffer,
  signature: string,
  secret: string
): boolean {
  const expected = crypto
    .createHmac("sha256", secret)
    .update(payload)
    .digest("hex");
  const expectedBuf = Buffer.from(expected, "hex");
  const signatureBuf = Buffer.from(signature, "hex");
  // timingSafeEqual throws RangeError on mismatched lengths;
  // return false for any malformed header instead of crashing.
  if (expectedBuf.length !== signatureBuf.length) return false;
  return crypto.timingSafeEqual(expectedBuf, signatureBuf);
}

app.post("/webhooks", express.raw({ type: "application/json" }), (req, res) => {
  const signature = req.headers["x-agentmail-signature"];
  if (typeof signature !== "string") {
    return res.status(401).send("Missing signature");
  }

  const payload = req.body;
  if (!verifySignature(payload, signature, WEBHOOK_SECRET)) {
    return res.status(401).send("Invalid signature");
  }
  const event = JSON.parse(payload.toString("utf8"));
  // Process event...
  res.status(200).send("OK");
});
```

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
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.route("/webhooks", methods=["POST"])
def handle_webhook():
    signature = request.headers.get("X-AgentMail-Signature")
    if not verify_signature(request.data, signature, WEBHOOK_SECRET):
        return "Invalid signature", 401
    # Process payload...
```

## Local Development

Use ngrok to expose your local server:

```bash
ngrok http 5000
# Use the ngrok URL when creating the webhook
```
