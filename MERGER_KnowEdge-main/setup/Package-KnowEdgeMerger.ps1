# KnowEdge Merger Packaging Script — V4.3.2
# This script creates a production-ready deployment ZIP.

# 0. Admin Check & Elevation
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[Elevation] Requesting Administrator privileges..." -ForegroundColor Cyan
    Start-Process powershell -Verb RunAs -ArgumentList "-File `"$PSCommandPath`""
    exit
}

# --- UI FUNCTIONS ---

function Show-Header {
    Clear-Host
    Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║         KNOWEDGE MERGER — PACKAGING ENGINE V4.3.2       ║" -ForegroundColor Cyan
    Write-Host "║              Building your Distribution Bundle           ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host "  Preparing deployment artifacts for NWU distribution. Please wait." -ForegroundColor Gray
    Write-Host ""
}

function Show-Progress {
    param([int]$step, [int]$total, [string]$label, [int]$percent)
    
    $width = 40
    $filled = [math]::Floor(($percent / 100) * $width)
    $empty = $width - $filled
    
    $bar = ("█" * $filled) + ("░" * $empty)
    
    $color = "Green"
    if ($percent -gt 80) { $color = "Yellow" }
    elseif ($percent -gt 50) { $color = "Cyan" }
    
    $stepText = "Step $step of $total"
    $progressLine = "`r  $stepText | [$bar] $percent%  $label"
    
    Write-Host $progressLine -NoNewline -ForegroundColor $color
}

function Show-InfoBox {
    param([string]$tip)
    Write-Host "`n"
    Write-Host "  ┌─────────────────────────────────────────────────────────┐" -ForegroundColor Gray
    $wrappedTip = $tip
    if ($tip.Length -gt 55) { $wrappedTip = $tip.Substring(0, 52) + "..." }
    $padding = 57 - $wrappedTip.Length
    $padStr = " " * ($padding / 2)
    Write-Host "  │ $padStr$wrappedTip$padStr │" -ForegroundColor Gray
    Write-Host "  └─────────────────────────────────────────────────────────┘" -ForegroundColor Gray
    Write-Host -NoNewline "$([char]27)[3A" 
}

# --- SETUP ---

$source = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
if ($PSCommandPath.Contains("setup")) {
    $source = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
} else {
    $source = Split-Path -Parent $PSCommandPath
}
if (-not $source) { $source = Get-Location }

Show-Header

$staging = "$env:TEMP\KnowEdgeMerger-Package"
Write-Host "  [System] Prepared staging at $staging" -ForegroundColor Gray
Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory $staging | Out-Null

$packTips = @(
    'Copying your AI source files...',
    'Bundling the Python intelligence engine...',
    'Packaging the one-click setup scripts...',
    'Adding documentation and playbook...',
    'Compressing everything into your deploy ZIP...'
)

$steps = @(
    @{ Label = "Migrating Frontend Core"; Job = {
        param($s, $t)
        Copy-Item "$s\src" -Destination "$t\src" -Recurse -Force
        Copy-Item "$s\public" -Destination "$t\public" -Recurse -Force
        Copy-Item "$s\index.html" -Destination "$t\" -Force
        Copy-Item "$s\package.json" -Destination "$t\" -Force
        Copy-Item "$s\tsconfig.json" -Destination "$t\" -Force
        Copy-Item "$s\vite.config.ts" -Destination "$t\" -Force
    }},
    @{ Label = "Migrating Backend Core"; Job = {
        param($s, $t)
        Copy-Item "$s\app.py" -Destination "$t\" -Force
        Copy-Item "$s\server.ts" -Destination "$t\" -Force
        Copy-Item "$s\requirements.txt" -Destination "$t\" -Force
    }},
    @{ Label = "Migrating Setup Scripts"; Job = {
        param($s, $t)
        Copy-Item "$s\setup" -Destination "$t\setup" -Recurse -Force
    }},
    @{ Label = "Migrating Documentation"; Job = {
        param($s, $t)
        Copy-Item "$s\MASTER_PLAYBOOK.md" -Destination "$t\" -Force
        Copy-Item "$s\README.md" -Destination "$t\" -Force
        Copy-Item "$s\.env.example" -Destination "$t\" -Force
        Copy-Item "$s\docker-compose.yml" -Destination "$t\" -Force
        Copy-Item "$s\firebase-applet-config.json" -Destination "$t\" -Force
        Copy-Item "$s\firestore.rules" -Destination "$t\" -Force
        Copy-Item "$s\metadata.json" -Destination "$t\" -Force
    }}
)

for ($i=0; $i -lt $steps.Count; $i++) {
    $currentStep = $i + 1
    $totalSteps = 6
    $stepInfo = $steps[$i]
    
    $job = Start-Job -ScriptBlock $stepInfo.Job -ArgumentList $source, $staging
    $startTime = Get-Date
    
    while ($job.State -eq 'Running') {
        $elapsed = (New-TimeSpan -Start $startTime -End (Get-Date)).TotalSeconds
        $p = [math]::Min(95, [math]::Floor(($elapsed / 5) * 100)) # Expected 5s copy
        Show-Progress -step $currentStep -total $totalSteps -label $stepInfo.Label -percent $p
        Show-InfoBox -tip $packTips[$i]
        Start-Sleep -Milliseconds 500
    }
    Receive-Job -Job $job | Out-Null
    Show-Progress -step $currentStep -total $totalSteps -label ($stepInfo.Label + " ✓") -percent 100
    Write-Host "`n"
}

# Step 5: Finalize Staged Files
Show-Progress -step 5 -total 6 -label "Generating Batch Runners..." -percent 50
$startBat = "@echo off`necho Starting KnowEdge Merger...`nstart `"`" `"http://localhost:3000`"`ncd /d `"%~dp0`"`npython app.py`npause"
$startBat | Out-File -FilePath "$staging\start.bat" -Encoding ascii

$readmeFirst = @"
===== KNOWEDGE MERGER =====
Thank you for installing KnowEdge Merger.

FIRST TIME SETUP:
1. Right-click 'install-mistral-vibe.ps1' in the setup folder
2. Choose 'Run with PowerShell'
3. Follow the on-screen steps (takes 10-20 min first time — downloading AI model)
4. After setup completes, double-click 'start.bat' to launch the app

EVERY DAY AFTER THAT:
Just double-click 'start.bat'

Need help? See MASTER_PLAYBOOK.md
"@
$readmeFirst | Out-File -FilePath "$staging\README-FIRST.txt" -Encoding ascii
Show-Progress -step 5 -total 6 -label "Generating Batch Runners ✓" -percent 100
Write-Host "`n"

# Step 6: Create Archive
$dest = "C:\KnowEdgeMerger-Deploy.zip"
$zipJob = Start-Job -ArgumentList $staging, $dest {
    param($s, $d)
    if (Test-Path $d) { Remove-Item $d -Force }
    Compress-Archive -Path "$s\*" -DestinationPath "$d" -Force
}

while ($zipJob.State -eq 'Running') {
    # Simple time-based for zip (est 10s)
    Show-Progress -step 6 -total 6 -label "Compressing ZIP Bundle..." -percent 75
    Show-InfoBox -tip $packTips[4]
    Start-Sleep -Seconds 1
}
Receive-Job -Job $zipJob | Out-Null
Show-Progress -step 6 -total 6 -label "Compressing ZIP Bundle ✓" -percent 100
Write-Host "`n"

# Final Screen
Clear-Host
if (Test-Path $dest) {
    $zipSize = (Get-Item $dest).Length / 1MB
    Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║   ✅  PACKAGING COMPLETE!                               ║" -ForegroundColor Green
    Write-Host "║                                                          ║" -ForegroundColor White
    Write-Host "║   Package: $dest                  " -ForegroundColor Cyan
    Write-Host "║   Size: $([math]::Round($zipSize,1)) MB                                   " -ForegroundColor White
    Write-Host "║                                                          ║" -ForegroundColor White
    Write-Host "║   Copy this ZIP to any machine for deployment.           ║" -ForegroundColor White
    Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
}

Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
Start-Process explorer.exe "C:\"
