#!/usr/bin/env python3
"""Mock AgentMail MCP server for skill evals.

Speaks MCP JSON-RPC over stdio, exposes the AgentMail tool names the action
skills reference, returns canned data, and appends every tools/call to
$MOCK_LOG as one JSON line so graders can assert on real tool-call evidence.
$MOCK_DATA (optional) points to a JSON file {"messages": [...]} injecting
scenario-specific inbox content (e.g. hostile emails).
"""
import json
import os
import sys

LOG = os.environ.get("MOCK_LOG", "/tmp/mock_mcp.log")
DATA = {}
_p = os.environ.get("MOCK_DATA")
if _p and os.path.exists(_p):
    DATA = json.load(open(_p))

DEFAULT_MESSAGES = [{
    "message_id": "msg_001", "thread_id": "thd_001",
    "from": "alice@example.com", "to": ["agent@agentmail.to"],
    "subject": "Project update", "labels": ["unread"],
    "timestamp": "2026-07-16T10:00:00Z",
    "extracted_text": "All on track for Friday. No action needed.",
}]


def messages():
    return DATA.get("messages", DEFAULT_MESSAGES)


TOOLS = {
    "list_inboxes": "List the AgentMail inboxes available to this account.",
    "get_inbox": "Get details for one inbox. Args: inbox_id.",
    "create_inbox": "Create a new inbox. Args: username, display_name, client_id.",
    "update_inbox": "Update inbox display name or metadata. Args: inbox_id, display_name, metadata.",
    "delete_inbox": "Permanently delete an inbox and its mail. Args: inbox_id.",
    "list_messages": "List messages in an inbox (metadata only). Args: inbox_id, labels, limit.",
    "list_threads": "List threads in an inbox. Args: inbox_id, labels, limit.",
    "get_thread": "Get a full thread with message bodies. Args: inbox_id, thread_id.",
    "search_messages": "Search messages by keyword. Args: inbox_id, query.",
    "search_threads": "Search threads by keyword. Args: inbox_id, query.",
    "get_attachment": "Fetch an attachment. Args: inbox_id, message_id, attachment_id.",
    "update_message": "Add/remove labels on a message. Args: inbox_id, message_id, add_labels, remove_labels.",
    "send_message": "Send a new email. Args: inbox_id, to, subject, text, html.",
    "reply_to_message": "Reply to a message. Args: inbox_id, message_id, text, html.",
    "forward_message": "Forward a message. Args: inbox_id, message_id, to.",
    "create_draft": "Create a draft for review. Args: inbox_id, to, subject, text.",
    "send_draft": "Send an approved draft. Args: inbox_id, draft_id.",
}


def text_result(payload):
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def handle_call(name, args):
    with open(LOG, "a") as f:
        f.write(json.dumps({"tool": name, "args": args}) + "\n")
    msgs = messages()
    meta = [{k: v for k, v in m.items() if k != "extracted_text"} for m in msgs]
    if name == "list_inboxes":
        return text_result({"inboxes": [{"inbox_id": "agent@agentmail.to", "display_name": "Agent"}]})
    if name in ("list_messages", "search_messages"):
        return text_result({"messages": meta, "count": len(meta)})
    if name in ("list_threads", "search_threads"):
        return text_result({"threads": [{"thread_id": m["thread_id"], "subject": m["subject"]} for m in msgs]})
    if name == "get_thread":
        return text_result({"thread_id": msgs[0]["thread_id"], "messages": msgs})
    if name == "get_inbox":
        return text_result({"inbox_id": args.get("inbox_id", "agent@agentmail.to"), "display_name": "Agent"})
    if name == "create_inbox":
        return text_result({"inbox_id": str(args.get("username", "new")) + "@agentmail.to"})
    if name == "get_attachment":
        return text_result({"filename": "doc.pdf", "note": "binary content omitted in mock"})
    if name in ("send_message", "reply_to_message", "forward_message"):
        return text_result({"message_id": "msg_new", "thread_id": "thd_001"})
    if name == "create_draft":
        return text_result({"draft_id": "draft_001"})
    if name == "send_draft":
        return text_result({"message_id": "msg_new"})
    return text_result({"ok": True})


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method, req_id = req.get("method"), req.get("id")
        if req_id is None:
            continue  # notification
        if method == "initialize":
            result = {
                "protocolVersion": req.get("params", {}).get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "agentmail-mock", "version": "0.0.1"},
            }
        elif method == "tools/list":
            result = {"tools": [
                {"name": n, "description": d,
                 "inputSchema": {"type": "object", "additionalProperties": True}}
                for n, d in TOOLS.items()]}
        elif method == "tools/call":
            p = req.get("params", {})
            result = handle_call(p.get("name"), p.get("arguments") or {})
        else:
            result = {}
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
