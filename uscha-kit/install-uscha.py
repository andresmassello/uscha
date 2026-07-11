#!/usr/bin/env python3
"""Universal Uscha machine installer (stdlib only, safe with --home/--dry-run)."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent
PLUGIN_NAME = "uscha"
SKILLS = ["uscha-discovery", "uscha-adr-refine", "uscha-reverse-discovery", "uscha-characterize",
          "uscha-devloop", "uscha-sysdoc", "uscha-rubric", "uscha-mirador"]
TARGETS = ("codex", "claude")
HOOK_NAME = "block-approved-writes.py"


class InstallError(Exception):
    pass


def source_version():
    return (KIT_ROOT / "VERSION").read_text(encoding="utf-8").strip().split()[-1]


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def home_path(args):
    return Path(args.home).expanduser().resolve() if args.home else Path.home().resolve()


def selected_targets(value):
    return list(TARGETS) if value == "both" else [value]


def load_json(path, label):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError("[install-uscha] invalid %s: %s" % (label, path)) from exc


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".%s." % path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def atomic_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".%s." % path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def remove_path(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def link_dir(src, dst):
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], text=True, capture_output=True)
        if result.returncode:
            raise InstallError("[install-uscha] cannot create junction %s -> %s" % (dst, src))
    else:
        os.symlink(src, dst, target_is_directory=True)


def copy_skill(src, dst, mode):
    if mode == "copy":
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    else:
        link_dir(src, dst)


def source_skills():
    root = KIT_ROOT / ".claude" / "skills"
    missing = [skill for skill in SKILLS if not (root / skill / "SKILL.md").is_file()]
    if missing:
        raise InstallError("[install-uscha] source skills missing: %s" % ", ".join(missing))
    if not (KIT_ROOT / "hooks" / HOOK_NAME).is_file():
        raise InstallError("[install-uscha] source hook missing: %s" % HOOK_NAME)
    return root


def plugin_manifest():
    return {"name": PLUGIN_NAME, "version": source_version(),
            "description": "Uscha spec-driven development methodology for coding agents.",
            "author": {"name": "Andres Massello", "url": "https://github.com/andresmassello"},
            "homepage": "https://github.com/andresmassello/uscha", "repository": "https://github.com/andresmassello/uscha",
            "license": "MIT", "keywords": ["spec-driven", "qa", "gates", "golden-testing", "readiness"],
            "skills": "./skills/", "interface": {"displayName": "Uscha", "shortDescription": "Spec-driven development with fact gates and readiness.",
            "longDescription": "Uscha installs discovery, ADR, characterization, devloop, rubric, sysdoc and Mirador skills plus qa_ledger.py.",
            "developerName": "Andres Massello", "category": "Productivity", "capabilities": ["Write", "Interactive"],
            "defaultPrompt": ["Run Uscha discovery for this feature.", "Use Uscha devloop to verify this change.", "Show the Uscha readiness for this repo."], "brandColor": "#7C3AED"}}


def marker(target, install_root, mode):
    return {"name": PLUGIN_NAME, "target": target, "version": source_version(), "mode": mode,
            "installed_at": now_iso(), "source": str(KIT_ROOT), "install_root": str(install_root)}


def marketplace_entry():
    return {"name": PLUGIN_NAME, "source": {"source": "local", "path": "./plugins/uscha"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Productivity"}


def valid_marketplace_source(source):
    if not isinstance(source, dict) or source.get("source") != "local":
        return False
    path = source.get("path")
    if not isinstance(path, str) or not path or not path.startswith("./"):
        return False
    return not any(part in ("", ".", "..") for part in path[2:].split("/"))


def valid_marketplace_plugin(plugin):
    if not isinstance(plugin, dict) or not isinstance(plugin.get("name"), str) or not plugin["name"].strip():
        return False
    policy = plugin.get("policy")
    if (not isinstance(policy, dict)
            or policy.get("installation") not in {"AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"}
            or policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}):
        return False
    return (valid_marketplace_source(plugin.get("source"))
            and isinstance(plugin.get("category"), str) and bool(plugin["category"].strip()))


def valid_marketplace(data):
    interface = data.get("interface") if isinstance(data, dict) else None
    interface_ok = ("interface" not in data or isinstance(interface, dict)) if isinstance(data, dict) else False
    if interface_ok and isinstance(interface, dict) and "displayName" in interface:
        interface_ok = isinstance(interface["displayName"], str) and bool(interface["displayName"].strip())
    return (isinstance(data, dict) and isinstance(data.get("name"), str) and bool(data["name"].strip())
            and interface_ok and isinstance(data.get("plugins"), list)
            and all(valid_marketplace_plugin(plugin) for plugin in data["plugins"]))


def prepared_marketplace(path):
    data = {"name": "personal", "interface": {"displayName": "Personal"}, "plugins": []}
    if path.exists():
        data = load_json(path, "marketplace.json")
    if not valid_marketplace(data):
        raise InstallError("[install-uscha] marketplace.json has no supported required shape: %s" % path)
    entry = marketplace_entry()
    plugins = list(data["plugins"])
    index = next((i for i, plugin in enumerate(plugins) if plugin["name"] == PLUGIN_NAME), None)
    if index is None:
        plugins.append(entry)
    else:
        plugins[index] = entry
    result = dict(data)
    result["plugins"] = plugins
    return result


def hook_command(hook):
    parts = [sys.executable, str(hook)]
    return subprocess.list2cmdline(parts) if os.name == "nt" else " ".join(shlex.quote(part) for part in parts)


def hook_registered(settings, command):
    hooks = settings.get("hooks", {}) if isinstance(settings, dict) else {}
    groups = hooks.get("PreToolUse", []) if isinstance(hooks, dict) else []
    return any(isinstance(group, dict) and group.get("matcher") == "*"
               and any(isinstance(item, dict) and item.get("type") == "command" and item.get("command") == command
                       for item in group.get("hooks", []) if isinstance(group.get("hooks", []), list))
               for group in groups if isinstance(groups, list))


def prepared_settings(path, command):
    data = {} if not path.exists() else load_json(path, "Claude settings.json")
    if not isinstance(data, dict):
        raise InstallError("[install-uscha] Claude settings.json must be an object: %s" % path)
    hooks_data = data.get("hooks", {})
    if not isinstance(hooks_data, dict):
        raise InstallError("[install-uscha] Claude settings hooks must be an object: %s" % path)
    groups_data = hooks_data.get("PreToolUse", [])
    if not isinstance(groups_data, list):
        raise InstallError("[install-uscha] Claude PreToolUse hooks must be an array: %s" % path)
    for group in groups_data:
        if not isinstance(group, dict):
            raise InstallError("[install-uscha] Claude PreToolUse group must be an object: %s" % path)
        items = group.get("hooks", [])
        if not isinstance(items, list):
            raise InstallError("[install-uscha] Claude PreToolUse group hooks must be an array: %s" % path)
        if not all(isinstance(item, dict) for item in items):
            raise InstallError("[install-uscha] Claude PreToolUse hook item must be an object: %s" % path)
    result = dict(data)
    hooks = dict(hooks_data)
    groups = list(groups_data)
    if not hook_registered(result, command):
        groups.append({"matcher": "*", "hooks": [{"type": "command", "command": command}]})
    hooks["PreToolUse"] = groups
    result["hooks"] = hooks
    return result


def stage_plugin(plugin_root, mode):
    source = source_skills()
    stage = plugin_root.parent / (".%s.staging-%s" % (PLUGIN_NAME, uuid.uuid4().hex))
    stage.mkdir(parents=True)
    try:
        (stage / ".codex-plugin").mkdir()
        atomic_json(stage / ".codex-plugin" / "plugin.json", plugin_manifest())
        (stage / "skills").mkdir()
        for skill in SKILLS:
            copy_skill(source / skill, stage / "skills" / skill, mode)
        shutil.copy2(KIT_ROOT / "VERSION", stage / "VERSION")
        shutil.copy2(KIT_ROOT / "uscha.config.json", stage / "uscha.config.json")
        return stage
    except Exception:
        remove_path(stage)
        raise


def install_codex(home, mode, dry_run, operations):
    plugin_root = home / "plugins" / PLUGIN_NAME
    market = home / ".agents" / "plugins" / "marketplace.json"
    market_data = prepared_marketplace(market)  # preflight before any filesystem mutation, including dry-run
    operations.append({"action": "stage-plugin", "path": str(plugin_root)})
    operations.extend({"action": "copy-dir", "path": str(plugin_root / "skills" / skill)} for skill in SKILLS)
    operations.extend([{"action": "atomic-write-json", "path": str(market)}, {"action": "write-marker-last", "path": str(plugin_root / "uscha-install.json")}])
    if dry_run:
        return plugin_root
    stage = stage_plugin(plugin_root, mode)
    backup = plugin_root.parent / (".%s.backup-%s" % (PLUGIN_NAME, uuid.uuid4().hex))
    market_existed = market.exists()
    market_before = market.read_bytes() if market_existed else None
    missing_market_dirs = []
    directory = market.parent
    while directory != home and not directory.exists():
        missing_market_dirs.append(directory)
        directory = directory.parent
    swapped = False
    market_mutated = False
    try:
        plugin_root.parent.mkdir(parents=True, exist_ok=True)
        if plugin_root.exists() or plugin_root.is_symlink():
            os.replace(plugin_root, backup)
        os.replace(stage, plugin_root)
        swapped = True
        atomic_json(market, market_data)
        market_mutated = True
        atomic_json(plugin_root / "uscha-install.json", marker("codex", plugin_root, mode))
    except Exception as exc:
        rollback_errors = []
        if swapped:
            try:
                remove_path(plugin_root)
                if backup.exists() or backup.is_symlink():
                    os.replace(backup, plugin_root)
            except Exception as rollback_exc:
                rollback_errors.append("%s: %s" % (plugin_root, rollback_exc))
        if market_mutated:
            try:
                if market_existed:
                    atomic_bytes(market, market_before)
                elif market.exists() or market.is_symlink():
                    remove_path(market)
                for created in missing_market_dirs:
                    try:
                        created.rmdir()
                    except OSError:
                        pass
            except Exception as rollback_exc:
                rollback_errors.append("%s: %s" % (market, rollback_exc))
        if rollback_errors:
            raise InstallError("[install-uscha] Codex rollback incomplete: %s" % "; ".join(rollback_errors)) from exc
        raise
    finally:
        if stage.exists():
            remove_path(stage)
        if backup.exists() or backup.is_symlink():
            remove_path(backup)
    return plugin_root


def install_claude(home, mode, dry_run, operations):
    source = source_skills()
    root = home / ".claude"
    hook = root / "hooks" / HOOK_NAME
    settings = root / "settings.json"
    install_marker = root / "uscha-install.json"
    data = prepared_settings(settings, hook_command(hook))  # parse and merge before writes, including dry-run
    marker_data = marker("claude", root, mode)
    operations.extend({"action": "install-skill", "path": str(root / "skills" / skill)} for skill in SKILLS)
    operations.extend([{"action": "copy-hook", "path": str(hook)}, {"action": "atomic-write-json", "path": str(settings)}, {"action": "write-marker-last", "path": str(install_marker)}])
    if dry_run:
        return root

    home_existed = home.exists()
    home.mkdir(parents=True, exist_ok=True)
    transaction = home / (".uscha-claude-transaction-%s" % uuid.uuid4().hex)
    staged = transaction / "staged"
    backups = transaction / "backups"
    cleanup_transaction = True
    try:
        (staged / "skills").mkdir(parents=True)
        backups.mkdir()
        for skill in SKILLS:
            copy_skill(source / skill, staged / "skills" / skill, mode)
        (staged / "hooks").mkdir()
        shutil.copy2(KIT_ROOT / "hooks" / HOOK_NAME, staged / "hooks" / HOOK_NAME)
        atomic_json(staged / "settings.json", data)
        atomic_json(staged / "uscha-install.json", marker_data)

        skills_root = root / "skills"
        entries = [(skills_root / skill, staged / "skills" / skill, backups / "skills" / skill)
                   for skill in SKILLS]
        entries.extend([
            (hook, staged / "hooks" / HOOK_NAME, backups / "hooks" / HOOK_NAME),
            (settings, staged / "settings.json", backups / "settings.json"),
            (install_marker, staged / "uscha-install.json", backups / "uscha-install.json"),
        ])
        preexisting = {target: target.exists() or target.is_symlink()
                       for target, _, _ in entries}
        created_dirs = []
        backed_up = set()
        installed = set()

        try:
            for directory in (root, skills_root, hook.parent):
                if not directory.exists():
                    directory.mkdir(parents=True)
                    created_dirs.append(directory)

            for target, replacement, backup in entries:
                if preexisting[target]:
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(target, backup)
                    backed_up.add(target)
                os.replace(replacement, target)
                installed.add(target)
        except Exception as exc:
            rollback_errors = []
            for target, _, backup in reversed(entries):
                try:
                    if target in installed and (target.exists() or target.is_symlink()):
                        remove_path(target)
                    if target in backed_up and (backup.exists() or backup.is_symlink()):
                        target.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(backup, target)
                except Exception as rollback_exc:
                    rollback_errors.append("%s: %s" % (target, rollback_exc))
            for directory in reversed(created_dirs):
                try:
                    directory.rmdir()
                except OSError:
                    pass
            if rollback_errors:
                cleanup_transaction = False
                raise InstallError(
                    "[install-uscha] Claude rollback incomplete; recovery retained at %s (%s)"
                    % (transaction, "; ".join(rollback_errors))
                ) from exc
            raise
    finally:
        if cleanup_transaction and (transaction.exists() or transaction.is_symlink()):
            remove_path(transaction)
        if not home_existed:
            try:
                home.rmdir()
            except OSError:
                pass
    return root

def marker_ok(path, target):
    if not path.is_file():
        return False, None
    try:
        data = load_json(path, "install marker")
    except InstallError:
        return False, None
    return data.get("name") == PLUGIN_NAME and data.get("target") == target and data.get("version") == source_version(), data.get("version")


def target_status(home, target):
    if target == "codex":
        root = home / "plugins" / PLUGIN_NAME
        skills_root, marker_path = root / "skills", root / "uscha-install.json"
        manifest_path, market_path = root / ".codex-plugin" / "plugin.json", home / ".agents" / "plugins" / "marketplace.json"
        skills_present = [skill for skill in SKILLS if (skills_root / skill / "SKILL.md").is_file()]
        try:
            manifest = load_json(manifest_path, "plugin manifest")
            manifest_ok = manifest.get("name") == PLUGIN_NAME and manifest.get("version") == source_version()
        except InstallError:
            manifest_ok = False
        try:
            market = prepared_marketplace(market_path)
            marketplace_ok = market == load_json(market_path, "marketplace.json") and any(p == marketplace_entry() for p in market["plugins"])
        except InstallError:
            marketplace_ok = False
        checks = {"skills_present": skills_present, "manifest": manifest_ok, "marketplace_registered": marketplace_ok}
    else:
        root = home / ".claude"
        skills_root, marker_path = root / "skills", root / "uscha-install.json"
        hook, settings_path = root / "hooks" / HOOK_NAME, root / "settings.json"
        skills_present = [skill for skill in SKILLS if (skills_root / skill / "SKILL.md").is_file()]
        try:
            settings_ok = hook_registered(load_json(settings_path, "Claude settings.json"), hook_command(hook))
        except InstallError:
            settings_ok = False
        checks = {"skills_present": skills_present, "hook_file": hook.is_file(), "hook_registered": settings_ok}
    marker_valid, installed_version = marker_ok(marker_path, target)
    checks["marker"] = marker_valid
    checks["source_version_match"] = installed_version == source_version()
    healthy = len(skills_present) == len(SKILLS) and all(value is True for key, value in checks.items() if key != "skills_present")
    return {"healthy": healthy, "installed": healthy, "install_root": str(root), "installed_version": installed_version,
            "source_version": source_version(), "version_match": installed_version == source_version(), "checks": checks,
            "content_integrity": "not measured; checks verify presence, registration, marker, and version only"}


def cmd_version(args):
    emit({"name": PLUGIN_NAME, "source_version": source_version(), "targets": list(TARGETS)}, args.json)


def cmd_install(args):
    home, operations, installed = home_path(args), [], {}
    for target in selected_targets(args.target):
        installed[target] = str(install_codex(home, args.mode, args.dry_run, operations) if target == "codex" else install_claude(home, args.mode, args.dry_run, operations))
    emit({"status": "planned" if args.dry_run else "installed", "dry_run": args.dry_run, "source_version": source_version(), "home": str(home), "installed": installed, "operations": operations, "next": next_steps(args.target)}, args.json)


def cmd_doctor(args):
    home = home_path(args)
    targets = {target: target_status(home, target) for target in selected_targets(args.target)}
    ok = all(status["healthy"] for status in targets.values())
    emit({"ok": ok, "source_version": source_version(), "home": str(home), "python": sys.version.split()[0], "targets": targets}, args.json)
    if not ok:
        raise SystemExit(1)


def cmd_init(args):
    repo, operations, conflicts = Path(args.repo).expanduser().resolve(), [], []
    sources = [(KIT_ROOT / "uscha.config.json", repo / "uscha.config.json")] + [(KIT_ROOT / "templates" / name, repo / name) for name in ("CLAUDE.md", "CONSTITUTION.md", ".gitattributes")]
    copies = []
    for source, target in sources:
        if not source.is_file():
            raise InstallError("[install-uscha] init source missing: %s" % source)
        if target.is_symlink():
            raise InstallError("[install-uscha] init target must not be a symlink: %s" % target)
        if target.exists() and not target.is_file():
            raise InstallError("[install-uscha] init target must be a file: %s" % target)
        if target.exists() and target.read_bytes() != source.read_bytes() and not args.force:
            conflicts.append({"path": str(target), "source": str(source)})
            operations.append({"action": "conflict", "path": str(target), "source": str(source)})
        elif target.exists() and target.read_bytes() == source.read_bytes():
            operations.append({"action": "unchanged", "path": str(target)})
        else:
            operations.append({"action": "copy-file", "path": str(target), "source": str(source), "note": "force" if target.exists() else None})
            copies.append((source, target))
    conflicted = bool(conflicts)
    if not conflicted and not args.dry_run:
        for source, target in copies:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    emit({"status": "conflicts" if conflicted else ("planned" if args.dry_run else "initialized"), "dry_run": args.dry_run, "repo": str(repo), "operations": operations, "conflicts": conflicts}, args.json)
    if conflicted:
        raise SystemExit(1)


def next_steps(target):
    steps = []
    if target in ("codex", "both"): steps.append("Codex: restart or open a new thread, then install/use uscha from the Personal marketplace if needed.")
    if target in ("claude", "both"): steps.append("Claude: restart Claude Code so global skills/hooks are reloaded.")
    return steps + ["Run: python install-uscha.py doctor --target %s" % target]


def emit(data, as_json):
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False)); return
    if "targets" in data and isinstance(data["targets"], dict):
        print("Uscha %s" % data.get("source_version"))
        for name, status in data["targets"].items(): print("  %s %s" % ("OK" if status["healthy"] else "WARN", name))
    elif "operations" in data:
        print("Uscha %s: %s (%s operations)" % (data.get("source_version", source_version()), data["status"], len(data["operations"])))
        for operation in data["operations"][:20]: print("  - {action}: {path}".format(**operation))
    else:
        print("Uscha %s" % data.get("source_version", source_version()))


def build_parser():
    parser = argparse.ArgumentParser(description="Install/update Uscha for Codex and Claude machines")
    sub = parser.add_subparsers(dest="cmd", required=True)
    version = sub.add_parser("version", help="show source version and supported targets"); version.add_argument("--json", action="store_true"); version.set_defaults(func=cmd_version)
    install = sub.add_parser("install", help="install Uscha globally for a machine")
    install.add_argument("--target", choices=["codex", "claude", "both"], default="both"); install.add_argument("--mode", choices=["copy", "link"], default="copy"); install.add_argument("--home"); install.add_argument("--dry-run", action="store_true"); install.add_argument("--json", action="store_true"); install.set_defaults(func=cmd_install)
    doctor = sub.add_parser("doctor", help="check installed Uscha presence, registrations, and version drift")
    doctor.add_argument("--target", choices=["codex", "claude", "both"], default="both"); doctor.add_argument("--home"); doctor.add_argument("--json", action="store_true"); doctor.set_defaults(func=cmd_doctor)
    init = sub.add_parser("init", help="prepare a repo with Uscha config/templates")
    init.add_argument("--repo", default="."); init.add_argument("--force", action="store_true", help="replace differing init files deliberately"); init.add_argument("--dry-run", action="store_true"); init.add_argument("--json", action="store_true"); init.set_defaults(func=cmd_init)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except InstallError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
