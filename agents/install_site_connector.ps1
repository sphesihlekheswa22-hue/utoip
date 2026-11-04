# UITOP Site Connector installer (run on an always-on PC on the organization LAN)
#
# Usage:
#   irm https://YOUR-APP.onrender.com/network/site-connector/install.ps1 | iex
#   Install-UitopSiteConnector -Token 'enroll_xxx' -Server 'https://YOUR-APP.onrender.com' -Site 'HQ'
#
param(
    [Parameter(Mandatory = $false)]
    [string]$Token = "",

    [Parameter(Mandatory = $false)]
    [string]$Server = "",

    [Parameter(Mandatory = $false)]
    [string]$Site = ""
)

function Install-UitopSiteConnector {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Token,

        [Parameter(Mandatory = $true)]
        [string]$Server,

        [Parameter(Mandatory = $false)]
        [string]$Site = $env:COMPUTERNAME,

        [string[]]$Cidr = @(),

        [switch]$Once,

        [int]$Interval = 3600
    )

    $Server = $Server.TrimEnd("/")
    $dir = Join-Path $env:LOCALAPPDATA "UITOP\site-connector"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    Write-Host "Downloading site connector from $Server ..."
    $scriptUrl = "$Server/network/site-connector/site_connector.py"
    $scriptPath = Join-Path $dir "site_connector.py"
    Invoke-WebRequest -Uri $scriptUrl -OutFile $scriptPath -UseBasicParsing

    $pyArgs = @($scriptPath, "--server", $Server, "--token", $Token, "--site", $Site)
    foreach ($c in $Cidr) {
        $pyArgs += @("--cidr", $c)
    }
    if ($Once) {
        $pyArgs += "--once"
    } else {
        $pyArgs += @("--interval", "$Interval")
    }

    Write-Host "Starting UITOP Site Connector..."
    Write-Host "  python $($pyArgs -join ' ')"
    & python @pyArgs
}

if ($Token -and $Server) {
    Install-UitopSiteConnector -Token $Token -Server $Server -Site $(if ($Site) { $Site } else { $env:COMPUTERNAME })
}
