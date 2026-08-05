$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$port = if ($args.Count -gt 0) { $args[0] } else { "8000" }

Set-Location $root
python -m http.server $port --bind 127.0.0.1
