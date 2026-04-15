# Full API Reference

Complete endpoint and SDK method mapping for AgentMail.

**Base URL:** `https://api.agentmail.to/v0`
**Authentication:** `Authorization: Bearer am_...`

## Agent

| Operation | Method | Python | TypeScript |
|---|---|---|---|
| Sign up | `POST /agent/sign-up` | `client.agent.sign_up(human_email, username)` | `client.agent.signUp({ humanEmail, username })` |
| Verify | `POST /agent/verify` | `client.agent.verify(otp_code)` | `client.agent.verify({ otpCode })` |

Returns: `api_key`, `inbox_id`, `organization_id`. Sign-up is idempotent.

## Inboxes

| Operation | Method | Python | TypeScript |
|---|---|---|---|
| Create | `POST /inboxes` | `client.inboxes.create(request=CreateInboxRequest(username?, domain?, display_name?, client_id?))` | `client.inboxes.create({ username?, domain?, displayName?, clientId? })` |
| List | `GET /inboxes` | `client.inboxes.list(limit?, page_token?)` | `client.inboxes.list({ limit?, pageToken? })` |
| Get | `GET /inboxes/:inbox_id` | `client.inboxes.get(inbox_id)` | `client.inboxes.get(inboxId)` |
| Update | `PATCH /inboxes/:inbox_id` | `client.inboxes.update(inbox_id, display_name)` | `client.inboxes.update(inboxId, { displayName })` |
| Delete | `DELETE /inboxes/:inbox_id` | `client.inboxes.delete(inbox_id)` | `client.inboxes.delete(inboxId)` |

The Python `inboxes.create` only takes a single `request=CreateInboxRequest(...)` argument — not flat kwargs. Import it from `agentmail.inboxes.types import CreateInboxRequest`. To create inboxes scoped to a pod, use `client.pods.inboxes.create(pod_id, ...)` (which *does* accept flat kwargs).

Inbox fields: `inbox_id`, `email_address`, `username`, `domain`, `display_name`, `pod_id`, `created_at`.

## Messages

| Operation | Method | Python | TypeScript |
|---|---|---|---|
| Send | `POST /inboxes/:id/messages/send` | `client.inboxes.messages.send(inbox_id, to, subject, text, html?, cc?, bcc?, reply_to?, labels?, attachments?, headers?)` | `client.inboxes.messages.send(inboxId, { to, subject, text, html?, cc?, bcc?, replyTo?, labels?, attachments?, headers? })` |
| List | `GET /inboxes/:id/messages` | `client.inboxes.messages.list(inbox_id, limit?, page_token?, labels?)` | `client.inboxes.messages.list(inboxId, { limit?, pageToken?, labels? })` |
| Get | `GET /inboxes/:id/messages/:msg_id` | `client.inboxes.messages.get(inbox_id, message_id)` | `client.inboxes.messages.get(inboxId, messageId)` |
| Reply | `POST /inboxes/:id/messages/:msg_id/reply` | `client.inboxes.messages.reply(inbox_id, message_id, text, html?, attachments?, reply_all?)` | `client.inboxes.messages.reply(inboxId, messageId, { text, html?, attachments?, replyAll? })` |
| Forward | `POST /inboxes/:id/messages/:msg_id/forward` | `client.inboxes.messages.forward(inbox_id, message_id, to, subject?, text?, html?)` | `client.inboxes.messages.forward(inboxId, messageId, { to, subject?, text?, html? })` |
| Update | `PATCH /inboxes/:id/messages/:msg_id` | `client.inboxes.messages.update(inbox_id, message_id, add_labels?, remove_labels?)` | `client.inboxes.messages.update(inboxId, messageId, { addLabels?, removeLabels? })` |
| Get raw | `GET /inboxes/:id/messages/:msg_id/raw` | `client.inboxes.messages.get_raw(inbox_id, message_id)` | `client.inboxes.messages.getRaw(inboxId, messageId)` |
| Get attachment | `GET /inboxes/:id/messages/:msg_id/attachments/:att_id` | `client.inboxes.messages.get_attachment(inbox_id, message_id, attachment_id)` | `client.inboxes.messages.getAttachment(inboxId, messageId, attachmentId)` |

The Python `inboxes.messages` module has no `delete` method — deleting individual messages is not supported from Python. Delete threads instead (`client.inboxes.threads.delete`). TypeScript exposes `client.inboxes.messages.delete(inboxId, messageId)`.

### Message fields (received)

| Field | Description |
|---|---|
| `message_id` | Unique message identifier |
| `thread_id` | Thread this message belongs to |
| `inbox_id` | Inbox that received/sent this message |
| `from_` / `from` | Sender address(es) |
| `to` | Recipient address(es) |
| `cc`, `bcc` | CC and BCC addresses |
| `subject` | Subject line |
| `text` | Plain text body (may be absent on forwarded emails) |
| `html` | HTML body (primary content source) |
| `extracted_text` | Reply content only, quoted history stripped (Talon) |
| `extracted_html` | Reply HTML content only, quoted history stripped |
| `preview` | Short preview text |
| `attachments` | List of attachment metadata |
| `labels` | List of labels |
| `headers` | Email headers |
| `created_at` | Timestamp |

Always prefer `extracted_text` / `extracted_html` for processing replies.

### Send parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `to` | string or list | Yes | Recipient(s) |
| `subject` | string | Yes | Subject line |
| `text` | string | Yes | Plain text body |
| `html` | string | No | HTML body (recommended) |
| `cc` | string or list | No | CC recipients |
| `bcc` | string or list | No | BCC recipients |
| `reply_to` | string or list | No | Reply-to address |
| `labels` | list of strings | No | Labels for organization |
| `attachments` | list | No | Base64-encoded files |
| `headers` | dict | No | Custom email headers |

Max 50 recipients across to + cc + bcc combined.

## Threads

| Operation | Method | Python | TypeScript |
|---|---|---|---|
| List (inbox) | `GET /inboxes/:id/threads` | `client.inboxes.threads.list(inbox_id, limit?, page_token?, labels?)` | `client.inboxes.threads.list(inboxId, { limit?, pageToken?, labels? })` |
| Get | `GET /inboxes/:id/threads/:thd_id` | `client.inboxes.threads.get(inbox_id, thread_id)` | `client.inboxes.threads.get(inboxId, threadId)` |
| Delete | `DELETE /inboxes/:id/threads/:thd_id` | `client.inboxes.threads.delete(inbox_id, thread_id)` | `client.inboxes.threads.delete(inboxId, threadId)` |
| List (org-wide) | `GET /threads` | `client.threads.list(limit?, page_token?, labels?)` | `client.threads.list({ limit?, pageToken?, labels? })` |
| List (pod-scoped) | `GET /pods/:pod_id/threads` | `client.pods.threads.list(pod_id, limit?, page_token?, labels?)` | `client.pods.threads.list(podId, { limit?, pageToken?, labels? })` |

Top-level `threads.list` lists threads across *all* inboxes in the organization — there is no `pod_id` filter. To scope to a single pod, use `pods.threads.list(pod_id)`.

## Drafts

| Operation | Method | Python | TypeScript |
|---|---|---|---|
| Create | `POST /inboxes/:id/drafts` | `client.inboxes.drafts.create(inbox_id, to?, subject?, text?, html?, cc?, bcc?, reply_to?, attachments?)` | `client.inboxes.drafts.create(inboxId, { to?, subject?, text?, html?, ... })` |
| List | `GET /inboxes/:id/drafts` | `client.inboxes.drafts.list(inbox_id)` | `client.inboxes.drafts.list(inboxId)` |
| Get | `GET /inboxes/:id/drafts/:draft_id` | `client.inboxes.drafts.get(inbox_id, draft_id)` | `client.inboxes.drafts.get(inboxId, draftId)` |
| Update | `PATCH /inboxes/:id/drafts/:draft_id` | `client.inboxes.drafts.update(inbox_id, draft_id, ...)` | `client.inboxes.drafts.update(inboxId, draftId, { ... })` |
| Send | `POST /inboxes/:id/drafts/:draft_id/send` | `client.inboxes.drafts.send(inbox_id, draft_id)` | `client.inboxes.drafts.send(inboxId, draftId, {})` |
| Delete | `DELETE /inboxes/:id/drafts/:draft_id` | `client.inboxes.drafts.delete(inbox_id, draft_id)` | `client.inboxes.drafts.delete(inboxId, draftId)` |

## Webhooks

| Operation | Method | Python | TypeScript |
|---|---|---|---|
| Create | `POST /webhooks` | `client.webhooks.create(url, event_types, inbox_ids?, pod_ids?, client_id?)` | `client.webhooks.create({ url, eventTypes, inboxIds?, podIds?, clientId? })` |
| List | `GET /webhooks` | `client.webhooks.list()` | `client.webhooks.list()` |
| Get | `GET /webhooks/:id` | `client.webhooks.get(webhook_id)` | `client.webhooks.get(webhookId)` |
| Delete | `DELETE /webhooks/:id` | `client.webhooks.delete(webhook_id)` | `client.webhooks.delete(webhookId)` |

`event_types` / `eventTypes` is **required**. Typed values: `message.received`, `message.sent`, `message.delivered`, `message.bounced`, `message.complained`, `message.rejected`, `domain.verified`. Runtime-only (accepted but not in the SDK Literal): `message.received.spam`, `message.received.blocked`.

## Domains

| Operation | Method | Python | TypeScript |
|---|---|---|---|
| Create | `POST /domains` | `client.domains.create(domain, feedback_enabled)` | `client.domains.create({ domain, feedbackEnabled })` |
| List | `GET /domains` | `client.domains.list()` | `client.domains.list()` |
| Get | `GET /domains/:id` | `client.domains.get(domain_id)` | `client.domains.get(domainId)` |
| Verify | `POST /domains/:id/verify` | `client.domains.verify(domain_id)` | `client.domains.verify(domainId)` |
| Delete | `DELETE /domains/:id` | `client.domains.delete(domain_id)` | `client.domains.delete(domainId)` |

`feedback_enabled` / `feedbackEnabled` is **required** on create. Set it to `True` to route bounce and complaint notifications to your inboxes.

## Lists (allow/block)

Lists are flat, entry-per-call. There is no batch `.update` and no `.allow` / `.block` sub-namespace. Each entry is identified by `(inbox_id, direction, type, entry)`. `direction` is one of `"send"`, `"receive"`, `"reply"`. `type` is one of `"allow"`, `"block"`.

| Operation | Method | Python | TypeScript |
|---|---|---|---|
| List entries | `GET /inboxes/:id/lists/:direction/:type` | `client.inboxes.lists.list(inbox_id, direction, type, limit?, page_token?)` | `client.inboxes.lists.list(inboxId, direction, type, { limit?, pageToken? })` |
| Get entry | `GET /inboxes/:id/lists/:direction/:type/:entry` | `client.inboxes.lists.get(inbox_id, direction, type, entry)` | `client.inboxes.lists.get(inboxId, direction, type, entry)` |
| Create entry | `POST /inboxes/:id/lists/:direction/:type` | `client.inboxes.lists.create(inbox_id, direction, type, entry, reason?)` | `client.inboxes.lists.create(inboxId, direction, type, { entry, reason? })` |
| Delete entry | `DELETE /inboxes/:id/lists/:direction/:type/:entry` | `client.inboxes.lists.delete(inbox_id, direction, type, entry)` | `client.inboxes.lists.delete(inboxId, direction, type, entry)` |

To allow `boss@company.com` to send mail to the inbox: `client.inboxes.lists.create(inbox_id, direction="receive", type="allow", entry="boss@company.com")`. Replace an allow list by deleting existing entries and creating new ones — there is no bulk update.

## Pods

| Operation | Method | Python | TypeScript |
|---|---|---|---|
| Create | `POST /pods` | `client.pods.create(name?, client_id?)` | `client.pods.create({ name?, clientId? })` |
| List | `GET /pods` | `client.pods.list()` | `client.pods.list()` |
| Get | `GET /pods/:id` | `client.pods.get(pod_id)` | `client.pods.get(podId)` |
| Delete | `DELETE /pods/:id` | `client.pods.delete(pod_id)` | `client.pods.delete(podId)` |

## API Keys

| Operation | Method | Python | TypeScript |
|---|---|---|---|
| Create | `POST /api-keys` | `client.api_keys.create(name, permissions?)` | `client.apiKeys.create({ name, permissions? })` |
| List | `GET /api-keys` | `client.api_keys.list()` | `client.apiKeys.list()` |
| Delete | `DELETE /api-keys/:id` | `client.api_keys.delete(api_key_id)` | `client.apiKeys.delete(apiKeyId)` |

`name` is **required** on create.

## Metrics

| Operation | Method | Python | TypeScript |
|---|---|---|---|
| Query | `GET /metrics` | `client.metrics.query(event_types?, start?, end?, period?, limit?, descending?)` | `client.metrics.query({ eventTypes?, start?, end?, period?, limit?, descending? })` |

The method is `query`, not `get`, in both Python and TypeScript.

## Pagination

All list endpoints use cursor-based pagination with `limit` and `page_token` / `pageToken`. The response includes `next_page_token` / `nextPageToken` when more results are available.

## Rate limits

429 responses include `Retry-After` header. Both SDKs retry automatically with exponential backoff (default: 2 retries).

- **TypeScript**: override globally via `new AgentMailClient({ apiKey, maxRetries: 5 })` or per-call via `requestOptions.maxRetries`.
- **Python**: `AgentMail(...)` has no `max_retries` constructor arg. Override per-call with `request_options={"max_retries": 5}`.
