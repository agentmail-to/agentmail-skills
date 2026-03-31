# AgentMail Skills

Pre-built skills that teach AI coding agents (Claude Code, Cursor, Windsurf, etc.) how to use AgentMail.

## What are Skills?

Skills are structured knowledge packs — each contains a `SKILL.md` file with API patterns, code examples, and best practices. When an AI agent loads a skill, it can immediately build with the tool without needing documentation lookup.

## Available Skills

| Skill | Description |
|---|---|
| [`agentmail`](./agentmail) | Core AgentMail SDK — create inboxes, send/receive email, manage threads, labels, attachments, drafts, webhooks, and websockets |
| [`agentmail-cli`](./agentmail-cli) | AgentMail CLI — manage inboxes and email from the terminal |
| [`agentmail-mcp`](./agentmail-mcp) | AgentMail MCP Server — connect AI clients to email via Model Context Protocol |
| [`agentmail-toolkit`](./agentmail-toolkit) | AgentMail Toolkit — integrations for OpenAI Agents SDK, Vercel AI SDK, and MCP |

## Usage

### Claude Code

```bash
# Add a skill to your project
claude mcp add-skill agentmail https://github.com/agentmail-to/agentmail-skills/tree/main/agentmail
```

Or copy the `SKILL.md` file into your project's context.

### Other Agents

Copy the relevant `SKILL.md` into your agent's system prompt or knowledge base.

## Links

- [AgentMail](https://agentmail.to) — The email API for AI agents
- [Documentation](https://docs.agentmail.to)
- [Python SDK](https://github.com/agentmail-to/agentmail-python)
- [TypeScript SDK](https://github.com/agentmail-to/agentmail-node)
- [MCP Server](https://mcp.agentmail.to)
