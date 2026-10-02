# Cross-platform PowerShell shim for scripts/campaign.py
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptDir\campaign.py" @args
