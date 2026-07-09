# mirador-watch.ps1 -- live second-screen mirador (uscha-kit 1.34.0), Windows.
# Regenerates mirador.html every N seconds from the current ledger; the page is rendered
# with a meta-refresh at the same interval, so a browser open on it updates on its own.
#
# Usage (run in a spare terminal, from the project root):
#   powershell -NoProfile -File <kit>\.claude\skills\uscha-mirador\mirador-watch.ps1 [-Interval 30]
# then open mirador.html in a browser on your second screen. Ctrl-C to stop.
#
# Overridable via env: ENGINE, LEDGER, TEMPLATE, OUT, PYTHON.
param([int]$Interval = 30)
$here     = Split-Path -Parent $MyInvocation.MyCommand.Path
$engine   = if ($env:ENGINE)   { $env:ENGINE }   else { Join-Path $here "..\uscha-devloop\qa_ledger.py" }
$ledger   = if ($env:LEDGER)   { $env:LEDGER }   else { "QA-LEDGER.json" }
$template = if ($env:TEMPLATE) { $env:TEMPLATE } else { Join-Path $here "mirador.template.html" }
$out      = if ($env:OUT)      { $env:OUT }      else { "mirador.html" }
$py       = if ($env:PYTHON)   { $env:PYTHON }   else { "python" }
Write-Host "mirador-watch: regenerating $out every ${Interval}s (Ctrl-C to stop). Open $out in a browser."
while ($true) {
  & $py (Join-Path $here "mirador-render.py") --engine $engine --ledger $ledger --template $template --out $out --refresh $Interval
  if ($LASTEXITCODE -ne 0) { Write-Host "mirador-watch: render failed (ledger missing? run uscha-devloop first) -- retrying" }
  Start-Sleep -Seconds $Interval
}
