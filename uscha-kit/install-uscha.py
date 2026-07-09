#!/usr/bin/env python3
"""Universal Uscha machine installer.

One small public interface, two adapters inside:
- Codex: personal local plugin at ~/plugins/uscha + ~/.agents/plugins/marketplace.json
- Claude: global skills/hook at ~/.claude/skills and ~/.claude/hooks

Stdlib only. Safe to test with --home and --dry-run.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent
PLUGIN_NAME = "uscha"
SKILLS = [
    "uscha-discovery",
    "uscha-adr-refine",
    "uscha-reverse-discovery",
    "uscha-characterize",
    "uscha-devloop",
    "uscha-sysdoc",
    "uscha-rubric",
    "uscha-mirador",
]
TARGETS = ("codex", "claude")


def source_version() -> str:
    raw = (KIT_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    return raw.split()[-1]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def home_path(args) -> Path:
    return Path(args.home).expanduser().resolve() if args.home else Path.home().resolve()


def selected_targets(value: str) -> list[str]:
    return list(TARGETS) if value == "both" else [value]


class Plan:
    def __init__(self, dry_run: bool):
        self.dry_run = dry_run
        self.operations: list[dict] = []

    def add(self, action: str, path: Path, source: Path | None = None, note: str | None = None):
        row = {"action": action, "path": str(path)}
        if source is not None:
            row["source"] = str(source)
        if note:
            row["note"] = note
        self.operations.append(row)

    def ensure_dir(self, path: Path):
        self.add("mkdir", path)
        if not self.dry_run:
            path.mkdir(parents=True, exist_ok=True)

    def write_json(self, path: Path, data: dict):
        self.add("write-json", path)
        if not self.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def copy_file(self, src: Path, dst: Path):
        self.add("copy-file", dst, src)
        if not self.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    def copy_dir(self, src: Path, dst: Path, mode: str):
        self.add("copy-dir" if mode == "copy" else "link-dir", dst, src)
        if self.dry_run:
            return
        if dst.exists() or dst.is_symlink():
            if dst.is_symlink() or dst.is_file():
                dst.unlink()
            else:
                shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if mode == "copy":
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        else:
            link_dir(src, dst)


def link_dir(src: Path, dst: Path):
    """Create a directory link. On Windows prefer junctions for non-admin installs."""
    if os.name == "nt":
        cmd = ["cmd", "/c", "mklink", "/J", str(dst), str(src)]
        res = subprocess.run(cmd, text=True, capture_output=True)
        if res.returncode != 0:
            raise SystemExit("[install-uscha] cannot create junction %s -> %s: %s" %
                             (dst, src, (res.stderr or res.stdout).strip()))
    else:
        os.symlink(src, dst, target_is_directory=True)


def plugin_manifest() -> dict:
    return {
        "name": PLUGIN_NAME,
        "version": source_version(),
        "description": "Uscha spec-driven development methodology for coding agents.",
        "author": {"name": "Andres Massello", "url": "https://github.com/andresmassello"},
        "homepage": "https://github.com/andresmassello/uscha",
        "repository": "https://github.com/andresmassello/uscha",
        "license": "MIT",
        "keywords": ["spec-driven", "qa", "gates", "golden-testing", "readiness"],
        "skills": "./skills/",
        "interface": {
            "displayName": "Uscha",
            "shortDescription": "Spec-driven development with fact gates and readiness.",
            "longDescription": "Uscha installs discovery, ADR, characterization, devloop, rubric, sysdoc and Mirador skills plus the qa_ledger.py evidence engine.",
            "developerName": "Andres Massello",
            "category": "Productivity",
            "capabilities": ["Write", "Interactive"],
            "defaultPrompt": [
                "Run Uscha discovery for this feature.",
                "Use Uscha devloop to verify this change.",
                "Show the Uscha readiness for this repo."
            ],
            "brandColor": "#7C3AED"
        }
    }


def marker(target: str, install_root: Path, mode: str) -> dict:
    return {
        "name": PLUGIN_NAME,
        "target": target,
        "version": source_version(),
        "mode": mode,
        "installed_at": now_iso(),
        "source": str(KIT_ROOT),
        "install_root": str(install_root),
    }


def install_codex(plan: Plan, home: Path, mode: str):
    plugin_root = home / "plugins" / PLUGIN_NAME
    plan.ensure_dir(plugin_root / ".codex-plugin")
    plan.write_json(plugin_root / ".codex-plugin" / "plugin.json", plugin_manifest())
    skills_dst = plugin_root / "skills"
    plan.ensure_dir(skills_dst)
    for skill in SKILLS:
        plan.copy_dir(KIT_ROOT / ".claude" / "skills" / skill, skills_dst / skill, mode)
    plan.copy_file(KIT_ROOT / "VERSION", plugin_root / "VERSION")
    plan.copy_file(KIT_ROOT / "uscha.config.json", plugin_root / "uscha.config.json")
    plan.write_json(plugin_root / "uscha-install.json", marker("codex", plugin_root, mode))
    write_marketplace(plan, home, plugin_root)
    return plugin_root


def write_marketplace(plan: Plan, home: Path, plugin_root: Path):
    market = home / ".agents" / "plugins" / "marketplace.json"
    data = {"name": "personal", "interface": {"displayName": "Personal"}, "plugins": []}
    if market.exists() and not plan.dry_run:
        try:
            data = json.loads(market.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raise SystemExit("[install-uscha] marketplace.json is invalid: %s" % market)
    plugins = [p for p in data.get("plugins", []) if p.get("name") != PLUGIN_NAME]
    plugins.append({
        "name": PLUGIN_NAME,
        "source": {"source": "local", "path": "./plugins/uscha"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Productivity",
    })
    data["plugins"] = plugins
    data.setdefault("name", "personal")
    data.setdefault("interface", {"displayName": "Personal"})
    plan.write_json(market, data)


def install_claude(plan: Plan, home: Path, mode: str):
    skills_root = home / ".claude" / "skills"
    plan.ensure_dir(skills_root)
    for skill in SKILLS:
        plan.copy_dir(KIT_ROOT / ".claude" / "skills" / skill, skills_root / skill, mode)
    hooks_root = home / ".claude" / "hooks"
    plan.ensure_dir(hooks_root)
    plan.copy_file(KIT_ROOT / "hooks" / "block-approved-writes.ps1",
                   hooks_root / "block-approved-writes.ps1")
    plan.write_json(home / ".claude" / "uscha-install.json", marker("claude", home / ".claude", mode))
    return home / ".claude"


def target_status(home: Path, target: str) -> dict:
    if target == "codex":
        root = home / "plugins" / PLUGIN_NAME
        manifest = root / ".codex-plugin" / "plugin.json"
        engine = root / "skills" / "uscha-devloop" / "qa_ledger.py"
        market = home / ".agents" / "plugins" / "marketplace.json"
        marker_path = root / "uscha-install.json"
    else:
        root = home / ".claude"
        manifest = root / "uscha-install.json"
        engine = root / "skills" / "uscha-devloop" / "qa_ledger.py"
        market = root / "hooks" / "block-approved-writes.ps1"
        marker_path = root / "uscha-install.json"
    installed = engine.exists() and manifest.exists()
    installed_version = None
    if marker_path.exists():
        try:
            installed_version = json.loads(marker_path.read_text(encoding="utf-8")).get("version")
        except json.JSONDecodeError:
            installed_version = None
    return {
        "installed": installed,
        "install_root": str(root),
        "engine": str(engine),
        "marketplace_or_hook": str(market),
        "installed_version": installed_version,
        "source_version": source_version(),
        "version_match": installed_version == source_version(),
    }


def cmd_version(args):
    out = {"name": PLUGIN_NAME, "source_version": source_version(), "targets": list(TARGETS)}
    emit(out, args.json)


def cmd_install(args):
    home = home_path(args)
    plan = Plan(args.dry_run)
    installed = {}
    for target in selected_targets(args.target):
        if target == "codex":
            installed[target] = str(install_codex(plan, home, args.mode))
        else:
            installed[target] = str(install_claude(plan, home, args.mode))
    out = {"status": "planned" if args.dry_run else "installed", "dry_run": args.dry_run,
           "source_version": source_version(), "home": str(home), "installed": installed,
           "operations": plan.operations,
           "next": next_steps(args.target)}
    emit(out, args.json)


def cmd_doctor(args):
    home = home_path(args)
    targets = {t: target_status(home, t) for t in selected_targets(args.target)}
    ok = all(v["installed"] and v["version_match"] for v in targets.values())
    out = {"ok": ok, "source_version": source_version(), "home": str(home),
           "python": sys.version.split()[0], "targets": targets}
    emit(out, args.json)
    if not ok and not args.json:
        sys.exit(1)


def cmd_init(args):
    repo = Path(args.repo).expanduser().resolve()
    plan = Plan(args.dry_run)
    plan.copy_file(KIT_ROOT / "uscha.config.json", repo / "uscha.config.json")
    for name in ("CLAUDE.md", "CONSTITUTION.md", ".gitattributes"):
        src = KIT_ROOT / "templates" / name
        if src.exists():
            plan.copy_file(src, repo / name)
    out = {"status": "planned" if args.dry_run else "initialized", "dry_run": args.dry_run,
           "repo": str(repo), "operations": plan.operations}
    emit(out, args.json)


def next_steps(target: str) -> list[str]:
    steps = []
    if target in ("codex", "both"):
        steps.append("Codex: restart or open a new thread, then install/use uscha from the Personal marketplace if needed.")
    if target in ("claude", "both"):
        steps.append("Claude: restart Claude Code so global skills/hooks are reloaded.")
    steps.append("Run: python install-uscha.py doctor --target %s" % target)
    return steps


def emit(data: dict, as_json: bool):
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    if "targets" in data and isinstance(data["targets"], dict):
        print("Uscha %s" % data.get("source_version"))
        for name, st in data["targets"].items():
            mark = "OK" if st["installed"] and st["version_match"] else "WARN"
            print("  %s: %s installed=%s version=%s" %
                  (mark, name, st["installed"], st.get("installed_version")))
    elif "operations" in data:
        print("Uscha %s: %s (%s operations)" %
              (data.get("source_version", source_version()), data["status"], len(data["operations"])))
        for op in data["operations"][:20]:
            print("  - {action}: {path}".format(**op))
        if len(data["operations"]) > 20:
            print("  ... %d more" % (len(data["operations"]) - 20))
    else:
        print("Uscha %s" % data.get("source_version", source_version()))


def build_parser():
    p = argparse.ArgumentParser(description="Install/update Uscha for Codex and Claude machines")
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("version", help="show source version and supported targets")
    pv.add_argument("--json", action="store_true")
    pv.set_defaults(func=cmd_version)

    pi = sub.add_parser("install", help="install Uscha globally for a machine")
    pi.add_argument("--target", choices=["codex", "claude", "both"], default="both")
    pi.add_argument("--mode", choices=["copy", "link"], default="copy")
    pi.add_argument("--home", default=None, help="override home dir; useful for tests")
    pi.add_argument("--dry-run", action="store_true")
    pi.add_argument("--json", action="store_true")
    pi.set_defaults(func=cmd_install)

    pd = sub.add_parser("doctor", help="check installed Uscha and version drift")
    pd.add_argument("--target", choices=["codex", "claude", "both"], default="both")
    pd.add_argument("--home", default=None)
    pd.add_argument("--json", action="store_true")
    pd.set_defaults(func=cmd_doctor)

    pn = sub.add_parser("init", help="prepare a repo with Uscha config/templates")
    pn.add_argument("--repo", default=".")
    pn.add_argument("--dry-run", action="store_true")
    pn.add_argument("--json", action="store_true")
    pn.set_defaults(func=cmd_init)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
