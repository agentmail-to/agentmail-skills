---
name: agentmail-sdk
description: Comprehensive guide to the AgentMail Python and TypeScript SDKs. Use when building AI agents that need their own email inboxes, sending or receiving emails programmatically, managing threads and conversations, handling attachments, creating drafts for human-in-the-loop approval, setting up real-time notifications via webhooks or WebSockets, configuring custom domains, managing allow/block lists, using pods for multi-tenant isolation, or integrating email into any AI agent workflow. Covers the full AgentMail API with code examples, best practices, and production patterns.
license: MIT
metadata:
  author: agentmail-to
  version: "1.0"
---

# AgentMail SDK

AgentMail is an API-first email platform built for AI agents. Unlike transactional email APIs (Resend, SendGrid) that focus on one-way sending, AgentMail provides full two-way email inboxes that agents can create, send from, receive into, and manage programmatically.

Key capabilities:
- Instant inbox creation (milliseconds, no domain setup needed)
- Two-way conversations with native thread management
- Reply extraction (`extracted_text`) strips quoted history automatically
- WebSocket and webhook support for real-time inbound
- Human-in-the-loop drafts for agent oversight
- Multi-tenant isolation with pods
- Allow/block lists for sender filtering
- IMAP and SMTP access for legacy integrations

## Installation and setup

```bash
# Python
pip install agentmail

# TypeScript / Node.js
npm install agentmail
```

Get your API key from https://console.agentmail.to/ or via the Agent sign-up API (see below).

**Python:**
```python
from agentmail import AgentMail
client = AgentMail(api_key="YOUR_API_KEY")
# Or set AGENTMAIL_API_KEY env var and omit api_key:
# client = AgentMail()
```

**TypeScript:**
```typescript
import { AgentMailClient } from "agentmail";
const client = new AgentMailClient({ apiKey: "YOUR_API_KEY" });
```

## Agent sign-up (programmatic, no console needed)

Create an account and get an API key entirely from code. No browser required.

> Requires `agentmail>=0.4.15` (Python) / `agentmail>=0.x` (TypeScript). If your installed
> SDK raises `AttributeError: 'AgentMail' object has no attribute 'agent'`, upgrade first.

```python
client = AgentMail()  # no api_key needed for sign-up
response = client.agent.sign_up(
    human_email="you@example.com",
    username="my-agent",
)
# response.api_key   -> store this securely
# response.inbox_id  -> my-agent@agentmail.to
# response.organization_id

# Verify with OTP sent to your email
client = AgentMail(api_key=response.api_key)
client.agent.verify(otp_code="123456")
```

```typescript
const client = new AgentMailClient();
const response = await client.agent.signUp({
    humanEmail: "you@example.com",
    username: "my-agent",
});
// response.apiKey, response.inboxId, response.organizationId

const authedClient = new AgentMailClient({ apiKey: response.apiKey });
await authedClient.agent.verify({ otpCode: "123456" });
```

The sign-up endpoint is idempotent: calling again with the same email rotates the API key and resends the OTP.

## Inboxes

Create scalable inboxes on-demand. Each inbox has a unique email address. No domain verification needed for `@agentmail.to`.

```python
from agentmail.inboxes.types import CreateInboxRequest

# Create inbox (auto-generated address)
inbox = client.inboxes.create()
# inbox.inbox_id, inbox.email

# Create with options. All create kwargs go inside a CreateInboxRequest.
inbox = client.inboxes.create(
    request=CreateInboxRequest(
        username="support",
        domain="yourdomain.com",       # optional, defaults to agentmail.to
        display_name="Support Agent",
        client_id="support-v1",        # idempotency key, safe to retry
    ),
)

# List all inboxes
inboxes = client.inboxes.list()
# Paginate: client.inboxes.list(limit=20, page_token=inboxes.next_page_token)

# Get, update, delete
inbox = client.inboxes.get(inbox_id="support@agentmail.to")
client.inboxes.update(inbox_id="support@agentmail.to", display_name="New Name")
client.inboxes.delete(inbox_id="support@agentmail.to")
```

```typescript
const inbox = await client.inboxes.create({
    username: "support",
    domain: "yourdomain.com",
    displayName: "Support Agent",
    clientId: "support-v1",
});

const inboxes = await client.inboxes.list();
const fetched = await client.inboxes.get("support@agentmail.to");
await client.inboxes.update("support@agentmail.to", { displayName: "New Name" });
await client.inboxes.delete("support@agentmail.to");
```

Custom domains require a paid plan. Default `@agentmail.to` inboxes are free.

## Messages

### Send

Always provide both `text` and `html` for best deliverability. Maximum 50 recipients across to + cc + bcc combined.

```python
sent = client.inboxes.messages.send(
    inbox_id="agent@agentmail.to",
    to="recipient@example.com",       # string or list
    subject="Hello from AgentMail",
    text="Plain text body",
    html="<p>HTML body</p>",          # optional but recommended
    cc="cc@example.com",              # optional, string or list
    bcc="bcc@example.com",            # optional, string or list
    reply_to="replies@example.com",   # optional
    labels=["outreach"],              # optional
    attachments=[{                    # optional
        "filename": "report.pdf",
        "content": base64_content,    # Base64-encoded
        "content_type": "application/pdf",
    }],
)
# sent.message_id, sent.thread_id
```

```typescript
const sent = await client.inboxes.messages.send("agent@agentmail.to", {
    to: "recipient@example.com",
    subject: "Hello from AgentMail",
    text: "Plain text body",
    html: "<p>HTML body</p>",
    cc: "cc@example.com",
    labels: ["outreach"],
    attachments: [{
        filename: "report.pdf",
        content: base64Content,
        contentType: "application/pdf",
    }],
});
```

### List and get

```python
# List messages in an inbox. Note: .list() returns MessageItem objects
# (metadata only — subject, from, labels, timestamps, etc.) with NO body
# content. To read .text / .html / .extracted_text you must fetch the full
# message with .get().
response = client.inboxes.messages.list(
    inbox_id="agent@agentmail.to",
    limit=10,                # optional, default varies
    labels=["unread"],       # optional, filter by label
)
for item in response.messages:
    # item is a MessageItem (metadata only). Fetch the full Message for body:
    msg = client.inboxes.messages.get(
        inbox_id=item.inbox_id,
        message_id=item.message_id,
    )
    # Use extracted_text for reply content without quoted history
    content = msg.extracted_text or msg.text
    print(msg.subject, content)

# Paginate
while response.next_page_token:
    response = client.inboxes.messages.list(
        inbox_id="agent@agentmail.to",
        page_token=response.next_page_token,
    )

# Get a specific message
msg = client.inboxes.messages.get(
    inbox_id="agent@agentmail.to",
    message_id="<abc123@agentmail.to>",
)

# Get raw MIME content
raw = client.inboxes.messages.get_raw(
    inbox_id="agent@agentmail.to",
    message_id="<abc123@agentmail.to>",
)
```

```typescript
const response = await client.inboxes.messages.list("agent@agentmail.to", {
    limit: 10,
    labels: ["unread"],
});

const msg = await client.inboxes.messages.get(
    "agent@agentmail.to",
    "<abc123@agentmail.to>",
);
```

**Important**: when processing inbound replies, always use `extracted_text` / `extracted_html` instead of `text` / `html`. These fields strip quoted history and signatures, giving you only the new content. This is powered by Talon reply extraction.

Also note: some email clients (Gmail, Outlook) send forwards as HTML-only. Always treat `html` as the primary content source and `text` as optional.

### Reply

Replying adds the message to the existing thread.

```python
reply = client.inboxes.messages.reply(
    inbox_id="agent@agentmail.to",
    message_id="<abc123@agentmail.to>",
    text="Thanks for your email!",
    html="<p>Thanks for your email!</p>",   # optional
    attachments=[...],                       # optional
    reply_all=False,                         # optional, defaults to False
)
```

```typescript
const reply = await client.inboxes.messages.reply(
    "agent@agentmail.to",
    "<abc123@agentmail.to>",
    { text: "Thanks for your email!" },
);
```

### Forward

```python
client.inboxes.messages.forward(
    inbox_id="agent@agentmail.to",
    message_id="<abc123@agentmail.to>",
    to="colleague@example.com",
    text="FYI, see below.",       # optional prepended text
)
```

```typescript
await client.inboxes.messages.forward(
    "agent@agentmail.to",
    "<abc123@agentmail.to>",
    {
        to: "colleague@example.com",
        text: "FYI, see below.",
    },
);
```

### Update labels

Use labels to track message processing state. AgentMail does not have a built-in "read/unread" flag. Use labels instead.

```python
client.inboxes.messages.update(
    inbox_id="agent@agentmail.to",
    message_id="<abc123@agentmail.to>",
    add_labels=["processed", "replied"],
    remove_labels=["unread"],
)
```

```typescript
await client.inboxes.messages.update(
    "agent@agentmail.to",
    "<abc123@agentmail.to>",
    {
        addLabels: ["processed", "replied"],
        removeLabels: ["unread"],
    },
);
```

### Attachments

```python
import base64

# Send with attachment
with open("report.pdf", "rb") as f:
    content = base64.b64encode(f.read()).decode()

client.inboxes.messages.send(
    inbox_id="agent@agentmail.to",
    to="user@example.com",
    subject="Report attached",
    text="See attached.",
    attachments=[{
        "filename": "report.pdf",
        "content": content,
        "content_type": "application/pdf",
    }],
)

# Retrieve attachment from received message
attachment = client.inboxes.messages.get_attachment(
    inbox_id="agent@agentmail.to",
    message_id="<abc123@agentmail.to>",
    attachment_id="att_456",
)
```

```typescript
import { readFileSync } from "node:fs";

const content = readFileSync("report.pdf").toString("base64");

await client.inboxes.messages.send("agent@agentmail.to", {
    to: "user@example.com",
    subject: "Report attached",
    text: "See attached.",
    attachments: [{ filename: "report.pdf", content, contentType: "application/pdf" }],
});

const attachment = await client.inboxes.messages.getAttachment(
    "agent@agentmail.to",
    "<abc123@agentmail.to>",
    "att_456",
);
```

## Threads

Threads group related messages in a conversation. When you send a new message, a thread is created. Replies are added to the same thread automatically.

```python
# List threads in an inbox
threads = client.inboxes.threads.list(
    inbox_id="agent@agentmail.to",
    labels=["unreplied"],     # optional filter
)

# Get a specific thread with all messages
thread = client.inboxes.threads.get(
    inbox_id="agent@agentmail.to",
    thread_id="thd_123",
)
for msg in thread.messages:
    print(msg.subject, msg.extracted_text)

# Org-wide thread listing (across all inboxes)
all_threads = client.threads.list()

# Delete a thread
client.inboxes.threads.delete(
    inbox_id="agent@agentmail.to",
    thread_id="thd_123",
)
```

```typescript
const threads = await client.inboxes.threads.list("agent@agentmail.to", {
    labels: ["unreplied"],
});

const thread = await client.inboxes.threads.get("agent@agentmail.to", "thd_123");

const allThreads = await client.threads.list();
```

## Drafts

Create drafts for human-in-the-loop approval. The agent composes a draft, a human reviews, then the draft is sent.

```python
# Create draft
draft = client.inboxes.drafts.create(
    inbox_id="agent@agentmail.to",
    to="recipient@example.com",
    subject="Pending approval",
    text="Draft content for review",
    html="<p>Draft content for review</p>",
)

# List drafts
drafts = client.inboxes.drafts.list(inbox_id="agent@agentmail.to")

# Get, update
draft = client.inboxes.drafts.get(inbox_id="agent@agentmail.to", draft_id=draft.draft_id)
client.inboxes.drafts.update(
    inbox_id="agent@agentmail.to",
    draft_id=draft.draft_id,
    text="Updated draft content",
)

# Send draft (converts to message, removes from drafts)
client.inboxes.drafts.send(inbox_id="agent@agentmail.to", draft_id=draft.draft_id)

# Delete draft without sending
client.inboxes.drafts.delete(inbox_id="agent@agentmail.to", draft_id=draft.draft_id)
```

```typescript
const draft = await client.inboxes.drafts.create("agent@agentmail.to", {
    to: "recipient@example.com",
    subject: "Pending approval",
    text: "Draft content",
});

await client.inboxes.drafts.send("agent@agentmail.to", draft.draftId, {});
```

## Pods (multi-tenant isolation)

Pods provide isolated environments for SaaS platforms. Each pod has its own set of inboxes.

```python
# Create pod per customer
pod = client.pods.create(
    name="customer-acme",
    client_id="pod-acme-v1",   # idempotent
)

# Create inbox within pod (pods.inboxes.create accepts flat kwargs)
inbox = client.pods.inboxes.create(
    pod_id=pod.pod_id,
    username="notifications",
    client_id="acme-notifications-v1",
)

# List inboxes scoped to pod
inboxes = client.pods.inboxes.list(pod_id=pod.pod_id)

# List threads scoped to pod
threads = client.pods.threads.list(pod_id=pod.pod_id)

# List, get, delete pods
pods = client.pods.list()
pod = client.pods.get(pod_id=pod.pod_id)
client.pods.delete(pod_id=pod.pod_id)
```

```typescript
const pod = await client.pods.create({ name: "customer-acme", clientId: "pod-acme-v1" });
const inbox = await client.pods.inboxes.create(pod.podId, {
    username: "notifications",
    clientId: "acme-notifications-v1",
});
const inboxes = await client.pods.inboxes.list(pod.podId);
```

## Allow/block lists

Control which external senders can deliver to an inbox. Block list takes priority over allow list.

Lists are flat. Each entry is one `(direction, type, entry)` tuple — there is no batch update, no `.allow` / `.block` sub-namespace. `direction` is `"send"`, `"receive"`, or `"reply"`. `type` is `"allow"` or `"block"`.

```python
# Allow a sender on incoming mail
client.inboxes.lists.create(
    inbox_id="agent@agentmail.to",
    direction="receive",
    type="allow",
    entry="boss@company.com",
)

# Block a sender on incoming mail
client.inboxes.lists.create(
    inbox_id="agent@agentmail.to",
    direction="receive",
    type="block",
    entry="spammer@example.com",
)

# List entries for one (direction, type) pair
allow = client.inboxes.lists.list(
    inbox_id="agent@agentmail.to",
    direction="receive",
    type="allow",
)

# Check a single entry
entry = client.inboxes.lists.get(
    inbox_id="agent@agentmail.to",
    direction="receive",
    type="allow",
    entry="boss@company.com",
)

# Remove an entry
client.inboxes.lists.delete(
    inbox_id="agent@agentmail.to",
    direction="receive",
    type="allow",
    entry="boss@company.com",
)
```

```typescript
await client.inboxes.lists.create(
    "agent@agentmail.to",
    "receive",
    "allow",
    { entry: "boss@company.com" },
);

await client.inboxes.lists.create(
    "agent@agentmail.to",
    "receive",
    "block",
    { entry: "spammer@example.com" },
);

const allow = await client.inboxes.lists.list(
    "agent@agentmail.to",
    "receive",
    "allow",
);

await client.inboxes.lists.delete(
    "agent@agentmail.to",
    "receive",
    "allow",
    "boss@company.com",
);
```

## Domains

Custom domains let agents send from your own domain (e.g., `agent@yourdomain.com`). SPF, DKIM, and DMARC records are auto-generated. Requires paid plan.

```python
# Add domain. feedback_enabled is required: set True to route
# bounce/complaint notifications to your inboxes.
domain = client.domains.create(domain="yourdomain.com", feedback_enabled=True)
# domain.records -> list of VerificationRecord objects to add at your registrar

# Verify after DNS records are set
client.domains.verify(domain_id=domain.domain_id)

# List, get, delete
domains = client.domains.list()
domain = client.domains.get(domain_id=domain.domain_id)
client.domains.delete(domain_id=domain.domain_id)
```

```typescript
const domain = await client.domains.create({
    domain: "yourdomain.com",
    feedbackEnabled: true,
});
await client.domains.verify(domain.domainId);
```

## Real-time events

AgentMail supports both WebSockets and webhooks for real-time notifications. See `references/webhooks.md` and `references/websockets.md` for detailed setup and full code examples.

### WebSockets (recommended for agents)

No public URL needed. Persistent connection with instant delivery.

**Python (sync):**
```python
from agentmail import AgentMail, Subscribe, Subscribed, MessageReceivedEvent

client = AgentMail()
with client.websockets.connect() as socket:
    socket.send_subscribe(Subscribe(inbox_ids=["agent@agentmail.to"]))
    for event in socket:
        if isinstance(event, Subscribed):
            print(f"Subscribed to: {event.inbox_ids}")
        elif isinstance(event, MessageReceivedEvent):
            print(f"From: {event.message.from_}")
            print(f"Subject: {event.message.subject}")
            print(f"Body: {event.message.extracted_text}")
```

**Python (async):**
```python
from agentmail import AsyncAgentMail, Subscribe, MessageReceivedEvent

client = AsyncAgentMail()
async with client.websockets.connect() as socket:
    await socket.send_subscribe(Subscribe(inbox_ids=["agent@agentmail.to"]))
    async for event in socket:
        if isinstance(event, MessageReceivedEvent):
            await process_email(event.message)
```

**TypeScript:**
```typescript
const socket = await client.websockets.connect();
socket.on("open", () => {
    socket.sendSubscribe({ type: "subscribe", inboxIds: ["agent@agentmail.to"] });
});
socket.on("message", (event) => {
    // Use event.eventType (not event.type — event.type is always "event")
    if (event.eventType === "message.received") {
        // TypeScript uses .from directly; only Python needs .from_ (reserved keyword)
        console.log("From:", event.message.from);
        console.log("Subject:", event.message.subject);
    }
});
```

### Webhooks

HTTP POST to your endpoint on email events. Requires a public URL.

`event_types` is **required** — you must pick at least one event to subscribe to. Pass an explicit list of every event you want to receive.

```python
webhook = client.webhooks.create(
    url="https://your-server.com/webhooks",
    event_types=["message.received", "message.bounced"],
)
# webhook.webhook_id, webhook.secret

# List, get, delete
webhooks = client.webhooks.list()
client.webhooks.delete(webhook_id=webhook.webhook_id)
```

Typed webhook event types (listed in the SDK's Literal): `message.received`, `message.sent`, `message.delivered`, `message.bounced`, `message.complained`, `message.rejected`, `domain.verified`.

Runtime-only events — accepted by the API but not in the SDK's typed Literal — include `message.received.spam` and `message.received.blocked`. Pass them as plain strings if you need them. Type checkers will flag them; that's expected.

Always verify webhook signatures before processing. See `references/webhooks.md`.

## Idempotency

Pass `client_id` / `clientId` on create operations to make them safe to retry:

```python
from agentmail.inboxes.types import CreateInboxRequest

inbox = client.inboxes.create(
    request=CreateInboxRequest(client_id="my-unique-key"),
)
# Calling again with the same client_id returns the existing inbox, not a duplicate

pod = client.pods.create(client_id="pod-unique-key")
# pods.create takes flat kwargs; same idempotency behavior
```

## Error handling

Both SDKs raise/throw on 4xx and 5xx responses. On 429 (rate limit), read the `Retry-After` header and use exponential backoff. Both SDKs retry automatically (default: 2 retries).

```python
try:
    client.inboxes.messages.send(inbox_id, to="user@example.com", subject="Hi", text="Hello")
except Exception as e:
    print(f"Error: {e}")
    # e.body.message contains details if available

# Python: override retries per call via request_options
# (the AgentMail constructor has no max_retries argument)
client.inboxes.messages.send(
    inbox_id,
    to="user@example.com",
    subject="Hi",
    text="Hello",
    request_options={"max_retries": 5},
)
```

```typescript
try {
    await client.inboxes.messages.send(inboxId, {
        to: "user@example.com",
        subject: "Hi",
        text: "Hello",
    });
} catch (err) {
    console.error("Error:", err.message);
    // err.statusCode, err.body for details
}

// TypeScript: override retries globally on the client, or per-call via requestOptions
const client = new AgentMailClient({ apiKey: "...", maxRetries: 5 });
```

## IMAP and SMTP

AgentMail inboxes are accessible via standard IMAP and SMTP protocols, enabling integration with traditional email clients and legacy systems. See https://docs.agentmail.to/imap-smtp for setup details.

## Pagination

All list endpoints use cursor-based pagination:

```python
response = client.inboxes.messages.list(inbox_id, limit=20)
while response.next_page_token:
    response = client.inboxes.messages.list(
        inbox_id, limit=20, page_token=response.next_page_token
    )
```

## Reference files

For detailed coverage of specific topics:
- `references/webhooks.md` -- webhook setup, event types, payload structure, signature verification
- `references/websockets.md` -- WebSocket connection, sync/async patterns, event handler pattern, subscribe options
- `references/full-api-reference.md` -- complete endpoint and SDK method table with all parameters
