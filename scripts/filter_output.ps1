#!/usr/bin/env pwsh
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$PSScriptRoot\filter_output.py" @args
exit $LASTEXITCODE
