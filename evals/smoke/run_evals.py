#!/usr/bin/env python3
"""One-off release validation runner: trigger smoke + adversarial floor.

An eval = prompt -> captured stream-json trace -> deterministic checks -> score.
Each case runs `claude -p` in a throwaway sandbox containing the skills under
test and a mock AgentMail MCP server that logs every tool call. Graders assert
on the trace (Skill activations) and the mock log (tool calls). No real email
is ever sent.

Usage:
  python3 run_evals.py [--only trigger|adversarial] [--skill NAME] [--workers 4]
                       [--skills-root PATH] [--map MAP.json] [--label NAME]

--skills-root points at a directory of skill dirs (default: this repo,
aliases excluded). --map translates canonical fixture names to that root's
skill names ({} value = no equivalent -> case reported N_A, not run).
An empty --skills-root directory gives the no-skill control.
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


def skill_dirs(root, include_all):
    return [d for d in root.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
            and (include_all or d.name not in ALIASES)]


def make_sandbox(root, include_all, scenario_data=None):
    sb = Path(tempfile.mkdtemp(prefix="skill-eval-"))
    skills = sb / ".claude" / "skills"
    skills.mkdir(parents=True)
    for d in skill_dirs(root, include_all):
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
    skill_calls, result_text = [], ""
    for line in trace.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "tool_use" and b.get("name") == "Skill":
                    skill_calls.append(b.get("input", {}).get("skill"))
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
    return {"trace": trace, "skill_calls": skill_calls,
            "mock_log": mock_log, "result_text": result_text}


class Ctx:
    def __init__(self, root, include_all, name_map):
        self.root = root
        self.include_all = include_all
        self.map = name_map
        self.installed = {d.name for d in skill_dirs(root, include_all)}

    def accepted(self, canonical_names):
        out = []
        for n in canonical_names:
            out.extend(self.map.get(n, [n]))
        return [a for a in out if a in self.installed]


def trigger_case(ctx, skill, prompt, expect_positive):
    canonical = [skill]
    if isinstance(prompt, dict):
        canonical = prompt.get("accept", canonical)
        prompt = prompt["prompt"]
    accepted = ctx.accepted(canonical)
    if not accepted:
        return {"kind": "trigger", "skill": skill, "prompt": prompt,
                "polarity": "positive" if expect_positive else "negative",
                "na": True, "pass": None,
                "note": "no equivalent skill in this root"}
    sb = make_sandbox(ctx.root, ctx.include_all)
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


def adversarial_case(ctx, sc):
    sb = make_sandbox(ctx.root, ctx.include_all, scenario_data=sc["messages"])
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
    ap.add_argument("--skills-root", type=Path, default=REPO)
    ap.add_argument("--map", type=Path)
    ap.add_argument("--label", default="canonical")
    args = ap.parse_args()

    name_map = json.loads(args.map.read_text()) if args.map else {}
    include_all = args.skills_root.resolve() != REPO.resolve()
    ctx = Ctx(args.skills_root, include_all, name_map)

    jobs = []
    if args.only in (None, "trigger"):
        triggers = json.loads((HERE / "fixtures" / "triggers.json").read_text())
        for skill, cases in triggers.items():
            if args.skill and skill != args.skill:
                continue
            for p in cases["positive"]:
                jobs.append(lambda s=skill, p=p: trigger_case(ctx, s, p, True))
            for p in cases["negative"]:
                jobs.append(lambda s=skill, p=p: trigger_case(ctx, s, p, False))
    if args.only in (None, "adversarial") and not args.skill:
        adv = json.loads((HERE / "fixtures" / "adversarial.json").read_text())
        for sc in adv["scenarios"]:
            jobs.append(lambda sc=sc: adversarial_case(ctx, sc))

    print(f"[{args.label}] running {len(jobs)} cases, root={args.skills_root}, "
          f"installed={sorted(ctx.installed)}", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, res in enumerate(ex.map(lambda f: f(), jobs), 1):
            results.append(res)
            tag = res.get("skill") or res.get("name")
            status = "N_A " if res.get("na") else ("PASS" if res["pass"] else "FAIL")
            print(f"[{i}/{len(jobs)}] {status} {res['kind']}:{tag}:{res.get('polarity', '')}",
                  flush=True)

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{args.label}.json").write_text(json.dumps(results, indent=2))
    trig = [r for r in results if r["kind"] == "trigger" and not r.get("na")]
    na = [r for r in results if r.get("na")]
    adv = [r for r in results if r["kind"] == "adversarial"]
    if trig:
        pos = [r for r in trig if r["polarity"] == "positive"]
        neg = [r for r in trig if r["polarity"] == "negative"]
        ni = [r for r in pos if r.get("never_invoked")]
        print(f"\n[{args.label}] TRIGGER: positives {sum(r['pass'] for r in pos)}/{len(pos)} "
              f"| negatives {sum(r['pass'] for r in neg)}/{len(neg)} "
              f"| never-invoked {len(ni)}/{len(pos)} | N/A {len(na)}")
    if adv:
        print(f"[{args.label}] ADVERSARIAL: {sum(r['pass'] for r in adv)}/{len(adv)}")
    for r in results:
        if r.get("pass") is False:
            print("FAIL detail:", json.dumps(
                {k: r[k] for k in r if k != "trace"}, default=str)[:400])
    print(f"\nfull results: {RESULTS / (args.label + '.json')}")


if __name__ == "__main__":
    main()
