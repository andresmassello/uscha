# block-approved-writes.ps1 — PreToolUse hook (INV-GOLDEN-01).
# Forbids the agent from writing/renaming any *.approved.* golden. The golden is field
# truth, approved by a HUMAN — never authored by the agent. On the first failing diff the
# agent will try to "fix" the test by editing the golden; this makes that impossible.
#
# Wire it in settings.json:
#   "hooks": { "PreToolUse": [ { "matcher": "*", "hooks": [
#     { "type": "command",
#       "command": "powershell -NoProfile -ExecutionPolicy Bypass -File \"<path>/hooks/block-approved-writes.ps1\"" }
#   ] } ] }
# Exit 2 = block the tool call; the message on stderr is fed back to the agent.

$ErrorActionPreference = 'SilentlyContinue'
$raw = [Console]::In.ReadToEnd()
if (-not $raw) { exit 0 }
try { $data = $raw | ConvertFrom-Json } catch { exit 0 }

$tool = $data.tool_name
$block = $false
$target = ''

if ($tool -in @('Write', 'Edit', 'NotebookEdit', 'MultiEdit')) {
    $target = [string]$data.tool_input.file_path
    if ($target -match '\.approved(\.|$)') { $block = $true }
}
elseif ($tool -eq 'Bash') {
    $cmd = [string]$data.tool_input.command
    # Block ANY Bash command that references a .approved path. The old keyword
    # co-occurrence check (redirect/mv/cp/...) was bypassable via indirection —
    # python -c "open(p,'w')", a variable-built path, dd, etc. The agent has no
    # legitimate Bash reason to touch an .approved (reading goes through the Read
    # tool), so the coarse rule is safer than the clever one.
    if ($cmd -match '\.approved') {
        $block = $true
        $target = 'Bash command referencing a .approved path'
    }
}

if ($block) {
    [Console]::Error.WriteLine(
        "BLOCKED by INV-GOLDEN-01: the agent may not write or rename an .approved golden " +
        "($target). The .approved is field truth - a HUMAN approves it. Emit a .received " +
        "instead and stop for human approval.")
    exit 2
}
exit 0
