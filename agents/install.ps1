# UITOP Agent installer for Windows
# Usage (on the OTHER PC, with Python installed):
#   irm http://SERVER:5500/computers/agent/install.ps1 | iex
#   Install-UitopAgent -Token 'YOUR_TOKEN' -Server 'http://SERVER:5500'
#
# Or one-liner:
#   & ([scriptblock]::Create((irm "http://SERVER:5500/computers/agent/install.ps1"))) -Token 'TOKEN' -Server 'http://SERVER:5500'

param(
    [Parameter(Mandatory = $false)]
    [string]$Token = "",

    [Parameter(Mandatory = $false)]
    [string]$Server = ""
)

function Install-UitopAgent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Token,

        [Parameter(Mandatory = $true)]
        [string]$Server,

        [switch]$Once
    )

    $Server = $Server.TrimEnd("/")
    $dir = Join-Path $env:LOCALAPPDATA "UITOP\agent"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    Write-Host "Downloading agent from $Server ..."
    $agentUrl = "$Server/computers/agent/local_agent.py"
    $agentPath = Join-Path $dir "local_agent.py"
    Invoke-WebRequest -Uri $agentUrl -OutFile $agentPath -UseBasicParsing

    Write-Host "Ensuring psutil is installed..."
    python -m pip install --quiet psutil
    if ($LASTEXITCODE -ne 0) {
        throw "Python/pip not found. Install Python 3 from https://www.python.org/downloads/ (check 'Add to PATH')."
    }

    $args = @($agentPath, "--server", $Server, "--token", $Token)
    if ($Once) { $args += "--once" }

    Write-Host "Starting UITOP agent..."
    Write-Host "  python $($args -join ' ')"
    & python @args
}

# If invoked with -Token / -Server at top level, install immediately
if ($Token -and $Server) {
    Install-UitopAgent -Token $Token -Server $Server
}
