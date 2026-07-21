#!/usr/bin/env python3
"""One-off release validation runner: trigger smoke + adversarial floor.

An eval = prompt -> captured stream-json trace -> deterministic checks -> score.
Each case runs `claude -p` in a throwaway sandbox containing the candidate
skills and (for tool-using cases) a mock AgentMail MCP server that logs every
tool call. Graders assert on the trace (Skill activations) and the mock log
(tool calls). No real email is ever sent.

Usage:
  python3 run_evals.py [--only trigger|adversarial] [--skill NAME] [--workers 4]
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MOCK = HERE / "mock_mcp_server.py"
RESULTS = HERE / "results"
MODEL = "claude-sonnet-5"
ALIASES = {"agentmail-sdk", "email-for-ai-agents"}
CASE_TIMEOUT = 420


def skill_dirs():
    return [d for d in REPO.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists() and d.name not in ALIASES]


def make_sandbox(scenario_data=None):
    sb = Path(tempfile.mkdtemp(prefix="skill-eval-"))
    skills = sb / ".claude" / "skills"
    skills.mkdir(parents=True)
    for d in skill_dirs():
        shutil.copytree(d, skills / d.name)
    env = {"MOCK_LOG": str(sb / "mock.log")}
    if scenario_data is not None:
        data_path = sb / "scenario.json"
        data_path.write_text(json.dumps({"messages": scenario_data}))
        env["MOCK_DATA"] = str(data_path)
    (sb / ".mcp.json").write_text(json.dumps({
        "mcpServers": {"agentmail": {
            "command": "python3", "args": [str(MOCK)], "env": env}}}))
    return sb


def run_case(prompt, sandbox, max_turns):
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--max-turns", str(max_turns), "--model", MODEL,
           "--dangerously-skip-permissions"]
    try:
        proc = subprocess.run(cmd, cwd=sandbox, capture_output=True, text=True,
                              timeout=CASE_TIMEOUT, stdin=subprocess.DEVNULL)
        trace = proc.stdout
    except subprocess.TimeoutExpired as e:
        trace = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        trace += '\n{"type":"eval_error","error":"timeout"}'
    skill_calls, tool_calls, result_text = [], [], ""
    for line in trace.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "tool_use":
                    if b.get("name") == "Skill":
                        skill_calls.append(b.get("input", {}).get("skill"))
                    tool_calls.append(b.get("name"))
        elif ev.get("type") == "result":
            result_text = ev.get("result") or ""
    mock_log = []
    log_path = sandbox / "mock.log"
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            try:
                mock_log.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return {"trace": trace, "skill_calls": skill_calls, "tool_calls": tool_calls,
            "mock_log": mock_log, "result_text": result_text}


def trigger_case(skill, prompt, expect_positive):
    accepted = [skill]
    if isinstance(prompt, dict):
        accepted = prompt.get("accept", accepted)
        prompt = prompt["prompt"]
    sb = make_sandbox()
    try:
        out = run_case(prompt, sb, max_turns=4)
        activated = any(a in out["skill_calls"] for a in accepted)
        ok = activated if expect_positive else not activated
        return {"kind": "trigger", "skill": skill,
                "polarity": "positive" if expect_positive else "negative",
                "prompt": prompt, "pass": ok, "activated": out["skill_calls"],
                "never_invoked": expect_positive and not out["skill_calls"],
                "tools_called": [c["tool"] for c in out["mock_log"]]}
    finally:
        shutil.rmtree(sb, ignore_errors=True)


def adversarial_case(sc):
    sb = make_sandbox(scenario_data=sc["messages"])
    try:
        out = run_case(sc["prompt"], sb, max_turns=15)
        violations = []
        for f in sc.get("forbidden", []):
            for call in out["mock_log"]:
                if call["tool"] == f["tool"]:
                    if "arg_contains" not in f or f["arg_contains"] in json.dumps(call["args"]):
                        violations.append({"tool": call["tool"], "args": call["args"]})
        rx = sc.get("trace_regex_forbidden")
        if rx and re.search(rx, out["trace"]):
            violations.append({"trace_regex": rx})
        return {"kind": "adversarial", "name": sc["name"],
                "matrix_row": sc.get("matrix_row"), "pass": not violations,
                "violations": violations, "activated": out["skill_calls"],
                "tools_called": [c["tool"] for c in out["mock_log"]],
                "result_snippet": out["result_text"][:300]}
    finally:
        shutil.rmtree(sb, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["trigger", "adversarial"])
    ap.add_argument("--skill")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    jobs = []
    if args.only in (None, "trigger"):
        triggers = json.loads((HERE / "fixtures" / "triggers.json").read_text())
        for skill, cases in triggers.items():
            if args.skill and skill != args.skill:
                continue
            for p in cases["positive"]:
                jobs.append(lambda s=skill, p=p: trigger_case(s, p, True))
            for p in cases["negative"]:
                jobs.append(lambda s=skill, p=p: trigger_case(s, p, False))
    if args.only in (None, "adversarial") and not args.skill:
        adv = json.loads((HERE / "fixtures" / "adversarial.json").read_text())
        for sc in adv["scenarios"]:
            jobs.append(lambda sc=sc: adversarial_case(sc))

    print(f"running {len(jobs)} cases, {args.workers} workers, model={MODEL}", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, res in enumerate(ex.map(lambda f: f(), jobs), 1):
            results.append(res)
            tag = res.get("skill") or res.get("name")
            print(f"[{i}/{len(jobs)}] {'PASS' if res['pass'] else 'FAIL'} "
                  f"{res['kind']}:{tag}:{res.get('polarity', '')}", flush=True)

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "results.json").write_text(json.dumps(results, indent=2))
    trig = [r for r in results if r["kind"] == "trigger"]
    adv = [r for r in results if r["kind"] == "adversarial"]
    if trig:
        pos = [r for r in trig if r["polarity"] == "positive"]
        neg = [r for r in trig if r["polarity"] == "negative"]
        ni = [r for r in pos if r.get("never_invoked")]
        print(f"\nTRIGGER: positives {sum(r['pass'] for r in pos)}/{len(pos)} "
              f"| negatives {sum(r['pass'] for r in neg)}/{len(neg)} "
              f"| never-invoked rate {len(ni)}/{len(pos)}")
    if adv:
        print(f"ADVERSARIAL: {sum(r['pass'] for r in adv)}/{len(adv)}")
    for r in results:
        if not r["pass"]:
            print("FAIL detail:", json.dumps(
                {k: r[k] for k in r if k != "trace"}, default=str)[:400])
    print(f"\nfull results: {RESULTS / 'results.json'}")


if __name__ == "__main__":
    main()
