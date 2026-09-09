#!/usr/bin/env pwsh
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$PSScriptRoot\repo_map.py" @args
exit $LASTEXITCODE
