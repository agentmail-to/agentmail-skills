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

## Tool Discovery

MCP clients obtain the current tool catalog and schemas directly from the hosted runtime. The same generated contract is published at:

`https://github.com/agentmail-to/agentmail-mcp/blob/main/mcp-manifest.json`

Do not rely on a copied tool count. OAuth sessions can receive additional organization-selection tools.

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

## Stdio Compatibility

For clients that cannot connect to remote MCP servers, the supported npm and PyPI
`agentmail-mcp` packages are thin stdio bridges to the same hosted runtime. They discover
tools dynamically and do not contain separate AgentMail tool logic.
