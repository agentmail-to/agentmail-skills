#!/usr/bin/env python3
"""AgentMail skills repository tooling.

  validate       structure, links, denylist, matrix drift, tool refs, aliases
  sync           refresh backend-contract.json from an agentmail-mcp checkout
  build          regenerate aliases + skills.sh.json (+ plugin export via --target)
  publish-index  post-tag: archives + .well-known index (see --help)

Merging to main publishes to installers immediately; validate and
`build --check` are the merge gates.
"""
import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "skills.json").read_text())
SKILLS = CFG["skills"]
ALIASES = CFG["aliases"]
ACTION_SKILLS = CFG["pluginExport"]["mcpDependent"]

# Denylist: known-defective patterns. A defect fixed in one file is not fixed
# in the repository — this gates on zero hits everywhere. evals/ and scripts/
# legitimately contain attack fixtures / these very patterns.
DENYLIST = [
    ("fake webhook header", re.compile(r"X-AgentMail-Sig" + r"nature")),
    ("hand-rolled webhook HMAC", re.compile(r"hmac\.n" + r"ew\(|createH" + r"mac\(")),
    ("credential in URL", re.compile(r"\?api[_]?[Kk]ey=|\?tok" + r"en=")),
    ("memory as credential store", re.compile(r"persistent mem" + r"ory", re.I)),
    ("underscore WS discriminator", re.compile(r"['\"]message_rec" + r"eived['\"]")),
    ("unverified Go SDK claim", re.compile(r"Go S" + r"DK")),
]
ALLOW_PREFIXES = ("evals/", "scripts/", ".github/")

# Backticked snake_case tokens in MCP-facing skills that are fields/params,
# not tool names.
FIELD_ALLOW = {
    "extracted_text", "extracted_html", "message_id", "thread_id", "inbox_id",
    "draft_id", "client_id", "add_labels", "remove_labels", "next_page_token",
    "pod_id", "api_key", "human_email", "otp_code", "organization_id",
    "streamable_http", "allow_implicit_invocation", "page_token",
    "request_options", "max_retries", "get_raw", "send_at", "in_reply_to",
    "auth_type", "feedback_enabled", "display_name", "event_types",
}

MARKER_FULL = "<!-- authorization-matrix:full -->"
MARKER_ROWS = "<!-- authorization-matrix:rows -->"


def frontmatter(path):
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, text[m.end():]


def fenced_block(text, marker):
    idx = text.find(marker)
    if idx == -1:
        return None
    m = re.search(r"```markdown\n(.*?)```", text[idx:], re.S)
    return m.group(1) if m else None


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    return [ROOT / p for p in out.stdout.splitlines()]


def render_alias(name):
    """Return {relative_path: content} for a generated alias directory."""
    cfg = ALIASES[name]
    target = ROOT / cfg["target"]
    files = {}
    for f in sorted(target.rglob("*")):
        if f.is_file():
            files[str(f.relative_to(target))] = f.read_text()
    skill = files["SKILL.md"]
    skill = re.sub(r"^name: .*$", f"name: {name}", skill, count=1, flags=re.M)
    skill = re.sub(r"^description: .*$", f"description: {cfg['description']}",
                   skill, count=1, flags=re.M)
    files["SKILL.md"] = skill
    for rel, content in cfg.get("stubs", {}).items():
        files[rel] = content
    return files


def validate():
    errors = []

    def err(msg):
        errors.append(msg)

    contract_path = ROOT / "backend-contract.json"
    tools = set()
    if contract_path.exists():
        tools = set(json.loads(contract_path.read_text())["tools"])
    else:
        err("backend-contract.json missing — run: skills.py sync --backend <checkout>")

    for name in SKILLS + list(ALIASES):
        d = ROOT / name
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            err(f"{name}: SKILL.md missing")
            continue
        fm, body = frontmatter(skill_md)
        if fm is None:
            err(f"{name}: no frontmatter")
            continue
        if set(fm) != {"name", "description"}:
            err(f"{name}: frontmatter keys must be exactly name+description, got {sorted(fm)}")
        if fm.get("name") != name:
            err(f"{name}: frontmatter name '{fm.get('name')}' != directory")
        if not 40 <= len(fm.get("description", "")) <= 1024:
            err(f"{name}: description length {len(fm.get('description', ''))} outside 40..1024")
        lines = skill_md.read_text().count("\n") + 1
        if lines > 500:
            err(f"{name}: SKILL.md {lines} lines exceeds the 500-line ceiling")
        for md in d.rglob("*.md"):
            for link in re.findall(r"\]\(([^)#\s]+)\)", md.read_text()):
                if link.startswith(("http://", "https://", "mailto:")):
                    continue
                if not (md.parent / link).exists():
                    err(f"{md.relative_to(ROOT)}: broken link -> {link}")

    for f in tracked_files():
        rel = str(f.relative_to(ROOT))
        if rel.startswith(ALLOW_PREFIXES) or not f.exists() or f.suffix not in (".md", ".json", ".yaml", ".yml", ".txt"):
            continue
        text = f.read_text(errors="ignore")
        for label, rx in DENYLIST:
            for m in rx.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                err(f"{rel}:{line}: denylist hit ({label})")

    canon_text = (ROOT / "agent-email-patterns/references/threat-model.md").read_text()
    canon = fenced_block(canon_text, MARKER_FULL)
    if not canon:
        err("threat-model.md: canonical authorization matrix block missing")
    else:
        canon_lines = {l for l in canon.splitlines() if l.strip()}
        for name in ACTION_SKILLS:
            rows = fenced_block((ROOT / name / "SKILL.md").read_text(), MARKER_ROWS)
            if not rows:
                err(f"{name}: authorization rows block missing")
                continue
            for l in rows.splitlines():
                if l.strip() and l not in canon_lines:
                    err(f"{name}: matrix row drifted from canonical: {l[:80]}")

    if tools:
        for name in ACTION_SKILLS + ["agentmail-mcp"]:
            body = (ROOT / name / "SKILL.md").read_text()
            for tok in set(re.findall(r"`([a-z][a-z0-9]*_[a-z0-9_]+)`", body)):
                if tok not in tools and tok not in FIELD_ALLOW:
                    err(f"{name}: references unknown MCP tool/field `{tok}`")

    for name in ALIASES:
        expected = render_alias(name)
        actual_dir = ROOT / name
        actual = {str(f.relative_to(actual_dir)): f.read_text()
                  for f in actual_dir.rglob("*") if f.is_file()}
        for rel in sorted(set(expected) | set(actual)):
            if rel not in actual:
                err(f"{name}/{rel}: missing (build would create it)")
            elif rel not in expected:
                err(f"{name}/{rel}: unexpected file (not produced by build)")
            elif expected[rel] != actual[rel]:
                err(f"{name}/{rel}: differs from generated content — run: skills.py build")

    if errors:
        print(f"VALIDATE: {len(errors)} error(s)")
        for e in errors:
            print(" -", e)
        return 1
    print(f"VALIDATE: ok ({len(SKILLS)} skills, {len(ALIASES)} aliases)")
    return 0


def sync(backend, check=False):
    backend = Path(backend)
    manifest_path = backend / CFG["backend"]["manifestPath"]
    manifest = json.loads(manifest_path.read_text())
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=backend,
                            capture_output=True, text=True).stdout.strip()
    contract = {
        "sourceRepo": CFG["backend"]["repo"],
        "sourceCommit": commit,
        "manifestSha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "tools": sorted(t["name"] for t in manifest["tools"]),
    }
    path = ROOT / "backend-contract.json"
    old = json.loads(path.read_text()) if path.exists() else {"tools": []}
    added = sorted(set(contract["tools"]) - set(old["tools"]))
    removed = sorted(set(old["tools"]) - set(contract["tools"]))
    changed = added or removed or old.get("manifestSha256") != contract["manifestSha256"]
    if added or removed:
        print("added tools:", added or "-")
        print("removed tools:", removed or "-")
        affected = []
        for name in SKILLS:
            body = (ROOT / name / "SKILL.md").read_text()
            if any(t in body for t in added + removed):
                affected.append(name)
        print("skills referencing changed tools:", affected or "-")
    if check:
        if changed:
            print("SYNC --check: contract drift detected — a skills update PR is needed")
            return 1
        print("SYNC --check: contract matches")
        return 0
    path.write_text(json.dumps(contract, indent=2) + "\n")
    print(f"SYNC: wrote backend-contract.json ({len(contract['tools'])} tools @ {commit[:8]})")
    return 0


def openai_yaml(export_name, canonical_name):
    disp = CFG["pluginExport"]["display"][canonical_name]
    lines = ["interface:",
             f'  display_name: "{disp["name"]}"',
             f'  short_description: "{disp["short"]}"',
             f'  default_prompt: "{disp["prompt"]}"']
    if canonical_name in ACTION_SKILLS:
        lines += ["dependencies:", "  tools:", '    - type: "mcp"',
                  '      value: "agentmail"',
                  '      description: "AgentMail hosted MCP server"',
                  '      transport: "streamable_http"',
                  '      url: "https://mcp.agentmail.to/mcp"']
    implicit = "false" if canonical_name in ALIASES else "true"
    lines += ["policy:", f"  allow_implicit_invocation: {implicit}"]
    return "\n".join(lines) + "\n"


def build(check=False, target=None):
    changed = []

    def emit(path, content):
        if path.exists() and path.read_text() == content:
            return
        changed.append(str(path.relative_to(ROOT)) if ROOT in path.parents or path == ROOT else str(path))
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    for name in ALIASES:
        expected = render_alias(name)
        adir = ROOT / name
        for rel, content in expected.items():
            emit(adir / rel, content)
        if adir.exists():
            for f in adir.rglob("*"):
                if f.is_file() and str(f.relative_to(adir)) not in expected:
                    changed.append(str(f.relative_to(ROOT)))
                    if not check:
                        f.unlink()

    emit(ROOT / "skills.sh.json",
         json.dumps({"name": "agentmail", "skills": SKILLS}, indent=2) + "\n")

    if target:
        legacy = CFG["pluginExport"]["legacyIds"]
        out = Path(target) / "skills"
        exports = {legacy.get(n, n): n for n in SKILLS}
        for a in CFG["pluginExport"].get("includeAliases", []):
            exports[a] = a
        for export_name, source in sorted(exports.items()):
            src_files = render_alias(source) if source in ALIASES else {
                str(f.relative_to(ROOT / source)): f.read_text()
                for f in (ROOT / source).rglob("*") if f.is_file()}
            if export_name != source:
                skill = src_files["SKILL.md"]
                skill = re.sub(r"^name: .*$", f"name: {export_name}", skill,
                               count=1, flags=re.M)
                src_files["SKILL.md"] = skill
            src_files["agents/openai.yaml"] = openai_yaml(export_name, source)
            for rel, content in src_files.items():
                emit(out / export_name / rel, content)

    if check and changed:
        print(f"BUILD --check: {len(changed)} file(s) would change:")
        for c in sorted(set(changed)):
            print(" -", c)
        return 1
    print(f"BUILD: {'clean' if not changed else str(len(set(changed))) + ' file(s) written'}")
    return 0


def deterministic_targz(src_dir, out_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", compresslevel=9) as tar:
        for f in sorted(src_dir.rglob("*")):
            if not f.is_file():
                continue
            info = tarfile.TarInfo(str(f.relative_to(src_dir.parent)))
            data = f.read_bytes()
            info.size = len(data)
            info.mtime, info.uid, info.gid = 0, 0, 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(buf.getvalue())
    return hashlib.sha256(buf.getvalue()).hexdigest()


def publish_index(tag, dry_run=False):
    """Post-tag only. Builds per-skill artifacts + index.json into dist/.
    Single-file skills -> skill-md raw URL at the tag; multi-file -> tar.gz
    release asset. With --dry-run, artifacts and index are built locally and
    the gh upload commands are printed instead of executed."""
    repo = "agentmail-to/agentmail-skills"
    dist = ROOT / "dist"
    entries = []
    uploads = []
    for name in SKILLS:
        d = ROOT / name
        multi = any(p.is_dir() for p in d.iterdir())
        if multi:
            out = dist / f"{name}-{tag}.tar.gz"
            digest = deterministic_targz(d, out)
            uploads.append(out)
            entries.append({"name": name, "type": "archive",
                            "url": f"https://github.com/{repo}/releases/download/{tag}/{out.name}",
                            "sha256": digest})
        else:
            data = (d / "SKILL.md").read_bytes()
            entries.append({"name": name, "type": "skill-md",
                            "url": f"https://raw.githubusercontent.com/{repo}/{tag}/{name}/SKILL.md",
                            "sha256": hashlib.sha256(data).hexdigest()})
    index = {"version": tag, "skills": entries}
    dist.mkdir(exist_ok=True)
    (dist / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    print(f"PUBLISH-INDEX: dist/index.json ({len(entries)} entries)")
    cmds = [["gh", "release", "upload", tag, str(u), "--repo", repo] for u in uploads]
    for cmd in cmds:
        if dry_run:
            print("would run:", " ".join(cmd))
        else:
            subprocess.run(cmd, check=True)
    print("Assets first, index last: deploy dist/index.json to the "
          ".well-known route in agentmail-web AFTER assets are uploaded, "
          "then fetch the live index + one artifact and verify digests.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    p = sub.add_parser("sync")
    p.add_argument("--backend", required=True)
    p.add_argument("--check", action="store_true")
    p = sub.add_parser("build")
    p.add_argument("--check", action="store_true")
    p.add_argument("--target")
    p = sub.add_parser("publish-index")
    p.add_argument("--tag", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.cmd == "validate":
        sys.exit(validate())
    if args.cmd == "sync":
        sys.exit(sync(args.backend, args.check))
    if args.cmd == "build":
        sys.exit(build(args.check, args.target))
    if args.cmd == "publish-index":
        sys.exit(publish_index(args.tag, args.dry_run))


if __name__ == "__main__":
    main()
