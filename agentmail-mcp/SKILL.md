---
name: agentmail-mcp
description: AgentMail MCP server for email tools in AI assistants. Use when setting up AgentMail with Claude Desktop, Cursor, VS Code, Windsurf, or other MCP-compatible clients. Provides tools for inbox management, sending/receiving emails, and thread handling.
---

# AgentMail MCP Server

Connect AgentMail to any MCP-compatible AI client via the hosted MCP server.

## Prerequisites

Get your API key from [console.agentmail.to](https://console.agentmail.to).

---

## Remote MCP Server (Recommended)

No installation required. Connect directly to the hosted MCP server.

**URL:** `https://mcp.agentmail.to/mcp`

**Authentication:** Either OAuth (browser-based sign-in, for clients that support remote MCP
OAuth) or an API key — pass it as the `apiKey` query param, an `x-api-key` header, or an
`Authorization: Bearer <am_ key>` header.

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "AgentMail": {
      "url": "https://mcp.agentmail.to/mcp?apiKey=YOUR_API_KEY"
    }
  }
}
```

Clients that support remote-MCP OAuth can instead use the bare URL
(`https://mcp.agentmail.to/mcp`) and authenticate in-flow, without an `apiKey` param.

---

## Client Configuration

### Cursor, VS Code, Windsurf

Add the same MCP server entry in your client config file:

Cursor: `.cursor/mcp.json`  
VS Code: `.vscode/mcp.json`  
Windsurf: MCP config file

```json
{
  "mcpServers": {
    "AgentMail": {
      "url": "https://mcp.agentmail.to/mcp?apiKey=YOUR_API_KEY"
    }
  }
}
```

### Claude Desktop

Config location:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "AgentMail": {
      "url": "https://mcp.agentmail.to/mcp?apiKey=YOUR_API_KEY"
    }
  }
}
```

---

## Available Tools

The hosted MCP server (`https://mcp.agentmail.to/mcp`) exposes **24 tools**:

| Tool                | Description                                                                                          |
| -------------------- | ----------------------------------------------------------------------------------------------------- |
| `list_inboxes`       | List email inboxes, paginated.                                                                        |
| `get_inbox`          | Get an inbox by ID.                                                                                    |
| `create_inbox`       | Create a new email inbox. Optionally specify username, domain, display name, and metadata.             |
| `update_inbox`       | Update an inbox's display name or metadata (metadata keys merge; null removes).                        |
| `delete_inbox`       | Delete an inbox by ID.                                                                                  |
| `list_threads`       | List email threads in an inbox. Filter by labels, sender, recipient, subject, or before/after datetime, paginated. |
| `search_threads`     | Full-text search threads in an inbox, ranked by relevance (spam/trash excluded).                        |
| `get_thread`         | Get a thread by ID, including its messages.                                                             |
| `get_attachment`     | Get an attachment from a thread. Returns metadata and a download URL, plus extracted text for PDF/DOCX. |
| `update_thread`      | Update a thread's labels (add or remove). System labels cannot be modified.                             |
| `delete_thread`      | Delete a thread from an inbox.                                                                          |
| `list_messages`      | List messages in an inbox. Filter by labels, sender, recipient, subject, or before/after datetime, paginated. |
| `search_messages`    | Full-text search messages in an inbox, ranked by relevance (spam/trash excluded).                       |
| `send_message`       | Send an email from an inbox to one or more recipients.                                                  |
| `reply_to_message`   | Reply to a message in its thread (replyAll to include all original recipients).                         |
| `forward_message`    | Forward a message to new recipients.                                                                    |
| `update_message`     | Update a message's labels (add or remove).                                                              |
| `create_draft`       | Create a draft email. Use sendAt (ISO 8601) to schedule it.                                             |
| `list_drafts`        | List drafts in an inbox. Filter by labels (e.g. "scheduled").                                           |
| `get_draft`          | Get a draft by ID, including content, status, and scheduled send time.                                  |
| `update_draft`       | Update a draft. Use sendAt to reschedule.                                                                |
| `send_draft`         | Send a draft immediately (converted to a sent message and deleted).                                     |
| `delete_draft`       | Delete a draft. Also cancels a scheduled send.                                                          |
| `auth_me`            | Get the identity and scope of the authenticated credential (organization, pod, inbox IDs).              |

---

## Compatible Clients

The AgentMail MCP server works with any MCP-compatible client:

- Claude Desktop
- Cursor
- VS Code
- Windsurf
- Cline
- Goose
- Raycast
- ChatGPT
- Amazon Q
- Codex
- Gemini CLI
- LibreChat
- Roo Code
- And more...

---

## Example Usage

Once configured, you can ask your AI assistant:

- "Create a new inbox for support emails"
- "Send an email to john@example.com with subject 'Hello'"
- "Check my inbox for new messages"
- "Reply to the latest email thanking them"
- "List all my email threads"
- "Download the attachment from the last message"

---

## Troubleshooting

### "Invalid API key"

Verify your API key is correct and has the necessary permissions.

### "Unauthorized" / OAuth issues

If your client supports remote MCP OAuth, drop the `apiKey` query param and let the client
complete the browser-based sign-in flow instead.

---

## Deprecated: Local Packages

The local `npx agentmail-mcp` (Node) and `pip install agentmail-mcp` (Python) stdio servers
are deprecated in favor of the hosted server above. They are no longer actively maintained
and may be removed in a future release — use the [Remote MCP Server](#remote-mcp-server-recommended)
instead.
