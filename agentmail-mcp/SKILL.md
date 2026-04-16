---
name: agentmail-mcp
description: AgentMail MCP server for email tools in AI assistants. Use when setting up AgentMail with Claude Desktop, Cursor, VS Code, Windsurf, or other MCP-compatible clients. Provides tools for inbox management, sending/receiving emails, and thread handling.
---

# AgentMail MCP Server

Connect AgentMail to any MCP-compatible AI client. Three setup options available.

## Prerequisites

Get your API key from [console.agentmail.to](https://console.agentmail.to).

---

## Option 1: Remote MCP (Simplest)

No installation required. Connect directly to the hosted MCP server.

**URL:** `https://mcp.agentmail.to`

**Authentication:** OAuth 2.0 via Smithery. The remote server does NOT accept an API key in
env — it returns `401 Bearer error="invalid_token"` and redirects your MCP client through
the OAuth authorization server at `https://auth.smithery.ai/agentmail`. The MCP client
handles the browser-based consent flow automatically on first connect.

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "AgentMail": {
      "url": "https://mcp.agentmail.to"
    }
  }
}
```

On first use, your MCP client opens a browser window to complete the Smithery OAuth flow;
after approval, tokens are cached by the client. If you need API-key auth (no OAuth flow),
use Option 2 or Option 3 below instead.

---

## Option 2: Local npm Package

Run the MCP server locally via npx.

```json
{
  "mcpServers": {
    "AgentMail": {
      "command": "npx",
      "args": ["-y", "agentmail-mcp"],
      "env": {
        "AGENTMAIL_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

### Tool Selection

Load only specific tools with the `--tools` argument:

```json
{
  "mcpServers": {
    "AgentMail": {
      "command": "npx",
      "args": [
        "-y",
        "agentmail-mcp",
        "--tools",
        "send_message,reply_to_message,list_inboxes"
      ],
      "env": {
        "AGENTMAIL_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

---

## Option 3: Local Python Package

Install and run the Python MCP server.

```bash
pip install agentmail-mcp
```

### Claude Desktop

Config location:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`

The server accepts the API key in two ways: via `AGENTMAIL_API_KEY` env var, or via the
`--api-key` CLI flag. Use whichever works in your MCP client's launcher environment.

```json
{
  "mcpServers": {
    "AgentMail": {
      "command": "/path/to/your/.venv/bin/agentmail-mcp",
      "env": {
        "AGENTMAIL_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

If env vars don't propagate through your MCP launcher, pass the key as an argument
instead:

```json
{
  "mcpServers": {
    "AgentMail": {
      "command": "/path/to/your/.venv/bin/agentmail-mcp",
      "args": ["--api-key", "YOUR_API_KEY"]
    }
  }
}
```

Find your path:

```bash
# Activate your virtual environment, then:
which agentmail-mcp
```

### Run Standalone

```bash
# Option A: env var
export AGENTMAIL_API_KEY=your-api-key
agentmail-mcp

# Option B: CLI flag (useful if env vars aren't available)
agentmail-mcp --api-key="your-api-key"
```

---

## Available Tools

The Node MCP server (`npx agentmail-mcp`, Option 1 and Option 2) exposes **17 tools**:

| Tool               | Description                     |
| ------------------ | ------------------------------- |
| `create_inbox`     | Create a new email inbox        |
| `list_inboxes`     | List all inboxes                |
| `get_inbox`        | Get inbox details by ID         |
| `delete_inbox`     | Delete an inbox                 |
| `send_message`     | Send an email from an inbox     |
| `reply_to_message` | Reply to an existing message    |
| `forward_message`  | Forward an existing message     |
| `list_threads`     | List email threads in an inbox  |
| `get_thread`       | Get thread details and messages |
| `get_attachment`   | Download an attachment          |
| `update_message`   | Update message labels           |
| `create_draft`     | Create a draft message          |
| `list_drafts`      | List drafts in an inbox         |
| `get_draft`        | Get a draft by ID               |
| `update_draft`     | Update a draft                  |
| `send_draft`       | Send a previously-created draft |
| `delete_draft`     | Delete a draft without sending  |

The legacy **Python MCP server** (`pip install agentmail-mcp`, Option 3) is a separate
codebase with a smaller tool set — it omits the six `*_draft` tools above. For new
projects, prefer the Node server (Option 1 or Option 2) for full parity with the toolkit.

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
      "command": "npx",
      "args": ["-y", "agentmail-mcp"],
      "env": {
        "AGENTMAIL_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

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

### "Command not found"

Ensure npm/npx is in your PATH, or use the full path:

```json
"command": "/usr/local/bin/npx"
```

### "Invalid API key"

Verify your API key is correct and has the necessary permissions.

### Python package not found

Use the full path to the agentmail-mcp executable in your virtual environment:

```bash
# Find the path
source /path/to/venv/bin/activate
which agentmail-mcp
```
