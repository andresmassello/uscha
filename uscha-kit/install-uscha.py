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
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent
PLUGIN_NAME = "uscha"
SKILLS = ["uscha-discovery", "uscha-adr-refine", "uscha-reverse-discovery", "uscha-characterize",
          "uscha-devloop", "uscha-sysdoc", "uscha-rubric", "uscha-mirador",
          "uscha-status"]
# Agent-Skills targets: harness-neutral, SKILLS-ONLY installs. Each agent reads the 9 uscha-*
# skill directories from its own root -- no plugin manifest, no settings.json, no hook. They all
# share one transactional installer and one doctor branch, so a sixth costs a table row (kit
# 1.53.0). Roots are the directories each agent documents for the Agent Skills standard.
SKILL_ROOTS = {
    "pi":      (".agents", "skills"),    # Earendil pi
    "cursor":  (".cursor", "skills"),    # Cursor
    "copilot": (".copilot", "skills"),   # VS Code / GitHub Copilot
    "gemini":  (".gemini", "skills"),    # Gemini CLI
    "cline":   (".cline", "skills"),     # Cline
}
TARGETS = ("codex", "claude") + tuple(SKILL_ROOTS)
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
    # `all` = every target in TARGETS, so a new Agent-Skills row is picked up automatically;
    # `both` stays a LEGACY alias for codex+claude so existing scripts/users keep their exact
    # prior behavior -- it deliberately does NOT grow as targets are added.
    return {"all": list(TARGETS), "both": ["codex", "claude"]}.get(value, [value])


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
            "homepage": "https://uscha.dev", "repository": "https://github.com/andresmassello/uscha",
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
    # Match a registered PreToolUse "*" hook by the guard SCRIPT it references (PATH-ANCHORED),
    # not by exact command equality. `command` embeds sys.executable, an absolute interpreter
    # path: install-time and doctor-time can run under different interpreters (a `python` that
    # resolves to a different sys.executable between two invocations -- observed on Windows CI),
    # so an exact-match false-reports a healthy hook as unregistered. Anchoring on a path
    # separator before HOOK_NAME (the installer always writes it under a `hooks/` dir) keeps a
    # foreign command that merely MENTIONS the name -- `...not-block-approved-writes.py`, or the
    # literal inside a `-c` snippet -- from reading as our enforced guard, since this check feeds
    # the golden_guard trust signal. Exact `command` stays a fallback; a None command is skipped.
    anchored = ("/" + HOOK_NAME, "\\" + HOOK_NAME)
    def _is_ours(cmd):
        return isinstance(cmd, str) and (any(a in cmd for a in anchored) or cmd == command)
    hooks = settings.get("hooks", {}) if isinstance(settings, dict) else {}
    groups = hooks.get("PreToolUse", []) if isinstance(hooks, dict) else []
    return any(isinstance(group, dict) and group.get("matcher") == "*"
               and any(isinstance(item, dict) and item.get("type") == "command" and _is_ours(item.get("command"))
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
    # N-1 (kit 1.50.2): prune ANY prior uscha hook entry -- matched by the hook script's
    # basename, NOT the exact command -- before adding the current one. The command carries
    # an ABSOLUTE sys.executable, so an interpreter move (homebrew 3.12->3.13, pyenv, the
    # Windows Store python) would otherwise leave a dead entry that fails on every tool call
    # while the fresh one is merely appended. Suffix-pruning makes a reinstall self-heal.
    def _ours(item):
        # substring, NOT suffix: list2cmdline (Windows) / shlex.quote (POSIX) wrap a path
        # with spaces in quotes, so the command can end in `...block-approved-writes.py"`.
        # The script basename is specific enough that a foreign hook won't contain it.
        c = str(item.get("command", "")).replace("\\", "/") if isinstance(item, dict) else ""
        return HOOK_NAME in c
    groups = []
    for group in groups_data:
        kept = [it for it in group.get("hooks", []) if not _ours(it)]
        if kept:                          # keep foreign hooks; drop a group that was ONLY ours
            g = dict(group)
            g["hooks"] = kept
            groups.append(g)
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
    backed_up = False
    market_mutated = False
    try:
        plugin_root.parent.mkdir(parents=True, exist_ok=True)
        if plugin_root.exists() or plugin_root.is_symlink():
            os.replace(plugin_root, backup)
            backed_up = True
        os.replace(stage, plugin_root)
        swapped = True
        atomic_json(market, market_data)
        market_mutated = True
        atomic_json(plugin_root / "uscha-install.json", marker("codex", plugin_root, mode))
        # success: the pre-existing plugin (now in backup) is stale -- drop it HERE, not
        # in `finally`, so a failure can never delete the backup before it is restored
        # (kit 1.41.1 adversarial-review fix -- the Codex path used to gate the restore on
        # `swapped` and unconditionally delete the backup, destroying the user's install).
        if backed_up and (backup.exists() or backup.is_symlink()):
            remove_path(backup)
            backed_up = False
    except Exception as exc:
        rollback_errors = []
        # restore gated on the BACKUP existing (not on `swapped`): if the swap failed
        # AFTER the original was moved to backup, the original still lives in backup.
        try:
            if swapped and (plugin_root.exists() or plugin_root.is_symlink()):
                remove_path(plugin_root)
            if backed_up and (backup.exists() or backup.is_symlink()):
                os.replace(backup, plugin_root)
                backed_up = False
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
        # backup is intentionally NOT deleted here: on success it was dropped above; on
        # failure it was restored; on a hard interrupt (KeyboardInterrupt bypasses the
        # except) it is left in place so the user's original is never destroyed.
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

def install_skills_only(target, home, mode, dry_run, operations):
    # One installer for every Agent-Skills target (SKILL_ROOTS): the 9 skills land flat under
    # that agent's own root. Skills only -- no manifest, no settings.json, no hook. Same
    # transactional shape as install_claude: stage -> back up -> atomic replace -> marker last,
    # so a late failure rolls the target back with nothing lost.
    source = source_skills()
    root = home.joinpath(*SKILL_ROOTS[target])
    install_marker = root / "uscha-install.json"
    marker_data = marker(target, root, mode)
    operations.extend({"action": "install-skill", "path": str(root / skill)} for skill in SKILLS)
    operations.append({"action": "write-marker-last", "path": str(install_marker)})
    if dry_run:
        return root

    home_existed = home.exists()
    home.mkdir(parents=True, exist_ok=True)
    transaction = home / (".uscha-%s-transaction-%s" % (target, uuid.uuid4().hex))
    staged = transaction / "staged"
    backups = transaction / "backups"
    cleanup_transaction = True
    try:
        staged.mkdir(parents=True)
        backups.mkdir()
        for skill in SKILLS:
            copy_skill(source / skill, staged / skill, mode)
        atomic_json(staged / "uscha-install.json", marker_data)

        entries = [(root / skill, staged / skill, backups / skill) for skill in SKILLS]
        entries.append((install_marker, staged / "uscha-install.json", backups / "uscha-install.json"))
        # The loops below bind PATHS. They must NOT be named `target`: a Python for-loop has no
        # scope of its own, so that would permanently rebind this function's `target` argument
        # (the target NAME) to a Path, and the rollback error below would then report a file
        # path instead of naming which target failed -- exactly when that matters most.
        preexisting = {path: path.exists() or path.is_symlink()
                       for path, _, _ in entries}
        created_dirs = []
        backed_up = set()
        installed = set()
        try:
            for directory in (root.parent, root):   # e.g. ~/.cursor then ~/.cursor/skills
                if not directory.exists():
                    directory.mkdir(parents=True)
                    created_dirs.append(directory)
            for path, replacement, backup in entries:
                if preexisting[path]:
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(path, backup)
                    backed_up.add(path)
                os.replace(replacement, path)
                installed.add(path)
        except Exception as exc:
            rollback_errors = []
            for path, _, backup in reversed(entries):
                try:
                    if path in installed and (path.exists() or path.is_symlink()):
                        remove_path(path)
                    if path in backed_up and (backup.exists() or backup.is_symlink()):
                        path.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(backup, path)
                except Exception as rollback_exc:
                    rollback_errors.append("%s: %s" % (path, rollback_exc))
            for directory in reversed(created_dirs):
                try:
                    directory.rmdir()
                except OSError:
                    pass
            if rollback_errors:
                cleanup_transaction = False
                raise InstallError(
                    "[install-uscha] %s rollback incomplete; recovery retained at %s (%s)"
                    % (target, transaction, "; ".join(rollback_errors))
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
        guard = "advisory"   # Codex has no hooks mechanism (verified: .codex-plugin has no "hooks")
    elif target in SKILL_ROOTS:
        # Agent-Skills targets: the skills live FLAT under that agent's root; no manifest, no
        # hook. INV-GOLDEN-01 is therefore ADVISORY on all of them -- none exposes a blocking
        # pre-tool hook the way Claude's PreToolUse does. pi is the one exception in waiting: a
        # `tool_call` extension ships (uscha-kit/pi/golden-guard.js), but it stays advisory until
        # a real pi run measures the block. The kit does not claim enforcement it has not seen.
        root = home.joinpath(*SKILL_ROOTS[target])
        skills_root, marker_path = root, root / "uscha-install.json"
        skills_present = [skill for skill in SKILLS if (skills_root / skill / "SKILL.md").is_file()]
        checks = {"skills_present": skills_present}
        guard = "advisory"
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
        # INV-GOLDEN-01 is MECHANICAL on Claude only when the PreToolUse hook is registered.
        guard = "enforced" if settings_ok else "advisory"
    marker_valid, installed_version = marker_ok(marker_path, target)
    checks["marker"] = marker_valid
    checks["source_version_match"] = installed_version == source_version()
    healthy = len(skills_present) == len(SKILLS) and all(value is True for key, value in checks.items() if key != "skills_present")
    return {"healthy": healthy, "installed": healthy, "install_root": str(root), "installed_version": installed_version,
            "source_version": source_version(), "version_match": installed_version == source_version(), "checks": checks,
            "golden_guard": guard,   # per-target INV-GOLDEN-01: enforced (mechanical) | advisory
            "content_integrity": "not measured; checks verify presence, registration, marker, and version only"}


def cmd_version(args):
    emit({"name": PLUGIN_NAME, "source_version": source_version(), "targets": list(TARGETS)}, args.json)


def cmd_install(args):
    home, operations, installed = home_path(args), [], {}
    installers = {"codex": install_codex, "claude": install_claude}
    for target in selected_targets(args.target):
        if target in SKILL_ROOTS:
            root = install_skills_only(target, home, args.mode, args.dry_run, operations)
        else:
            root = installers[target](home, args.mode, args.dry_run, operations)
        installed[target] = str(root)
    emit({"status": "planned" if args.dry_run else "installed", "dry_run": args.dry_run, "source_version": source_version(), "home": str(home), "installed": installed, "operations": operations, "next": next_steps(args.target)}, args.json)


def cmd_doctor(args):
    home = home_path(args)
    targets = {target: target_status(home, target) for target in selected_targets(args.target)}
    ok = all(status["healthy"] for status in targets.values())
    emit({"ok": ok, "source_version": source_version(), "home": str(home), "python": sys.version.split()[0], "targets": targets}, args.json)
    if not ok:
        raise SystemExit(1)


# statusline wiring (kit 1.46.0): the progress statusline + its Stop-hook refresher, installed
# per-project. Commands are by NAME with forward slashes (Windows eats backslashes in the
# statusLine command; absolute paths are brittle across machines).
# The interpreter is OS-resolved (kit 1.50.2): `python3` on POSIX -- stock mac/Linux often
# ships only python3, so a bare `python` left the whole feature silently dead there -- and
# `python` on Windows, where `python3` may be a non-executing Store stub. Same rule as
# bin/uscha.js and workbench-doctor.sh; init runs on the target machine, so os.name is right.
STATUSLINE_SCRIPTS = ("uscha_statusline.py", "uscha_progress.py")
_STATUSLINE_PY = "python" if os.name == "nt" else "python3"
STATUSLINE_CMD = _STATUSLINE_PY + " .claude/scripts/uscha_statusline.py"
PROGRESS_CMD = _STATUSLINE_PY + " .claude/scripts/uscha_progress.py"


def _wire_statusline_settings(repo, force, dry_run):
    """Merge statusLine + a Stop hook into <repo>/.claude/settings.json WITHOUT clobbering:
    an existing DIFFERENT statusLine is reported as a conflict (never overwritten unless
    --force); the Stop hook is appended only if not already registered (idempotent).
    Returns (operations, wrote, conflicts)."""
    path = repo / ".claude" / "settings.json"
    ops, conflicts = [], []
    data = {}
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise InstallError("[install-uscha] settings.json must be a file: %s" % path)
        data = load_json(path, "Claude settings.json")
        if not isinstance(data, dict):
            raise InstallError("[install-uscha] settings.json must be an object: %s" % path)
    result = dict(data)
    changed = False
    want_sl = {"type": "command", "command": STATUSLINE_CMD}
    cur_sl = result.get("statusLine")
    # ours-by-suffix (kit 1.50.2): an existing statusLine that runs OUR script but with a
    # different interpreter (e.g. a pre-1.50.2 `python` entry on an upgraded mac) is refreshed,
    # not reported as a foreign conflict. A truly foreign statusLine still conflicts.
    cur_cmd = cur_sl.get("command", "") if isinstance(cur_sl, dict) else ""
    ours_sl = isinstance(cur_sl, dict) and cur_cmd.endswith("uscha_statusline.py")
    if cur_sl is None or ((ours_sl or force) and cur_sl != want_sl):
        result["statusLine"] = want_sl
        changed = True
        ops.append({"action": "wire-statusline", "path": str(path)})
    elif cur_sl == want_sl:
        ops.append({"action": "unchanged", "path": str(path) + " (statusLine)"})
    else:
        conflicts.append({"path": str(path), "source": "statusLine"})
        ops.append({"action": "conflict", "path": str(path), "source": "statusLine"})
    hooks = result.get("hooks") if isinstance(result.get("hooks"), dict) else {}
    stop = hooks.get("Stop") if isinstance(hooks.get("Stop"), list) else []
    # prune OUR Stop hook by script suffix (not exact command) before re-adding, so an
    # upgraded install whose entry runs the old `python` interpreter self-heals to `python3`
    # instead of accumulating a dead duplicate -- the same self-healing N-1 gives the golden
    # hook and the ours-by-suffix refresh gives the statusLine. Foreign Stop hooks are kept.
    def _ours_prog(h):
        return isinstance(h, dict) and "uscha_progress.py" in str(h.get("command", ""))
    pruned = []
    for g in stop:
        if isinstance(g, dict) and isinstance(g.get("hooks"), list):
            kept = [h for h in g["hooks"] if not _ours_prog(h)]
            if kept:
                gg = dict(g); gg["hooks"] = kept; pruned.append(gg)
        else:
            pruned.append(g)
    new_stop = pruned + [{"hooks": [{"type": "command", "command": PROGRESS_CMD}]}]
    if new_stop != stop:                 # differs -> a stale entry was pruned or none existed
        hooks = dict(hooks)
        hooks["Stop"] = new_stop
        result["hooks"] = hooks
        changed = True
        ops.append({"action": "wire-stop-hook", "path": str(path)})
    else:
        ops.append({"action": "unchanged", "path": str(path) + " (Stop hook)"})
    wrote = False
    if changed and not dry_run:
        atomic_json(path, result)
        wrote = True
    return ops, wrote, conflicts


def cmd_init(args):
    repo, operations, conflicts = Path(args.repo).expanduser().resolve(), [], []
    sources = ([(KIT_ROOT / "uscha.config.json", repo / "uscha.config.json")]
               + [(KIT_ROOT / "templates" / name, repo / name)
                  # AGENTS.md (kit 1.50.2): the context file Codex/pi read (they do not read
                  # CLAUDE.md); shipped as a thin pointer to CLAUDE.md so there is ONE source.
                  for name in ("CLAUDE.md", "AGENTS.md", "CONSTITUTION.md", ".gitattributes")]
               + [(KIT_ROOT / "templates" / "scripts" / s, repo / ".claude" / "scripts" / s)
                  for s in STATUSLINE_SCRIPTS])
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
    # per-file, not all-or-nothing (kit 1.44.1): a differing CLAUDE.md (which EVERY repo
    # already using Claude Code has) used to block ALL four copies. Now the non-conflicting
    # files are written regardless; each conflict is reported and left untouched (resolve by
    # hand, or re-run with --force). Exit stays nonzero while any conflict remains.
    if not args.dry_run:
        for source, target in copies:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    # wire the statusline (kit 1.46.0): merge statusLine + Stop hook into the project's
    # settings.json so the user never edits it by hand -- never clobbering existing keys.
    sl_ops, sl_wrote, sl_conflicts = _wire_statusline_settings(repo, args.force, args.dry_run)
    operations.extend(sl_ops)
    conflicts.extend(sl_conflicts)
    conflicted = bool(conflicts)
    if conflicted:
        status = "conflicts" if args.dry_run else "partial"
    else:
        status = "planned" if args.dry_run else "initialized"
    wrote = [str(t) for _, t in copies] if not args.dry_run else []
    if sl_wrote:
        wrote.append(str(repo / ".claude" / "settings.json"))
    emit({"status": status, "dry_run": args.dry_run, "repo": str(repo),
          "wrote": wrote, "operations": operations, "conflicts": conflicts}, args.json)
    if conflicted:
        raise SystemExit(1)


def _open_best_effort(path):
    """Open the rendered file in the default browser; never fail (headless/CI)."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]  # Windows-only
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass  # the renderer already printed the absolute path


def _kit_script_path(skill_dir, filename):
    """A script inside this kit, in either skill-tree layout (`skills/<skill_dir>/` or
    `.claude/skills/<skill_dir>/`) -- the one resolution every sibling script lookup in this
    file shares, and the same both-layouts precedent `uscha_top.py::engine_path()` uses on
    its own side of the lookup."""
    for rel in (("skills", skill_dir, filename), (".claude", "skills", skill_dir, filename)):
        candidate = KIT_ROOT.joinpath(*rel)
        if candidate.is_file():
            return candidate
    return None


def cmd_mirador(args):
    """`uscha mirador` — one command to render + open the project's dashboard.
    No paths, no python: the renderer self-resolves its engine/template siblings, and the
    ledger defaults to the QA-LEDGER.json convention in the current directory."""
    render = _kit_script_path("uscha-mirador", "mirador-render.py")
    if render is None:
        print("[uscha mirador] mirador-render.py not found in the kit", file=sys.stderr)
        raise SystemExit(1)
    if not Path(args.ledger).is_file():
        print("[uscha mirador] ledger '%s' not found here -- run the dev loop first, or pass --ledger"
              % args.ledger, file=sys.stderr)
        raise SystemExit(1)
    base = [sys.executable, str(render), "--ledger", args.ledger, "--out", args.out]
    if not args.watch:
        # one-shot: the renderer writes the file and opens it only when FIRST materializing it
        # -- a re-render updates the already-open tab in place instead of spawning another
        # (kit 1.51.2). --no-open suppresses; --open forces a reopen when the tab was closed.
        extra = ["--no-open"] if args.no_open else (["--open"] if args.force_open else [])
        rc = subprocess.call(base + extra)
        if rc:
            raise SystemExit(rc)
        return
    # live view: the page carries its own meta-refresh and reloads itself in ONE tab, so we
    # open once here and re-render quietly forever -- never re-open (no browser-tab spam).
    rc = subprocess.call(base + ["--refresh", str(args.interval), "--no-open"])
    if rc:
        raise SystemExit(rc)
    out_abs = os.path.abspath(args.out)
    if not args.no_open:
        _open_best_effort(out_abs)
    print("[uscha mirador] live view every %ss at %s -- Ctrl-C to stop" % (args.interval, out_abs))
    try:
        while True:
            time.sleep(args.interval)
            subprocess.call(base + ["--refresh", str(args.interval), "--no-open"])
    except KeyboardInterrupt:
        print("\n[uscha mirador] stopped")


def cmd_top(args):
    """`uscha top` — the live terminal board of the project's ledger (ADR-031).
    Wired exactly like `mirador`: resolve the sibling script inside the kit and exec it with
    this interpreter. `--json` is a passthrough to the engine's own read-only subcommand, so
    a script can consume the contract without going through the renderer at all."""
    if not Path(args.ledger).is_file():
        print("[uscha top] ledger '%s' not found here -- run the dev loop first, or pass "
              "--ledger" % args.ledger, file=sys.stderr)
        raise SystemExit(1)
    if args.json:
        engine = _kit_script_path("uscha-devloop", "qa_ledger.py")
        if engine is None:
            print("[uscha top] qa_ledger.py not found in the kit", file=sys.stderr)
            raise SystemExit(1)
        rc = subprocess.call([sys.executable, str(engine), "top", "--json",
                              "--ledger", args.ledger])
        if rc:
            raise SystemExit(rc)
        return
    renderer = _kit_script_path("uscha-devloop", "uscha_top.py")
    if renderer is None:
        print("[uscha top] uscha_top.py not found in the kit", file=sys.stderr)
        raise SystemExit(1)
    cmd = [sys.executable, str(renderer), "--ledger", args.ledger,
           "--refresh", str(args.refresh)]
    if args.once:
        cmd.append("--once")
    # the verdict's author travels from the launcher too (1.89.0): the person at the keyboard
    # is who the record names, and an SSH or multi-user session cannot be resolved from the
    # environment of whichever process happens to run `curate` (ADR-033). Absent -> not passed,
    # and uscha_top.py falls back to $USERNAME/$USER, then to curate's own default.
    if getattr(args, "human", None):
        cmd += ["--human", args.human]
    rc = subprocess.call(cmd)
    if rc:
        raise SystemExit(rc)


def settings_without_hook(path):
    """Return (new_settings, removed_count): the user's settings with OUR PreToolUse entries
    dropped and nothing else touched. A foreign hook -- including one in the same group -- is
    preserved; an emptied group disappears rather than being left as an empty shell."""
    if not path.exists():
        return None, 0
    data = load_json(path, "Claude settings.json")
    if not isinstance(data, dict):
        raise InstallError("[install-uscha] Claude settings.json must be an object: %s" % path)
    hooks_data = data.get("hooks")
    if not isinstance(hooks_data, dict):
        return None, 0
    groups = hooks_data.get("PreToolUse")
    if not isinstance(groups, list):
        return None, 0
    removed = 0
    new_groups = []
    for group in groups:
        if not isinstance(group, dict):
            new_groups.append(group); continue
        items = group.get("hooks")
        if not isinstance(items, list):
            new_groups.append(group); continue
        keep = []
        for item in items:
            c = item.get("command") if isinstance(item, dict) else None
            if isinstance(c, str) and HOOK_NAME in c:
                removed += 1
            else:
                keep.append(item)
        if keep:
            g = dict(group); g["hooks"] = keep; new_groups.append(g)
        elif not items:
            new_groups.append(group)          # was already empty; not ours to prune
    if not removed:
        return None, 0
    result = dict(data)
    hooks = dict(hooks_data)
    if new_groups:
        hooks["PreToolUse"] = new_groups
    else:
        hooks.pop("PreToolUse", None)
    if hooks:
        result["hooks"] = hooks
    else:
        result.pop("hooks", None)
    return result, removed


def uninstall_target(target, home, dry_run, operations, force):
    """Remove one target. Refuses on ambiguity instead of guessing: without OUR marker there is
    no proof the files at that root are ours, and deleting a stranger's skills would be a far
    worse bug than leaving ours behind. --force overrides, and says what it assumed."""
    removed, kept = [], []
    if target == "codex":
        root = home / "plugins" / PLUGIN_NAME
        marker_path = root / "uscha-install.json"
        market_path = home / ".agents" / "plugins" / "marketplace.json"
    elif target in SKILL_ROOTS:
        root = home.joinpath(*SKILL_ROOTS[target])
        marker_path = root / "uscha-install.json"
        market_path = None
    else:
        root = home / ".claude"
        marker_path = root / "uscha-install.json"
        market_path = None

    valid, _ = marker_ok(marker_path, target)
    if not valid and not force:
        raise InstallError(
            "[install-uscha] %s: no uscha install marker at %s -- refusing to delete files this "
            "kit cannot prove it wrote. Re-run with --force if you are sure." % (target, marker_path))

    def drop(p, why):
        operations.append({"action": "remove", "path": str(p), "reason": why})
        if p.exists() or p.is_symlink():
            if not dry_run:
                remove_path(p)
            removed.append(str(p))

    if target == "codex":
        drop(root, "codex plugin tree (ours: marker verified)")
        if market_path and market_path.is_file():
            try:
                data = load_json(market_path, "marketplace.json")
                plugins = [p for p in data.get("plugins", []) if p != marketplace_entry()]
                if len(plugins) != len(data.get("plugins", [])):
                    data = dict(data); data["plugins"] = plugins
                    operations.append({"action": "edit", "path": str(market_path),
                                       "reason": "drop the uscha marketplace entry, keep the rest"})
                    if not dry_run:
                        atomic_json(market_path, data)
                    removed.append(str(market_path) + " (entry)")
                else:
                    kept.append(str(market_path) + " (no uscha entry)")
            except InstallError:
                kept.append(str(market_path) + " (unreadable, left untouched)")
    elif target in SKILL_ROOTS:
        for skill in SKILLS:
            drop(root / skill, "uscha skill")
        drop(marker_path, "install marker")
    else:
        skills_root = root / "skills"
        for skill in SKILLS:
            drop(skills_root / skill, "uscha skill")
        drop(root / "hooks" / HOOK_NAME, "INV-GOLDEN-01 hook")
        drop(marker_path, "install marker")
        settings_path = root / "settings.json"
        try:
            new_settings, n = settings_without_hook(settings_path)
        except InstallError:
            new_settings, n = None, 0
            kept.append(str(settings_path) + " (unreadable, left untouched)")
        if n:
            operations.append({"action": "edit", "path": str(settings_path),
                               "reason": "drop %d uscha PreToolUse entry(ies), keep foreign hooks" % n})
            if not dry_run:
                atomic_json(settings_path, new_settings)
            removed.append(str(settings_path) + " (%d hook entry)" % n)
        else:
            kept.append(str(settings_path) + " (no uscha hook entry)")
    return {"removed": removed, "kept": kept}


def cmd_uninstall(args):
    home, operations, result = home_path(args), [], {}
    for target in selected_targets(args.target):
        result[target] = uninstall_target(target, home, args.dry_run, operations, args.force)
    emit({"status": "planned" if args.dry_run else "uninstalled", "dry_run": args.dry_run,
          "home": str(home), "targets": result, "operations": operations,
          "next": ["Run: python install-uscha.py doctor --target %s" % args.target,
                   "Your own files were left alone: only paths this kit wrote are removed."]},
         args.json)


def next_steps(target):
    picked = selected_targets(target)   # resolves both/all so each installed target speaks
    steps = []
    if "codex" in picked: steps.append("Codex: restart or open a new thread, then install/use uscha from the Personal marketplace if needed.")
    if "claude" in picked: steps.append("Claude: restart Claude Code so global skills/hooks are reloaded.")
    labels = {"pi": "pi (Earendil)", "cursor": "Cursor", "copilot": "VS Code / GitHub Copilot",
              "gemini": "Gemini CLI", "cline": "Cline"}
    for name in SKILL_ROOTS:
        if name in picked:
            steps.append("%s: restart it; the 9 uscha-* skills load from ~/%s. INV-GOLDEN-01 is "
                         "advisory there (no blocking pre-tool hook) -- doctor reports golden_guard."
                         % (labels.get(name, name), "/".join(SKILL_ROOTS[name])))
    return steps + ["Run: python install-uscha.py doctor --target %s" % target,
                    "Learn the method: https://uscha.dev"]


def emit(data, as_json):
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False)); return
    # uninstall also reports per-target, but with removed/kept instead of health -- match on
    # the SHAPE, not just the key name, or a payload that merely has "targets" crashes here.
    if data.get("status") in ("uninstalled", "planned") and isinstance(data.get("targets"), dict):
        print("Uscha uninstall%s" % ("  (dry-run: nothing was touched)" if data.get("dry_run") else ""))
        for name, res in data["targets"].items():
            print("  %-8s removed %d, left alone %d" % (name, len(res.get("removed", [])), len(res.get("kept", []))))
        for k in res.get("kept", []) if data["targets"] else []:
            print("     kept: %s" % k)
    elif ("targets" in data and isinstance(data["targets"], dict)
            and all(isinstance(v, dict) and "healthy" in v for v in data["targets"].values())):
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
    install.add_argument("--target", choices=list(TARGETS) + ["both", "all"], default="both"); install.add_argument("--mode", choices=["copy", "link"], default="copy"); install.add_argument("--home"); install.add_argument("--dry-run", action="store_true"); install.add_argument("--json", action="store_true"); install.set_defaults(func=cmd_install)
    doctor = sub.add_parser("doctor", help="check installed Uscha presence, registrations, and version drift")
    doctor.add_argument("--target", choices=list(TARGETS) + ["both", "all"], default="both"); doctor.add_argument("--home"); doctor.add_argument("--json", action="store_true"); doctor.set_defaults(func=cmd_doctor)
    init = sub.add_parser("init", help="prepare a repo with Uscha config/templates")
    init.add_argument("--repo", default="."); init.add_argument("--force", action="store_true", help="replace differing init files deliberately"); init.add_argument("--dry-run", action="store_true"); init.add_argument("--json", action="store_true"); init.set_defaults(func=cmd_init)
    uninstall = sub.add_parser("uninstall", help="remove what this kit installed, and nothing else")
    uninstall.add_argument("--target", choices=list(TARGETS) + ["both", "all"], default="both")
    uninstall.add_argument("--home"); uninstall.add_argument("--dry-run", action="store_true")
    uninstall.add_argument("--json", action="store_true")
    uninstall.add_argument("--force", action="store_true",
                           help="remove even without an install marker (you assert the files are ours)")
    uninstall.set_defaults(func=cmd_uninstall)
    mirador = sub.add_parser("mirador", help="render + open the project's mirador dashboard from QA-LEDGER.json")
    mirador.add_argument("--ledger", default="QA-LEDGER.json", help="ledger to read (default: the QA-LEDGER.json convention)")
    mirador.add_argument("--out", default="mirador.html")
    mirador.add_argument("--watch", action="store_true", help="live second-screen view: re-render every --interval seconds")
    mirador.add_argument("--interval", type=int, default=30)
    mirador.add_argument("--no-open", action="store_true", help="write the file but do not open a browser")
    mirador.add_argument("--open", dest="force_open", action="store_true",
                         help="open the browser even if mirador.html already existed (you closed the tab)")
    mirador.set_defaults(func=cmd_mirador)
    top = sub.add_parser("top", help="live terminal board of the project's obligations, read from QA-LEDGER.json")
    top.add_argument("--ledger", default="QA-LEDGER.json", help="ledger to read (default: the QA-LEDGER.json convention)")
    top.add_argument("--once", action="store_true", help="print one plain frame and exit (implied without a TTY)")
    top.add_argument("--refresh", type=float, default=2.0, help="seconds between mtime polls of the ledger (default: 2, floor 0.5); `r` still forces a re-read")
    top.add_argument("--human", default=None, help="who is at the keyboard: the name recorded on every verdict this session writes (default: $USERNAME/$USER, then `curate`'s own default)")
    top.add_argument("--json", action="store_true", help="print the engine's read-only `top --json` contract instead of rendering it")
    top.set_defaults(func=cmd_top)
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
