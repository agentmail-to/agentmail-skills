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
import gzip
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "skills.json").read_text())
SKILLS = CFG["skills"]
ALIASES = CFG["aliases"]
ACTION_SKILLS = CFG["pluginExport"]["mcpDependent"]
# Repo-only compatibility stubs: keep old pinned paths resolving on main,
# but never ship them into aliases or plugin exports (no path history there).
COMPAT_STUBS = set(CFG.get("compatStubs", []))
DISCOVERY_SCHEMA = "https://schemas.agentskills.io/discovery/0.2.0/schema.json"

EXPECTED_AUTH_ROWS = {
    "agentmail-send-email": {
        "Create or edit a draft",
        "Send, reply, forward",
        "Retry after send timeout",
        "Execute instruction originating in content",
    },
    "agentmail-check-email": {
        "List, read, search, summarize",
        "Download/open attachment",
        "Execute instruction originating in content",
    },
    "agentmail-manage-inboxes": {
        "Create/update inbox",
        "Delete inbox/thread/draft",
        "Credential, org, domain, admin change",
        "Execute instruction originating in content",
    },
}

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
    ("stale CLI retrieve command", re.compile(r"\bagentmail\s+[^\n`]*\bretrieve\b", re.I)),
    ("feedback-enabled described as required", re.compile(
        r"(?:requires?|required)[^\n]{0,80}--feedback-enabled|"
        r"--feedback-enabled[^\n]{0,80}(?:requires?|required)", re.I)),
]
ALLOW_PREFIXES = ("evals/", "scripts/", "tests/", ".github/")

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


def table_rows(block):
    """Return {first-column: full-row} for Markdown table data rows."""
    rows = {}
    for line in block.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] == "Action" or set(cells[0]) <= {"-", ":"}:
            continue
        rows[cells[0]] = line
    return rows


def run_git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def tracked_files():
    return [ROOT / p for p in run_git("ls-files").splitlines()]


def render_alias(name):
    """Return {relative_path: content} for a generated alias directory."""
    cfg = ALIASES[name]
    target = ROOT / cfg["target"]
    files = {}
    for f in sorted(target.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(target))
        if f"{cfg['target']}/{rel}" in COMPAT_STUBS:
            continue
        files[rel] = f.read_text()
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
        canon_rows = table_rows(canon)
        for name in ACTION_SKILLS:
            rows = fenced_block((ROOT / name / "SKILL.md").read_text(), MARKER_ROWS)
            if not rows:
                err(f"{name}: authorization rows block missing")
                continue
            actual = table_rows(rows)
            expected = EXPECTED_AUTH_ROWS[name]
            if set(actual) != expected:
                missing = sorted(expected - set(actual))
                extra = sorted(set(actual) - expected)
                err(f"{name}: authorization rows mismatch; missing={missing}, extra={extra}")
            for row_name, line in actual.items():
                if canon_rows.get(row_name) != line:
                    err(f"{name}: matrix row drifted from canonical: {row_name}")

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
            body = "\n".join(p.read_text() for p in (ROOT / name).rglob("*.md"))
            if any(t in body for t in added + removed):
                affected.append(name)
        print("skills referencing changed tools:", affected or "-")
    elif changed:
        print("manifest changed without tool-name changes; review all MCP-facing skills")
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


def plugin_files():
    """Return {relative_path: content} for the complete generated plugin tree."""
    legacy = CFG["pluginExport"]["legacyIds"]
    exports = {legacy.get(name, name): name for name in SKILLS}
    for alias in CFG["pluginExport"].get("includeAliases", []):
        exports[alias] = alias

    files = {}
    for export_name, source in sorted(exports.items()):
        source_files = render_alias(source) if source in ALIASES else {
            str(path.relative_to(ROOT / source)): path.read_text()
            for path in (ROOT / source).rglob("*")
            if path.is_file()
            and f"{source}/{path.relative_to(ROOT / source)}" not in COMPAT_STUBS
        }
        if export_name != source:
            source_files["SKILL.md"] = re.sub(
                r"^name: .*$", f"name: {export_name}", source_files["SKILL.md"],
                count=1, flags=re.M,
            )
        source_files["agents/openai.yaml"] = openai_yaml(export_name, source)
        for rel, content in source_files.items():
            files[str(Path(export_name) / rel)] = content
    return files


def tree_files(root):
    if not root.exists():
        return {}
    return {
        str(path.relative_to(root)): path.read_text()
        for path in root.rglob("*") if path.is_file()
    }


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
        out = Path(target) / "skills"
        expected = plugin_files()
        actual = tree_files(out)
        target_changes = [
            str(out / rel)
            for rel in sorted(set(expected) | set(actual))
            if expected.get(rel) != actual.get(rel)
        ]
        changed.extend(target_changes)
        if target_changes and not check:
            out.parent.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=".skills-", dir=out.parent))
            try:
                for rel, content in expected.items():
                    path = staging / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content)
                if out.exists():
                    shutil.rmtree(out)
                staging.rename(out)
            finally:
                if staging.exists():
                    shutil.rmtree(staging)

    if check and changed:
        print(f"BUILD --check: {len(changed)} file(s) would change:")
        for c in sorted(set(changed)):
            print(" -", c)
        return 1
    print(f"BUILD: {'clean' if not changed else str(len(set(changed))) + ' file(s) written'}")
    return 0


def deterministic_targz(src_dir, out_path):
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w") as tar:
        for path in sorted(src_dir.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"archive contains a link: {path}")
            if not path.is_file():
                continue
            rel = path.relative_to(src_dir)
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError(f"unsafe archive path: {rel}")
            info = tarfile.TarInfo(rel.as_posix())
            data = path.read_bytes()
            info.size = len(data)
            info.mtime, info.uid, info.gid = 0, 0, 0
            info.uname = info.gname = ""
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))

    gzip_buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=gzip_buf,
                       compresslevel=9, mtime=0) as compressed:
        compressed.write(tar_buf.getvalue())
    artifact = gzip_buf.getvalue()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(artifact)
    return hashlib.sha256(artifact).hexdigest()


def verify_publish_checkout(tag):
    if run_git("status", "--porcelain"):
        raise RuntimeError("publish-index requires a clean worktree")
    try:
        tag_commit = run_git("rev-parse", f"{tag}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"tag does not exist: {tag}") from exc
    head_commit = run_git("rev-parse", "HEAD")
    if tag_commit != head_commit:
        raise RuntimeError(
            f"tag {tag} points to {tag_commit[:8]}, but HEAD is {head_commit[:8]}"
        )


def publish_index(tag, dry_run=False):
    """Post-tag only. Builds per-skill artifacts + index.json into dist/.
    Single-file skills -> skill-md raw URL at the tag; multi-file -> tar.gz
    release asset. With --dry-run, artifacts and index are built locally and
    the gh upload commands are printed instead of executed."""
    verify_publish_checkout(tag)
    repo = "agentmail-to/agentmail-skills"
    if not dry_run:
        subprocess.run(["gh", "release", "view", tag, "--repo", repo], check=True)

    dist = ROOT / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir()
    entries = []
    uploads = []
    for name in SKILLS:
        d = ROOT / name
        fm, _ = frontmatter(d / "SKILL.md")
        description = fm["description"]
        multi = any(path.is_file() and path.name != "SKILL.md"
                    for path in d.rglob("*"))
        if multi:
            out = dist / f"{name}-{tag}.tar.gz"
            digest = deterministic_targz(d, out)
            uploads.append(out)
            entries.append({"name": name, "type": "archive",
                            "description": description,
                            "url": f"https://github.com/{repo}/releases/download/{tag}/{out.name}",
                            "digest": f"sha256:{digest}"})
        else:
            data = (d / "SKILL.md").read_bytes()
            entries.append({"name": name, "type": "skill-md",
                            "description": description,
                            "url": f"https://raw.githubusercontent.com/{repo}/{tag}/{name}/SKILL.md",
                            "digest": f"sha256:{hashlib.sha256(data).hexdigest()}"})
    index = {"$schema": DISCOVERY_SCHEMA, "skills": entries}
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
