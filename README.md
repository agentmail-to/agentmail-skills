# AgentMail Agent Skills

Canonical source for AgentMail's agent skills. Skills here are authored in this repository; every other first-party copy (Claude/Codex/Cursor plugins, product profiles, docs examples) is generated from it.

## Install

```bash
# All skills
npx skills add agentmail-to/agentmail-skills

# One skill
npx skills add agentmail-to/agentmail-skills --skill agentmail
```

Or as a plugin: `/plugin install agentmail@agentmail` (Claude Code).

## Skills

| Skill | Job |
| --- | --- |
| `agentmail` | Build with the AgentMail TypeScript or Python SDK |
| `agentmail-cli` | Install, authenticate, script, and troubleshoot the CLI |
| `agentmail-mcp` | Configure and troubleshoot an AgentMail MCP connection |
| `agentmail-toolkit` | Framework integrations (Vercel AI SDK, LangChain, OpenAI Agents, LiveKit) |
| `agent-email-patterns` | Agent-email architecture, security threat model, provider tradeoffs |
| `agentmail-send-email` | Draft, send, reply, forward through AgentMail MCP tools |
| `agentmail-check-email` | Read, search, summarize, triage inboxes |
| `agentmail-manage-inboxes` | Create, update, delete inboxes |

`agentmail-sdk` and `email-for-ai-agents` are deprecated aliases (identical generated copies of `agentmail` and `agent-email-patterns`) kept so existing installs and pinned URLs keep resolving — don't install them alongside their replacements.

## Contributing

PRs welcome against this repository — skill content merged here ships to installers immediately (`npx skills add` tracks `main`). Generated copies elsewhere are overwritten on the next export; don't PR those repos.
