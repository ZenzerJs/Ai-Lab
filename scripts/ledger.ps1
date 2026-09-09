# Cross-platform PowerShell shim for scripts/ledger.py
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptDir\ledger.py" @args
