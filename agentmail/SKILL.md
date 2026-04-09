---
name: agentmail
description: Give AI agents their own email inboxes using the AgentMail API. Use when building email agents, sending/receiving emails programmatically, managing inboxes, handling attachments, organizing with labels, creating drafts for human approval, or setting up real-time notifications via webhooks/websockets. Supports multi-tenant isolation with pods.
---

# AgentMail SDK

AgentMail is an API-first email platform for AI agents. Install the SDK and initialize the client.

## Installation

```bash
# TypeScript/Node
npm install agentmail

# Python
pip install agentmail
```

## Setup

```typescript
import { AgentMailClient } from "agentmail";
const client = new AgentMailClient({ apiKey: "YOUR_API_KEY" });
```

```python
from agentmail import AgentMail
client = AgentMail(api_key="YOUR_API_KEY")
```

## Inboxes

Create scalable inboxes on-demand. Each inbox has a unique email address.

```typescript
// Create inbox (auto-generated address)
const autoInbox = await client.inboxes.create();

// Create with custom username and domain
const customInbox = await client.inboxes.create({
  username: "support",
  domain: "yourdomain.com",
});

// List, get, delete
const inboxes = await client.inboxes.list();
const fetchedInbox = await client.inboxes.get({
  inboxId: "inbox@agentmail.to",
});
await client.inboxes.delete({ inboxId: "inbox@agentmail.to" });
```

```python
# Create inbox (auto-generated address)
inbox = client.inboxes.create()

# Create with custom username and domain
inbox = client.inboxes.create(username="support", domain="yourdomain.com")

# List, get, delete
inboxes = client.inboxes.list()
inbox = client.inboxes.get(inbox_id="inbox@agentmail.to")
client.inboxes.delete(inbox_id="inbox@agentmail.to")
```

## Messages

Always send both `text` and `html` for best deliverability.

```typescript
// Send message
await client.inboxes.messages.send({
  inboxId: "agent@agentmail.to",
  to: "recipient@example.com",
  subject: "Hello",
  text: "Plain text version",
  html: "<p>HTML version</p>",
  labels: ["outreach"],
});

// Reply to message
await client.inboxes.messages.reply({
  inboxId: "agent@agentmail.to",
  messageId: "msg_123",
  text: "Thanks for your email!",
});

// List and get messages
const messages = await client.inboxes.messages.list({
  inboxId: "agent@agentmail.to",
});
const message = await client.inboxes.messages.get({
  inboxId: "agent@agentmail.to",
  messageId: "msg_123",
});

// Update labels
await client.inboxes.messages.update({
  inboxId: "agent@agentmail.to",
  messageId: "msg_123",
  addLabels: ["replied"],
  removeLabels: ["unreplied"],
});
```

```python
# Send message
client.inboxes.messages.send(
    inbox_id="agent@agentmail.to",
    to="recipient@example.com",
    subject="Hello",
    text="Plain text version",
    html="<p>HTML version</p>",
    labels=["outreach"]
)

# Reply to message
client.inboxes.messages.reply(
    inbox_id="agent@agentmail.to",
    message_id="msg_123",
    text="Thanks for your email!"
)

# List and get messages
messages = client.inboxes.messages.list(inbox_id="agent@agentmail.to")
message = client.inboxes.messages.get(inbox_id="agent@agentmail.to", message_id="msg_123")

# Update labels
client.inboxes.messages.update(
    inbox_id="agent@agentmail.to",
    message_id="msg_123",
    add_labels=["replied"],
    remove_labels=["unreplied"]
)
```

## Threads

Threads group related messages in a conversation.

```typescript
// List threads (with optional label filter)
const threads = await client.inboxes.threads.list({
  inboxId: "agent@agentmail.to",
  labels: ["unreplied"],
});

// Get thread details
const thread = await client.inboxes.threads.get({
  inboxId: "agent@agentmail.to",
  threadId: "thd_123",
});

// Org-wide thread listing
const allThreads = await client.threads.list();
```

```python
# List threads (with optional label filter)
threads = client.inboxes.threads.list(inbox_id="agent@agentmail.to", labels=["unreplied"])

# Get thread details
thread = client.inboxes.threads.get(inbox_id="agent@agentmail.to", thread_id="thd_123")

# Org-wide thread listing
all_threads = client.threads.list()
```

## Attachments

Send attachments with Base64 encoding. Retrieve via signed URLs.

```typescript
// Send with attachment
const content = Buffer.from(fileBytes).toString("base64");
await client.inboxes.messages.send({
  inboxId: "agent@agentmail.to",
  to: "recipient@example.com",
  subject: "Report",
  text: "See attached.",
  attachments: [
    { content, filename: "report.pdf", contentType: "application/pdf" },
  ],
});
```

```python
import base64

# Send with attachment
content = base64.b64encode(file_bytes).decode()
client.inboxes.messages.send(
    inbox_id="agent@agentmail.to",
    to="recipient@example.com",
    subject="Report",
    text="See attached.",
    attachments=[{"content": content, "filename": "report.pdf", "content_type": "application/pdf"}]
)
```

### Downloading attachments (read carefully)

`get_attachment` / `getAttachment` does **not** return file bytes. It returns an `AttachmentResponse` object containing:

- `download_url` — a **CloudFront-signed URL** (`https://cdn.agentmail.to/attachments/<id>?Expires=...&Signature=...`)
- `expires_at` — the URL expires **1 hour** after you call `get_attachment`
- `filename`, `size`, `content_type`

The signed URL is public-readable during its window — no auth header needed on the GET. To actually get the bytes you must fetch `download_url` yourself, and you must do it **before `expires_at`**. Do not persist the URL in a queue, a session file, or a ticket description — the next worker will see an expired-signature 403. Fetch to bytes inside the same call, then store the bytes (or the `attachment_id`, and re-fetch a fresh URL on demand).

```python
import urllib.request
from pathlib import Path

# Step 1: get the signed URL (and expiry)
att = client.inboxes.messages.get_attachment(
    inbox_id="agent@agentmail.to",
    message_id="msg_123",
    attachment_id="att_456",
)

# Step 2: fetch the bytes IMMEDIATELY — the URL expires in ~1h
with urllib.request.urlopen(att.download_url, timeout=30) as r:
    file_bytes = r.read()

Path(att.filename or "attachment.bin").write_bytes(file_bytes)
```

```typescript
import { promises as fs } from "fs";

// Step 1: get the signed URL (and expiry).
// Note: getAttachment takes positional path params, not an object.
// The broader TS calling-convention discussion is tracked in issue #2 —
// most methods on client.inboxes.* are positional, and the object-style
// examples elsewhere on this page throw `JsonError: Expected string.
// Received object.` until they're corrected.
const att = await client.inboxes.messages.getAttachment(
  "agent@agentmail.to", // inbox_id
  "msg_123",            // message_id
  "att_456",            // attachment_id
);

// Step 2: fetch the bytes IMMEDIATELY — the URL expires in ~1h
const res = await fetch(att.downloadUrl);
if (!res.ok) throw new Error(`Attachment fetch failed: ${res.status}`);
const fileBytes = Buffer.from(await res.arrayBuffer());
await fs.writeFile(att.filename ?? "attachment.bin", fileBytes);
```

**Sandbox gotcha:** the signed URLs point at `cdn.agentmail.to`, not `api.agentmail.to`. If your sandbox egress only whitelists the API host, the CDN fetch will 403/timeout even though `get_attachment` itself succeeds. Allow `cdn.agentmail.to` outbound, or do the CDN fetch in an outer process and pass the bytes into the sandbox.

## Drafts

Create drafts for human-in-the-loop approval before sending.

```typescript
// Create draft
const draft = await client.inboxes.drafts.create({
  inboxId: "agent@agentmail.to",
  to: "recipient@example.com",
  subject: "Pending approval",
  text: "Draft content",
});

// Send draft (converts to message)
await client.inboxes.drafts.send({
  inboxId: "agent@agentmail.to",
  draftId: draft.draftId,
});
```

```python
# Create draft
draft = client.inboxes.drafts.create(
    inbox_id="agent@agentmail.to",
    to="recipient@example.com",
    subject="Pending approval",
    text="Draft content"
)

# Send draft (converts to message)
client.inboxes.drafts.send(inbox_id="agent@agentmail.to", draft_id=draft.draft_id)
```

## Pods

Multi-tenant isolation for SaaS platforms. Each customer gets isolated inboxes.

```typescript
// Create pod for a customer
const pod = await client.pods.create({ clientId: "customer_123" });

// Create inbox within pod
const inbox = await client.inboxes.create({ podId: pod.podId });

// List resources scoped to pod
const inboxes = await client.inboxes.list({ podId: pod.podId });
```

```python
# Create pod for a customer
pod = client.pods.create(client_id="customer_123")

# Create inbox within pod
inbox = client.inboxes.create(pod_id=pod.pod_id)

# List resources scoped to pod
inboxes = client.inboxes.list(pod_id=pod.pod_id)
```

## Idempotency

Use `clientId` for safe retries on create operations.

```typescript
const inbox = await client.inboxes.create({
  clientId: "unique-idempotency-key",
});
// Retrying with same clientId returns the original inbox, not a duplicate
```

```python
inbox = client.inboxes.create(client_id="unique-idempotency-key")
# Retrying with same client_id returns the original inbox, not a duplicate
```

## Real-Time Events

For real-time notifications, see the reference files:

- [webhooks.md](references/webhooks.md) - HTTP-based notifications (requires public URL)
- [websockets.md](references/websockets.md) - Persistent connection (no public URL needed)
