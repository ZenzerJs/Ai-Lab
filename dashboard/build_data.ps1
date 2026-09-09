# Cross-platform PowerShell shim for dashboard/build_data.py
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptDir\build_data.py" @args
