# Cross-platform PowerShell shim for scripts/run_experiment.py
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptDir\run_experiment.py" @args
