#!/usr/bin/env pwsh
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$PSScriptRoot\lint_frontmatter.py" @args
exit $LASTEXITCODE
