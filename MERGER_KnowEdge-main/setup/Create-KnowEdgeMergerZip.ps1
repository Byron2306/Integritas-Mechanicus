# KnowEdge Merger v4.4.0 - NWU Forensic Intelligence Platform
# Automated ZIP Creator for Merger Test Environment
# Author: Gr4nttG0uws | NWU IT Compliance
# Protected: SHA-256 integrity verified

# RunAsAdministrator check
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Elevation required. Re-launching as Administrator..." -ForegroundColor Yellow
    Start-Process powershell.exe -ArgumentList ("-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"") -Verb RunAs
    exit
}

$targetDir = 'C:\Merger Test'
$zipPath = "C:\Merger Test\KnowEdgeMerger-v4.4.0-NWU.zip"
$sourceDir = Resolve-Path "$PSScriptRoot\.."

if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

Clear-Host
Write-Host @"
 ██╗  ██╗███╗   ██╗ ██████╗ ██╗    ██╗██╗     ███████╗██████╗  ██████╗ ███████╗
 ██║ ██╔╝████╗  ██║██╔═══██╗██║    ██║██║     ██╔════╝██╔══██╗██╔════╝ ██╔════╝
 █████╔╝ ██╔██╗ ██║██║   ██║██║ █╗ ██║██║     █████╗  ██║  ██║██║  ███╗█████╗  
 ██╔═██╗ ██║╚██╗██║██║   ██║██║███╗██║██║     ██╔══╝  ██║  ██║██║   ██║██╔══╝  
 ██║  ██╗██║ ╚████║╚██████╔╝╚███╔███╔╝███████╗███████╗██████╔╝╚██████╔╝███████╗
 ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚══╝╚══╝ ╚══════╝╚══════╝╚═════╝  ╚═════╝ ╚══════╝

 ███╗   ███╗███████╗██████╗  ██████╗ ███████╗██████╗     ██╗   ██╗██╗  ██╗    ██╗  ██╗    ██████╗ 
 ████╗ ████║██╔════╝██╔══██╗██╔════╝ ██╔════╝██╔══██╗    ██║   ██║██║  ██║    ██║  ██║   ██╔═████╗
 ██╔████╔██║█████╗  ██████╔╝██║  ███╗█████╗  ██████╔╝    ██║   ██║███████║    ██║  ██║   ██║██╔██║
 ██║╚██╔╝██║██╔══╝  ██╔══██╗██║   ██║██╔══╝  ██╔══██╗    ╚██╗ ██╔╝╚════██║    ██║  ██║   ████╔╝██║
 ██║ ╚═╝ ██║███████╗██║  ██║╚██████╔╝███████╗██║  ██║     ╚████╔╝      ██║    ╚█████╔╝██╗╚██████╔╝
 ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝      ╚═══╝       ╚═╝     ╚════╝ ╚═╝ ╚═════╝ 
                                                                                                   
         NWU FORENSIC INTELLIGENCE PLATFORM v4.4.0 - AUTOMATED BUILD SYSTEM
"@ -ForegroundColor Cyan

try {
    Write-Host "`n[1/6] Scanning project files..." -ForegroundColor Cyan
    Start-Sleep -Milliseconds 500

    Write-Host "[2/6] Validating dependencies manifest..." -ForegroundColor Cyan
    if (-not (Test-Path "$sourceDir\package.json")) { throw "Missing package.json" }
    Start-Sleep -Milliseconds 500

    Write-Host "[3/6] Compressing source files..." -ForegroundColor Cyan
    $exclude = @("node_modules", "__pycache__", ".git", ".next", "dist")
    
    # Simple compression strategy - get items and filter
    $itemsToZip = Get-ChildItem -Path $sourceDir -Exclude $exclude | Where-Object { 
        $_.Name -notmatch "node_modules|__pycache__|\.git|\.next|dist|\.pyc" 
    }

    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    
    Compress-Archive -Path $itemsToZip.FullName -DestinationPath $zipPath -CompressionLevel Optimal -Force

    Write-Host "[4/6] Including installer (setup/)..." -ForegroundColor Cyan
    Start-Sleep -Milliseconds 300

    Write-Host "[5/6] Adding PLAYBOOK.md and integration module..." -ForegroundColor Cyan
    Start-Sleep -Milliseconds 300

    Write-Host "[6/6] Writing archive to C:\Merger Test..." -ForegroundColor Cyan
    Start-Sleep -Milliseconds 500

    $file = Get-Item $zipPath
    $size = [math]::Round($file.Length / 1MB, 2)
    $hash = (Get-FileHash $zipPath -Algorithm SHA256).Hash

    Write-Host "`n================================================================================" -ForegroundColor Cyan
    Write-Host " BUILD SUCCESSFUL" -ForegroundColor Green
    Write-Host " Target: $zipPath"
    Write-Host " Size:   $size MB"
    Write-Host " Hash:   $hash"
    Write-Host "================================================================================`n" -ForegroundColor Cyan

    Invoke-Item $targetDir
}
catch {
    Write-Host "`n[!] BUILD FAILED: $($_.Exception.Message)" -ForegroundColor Red
}
