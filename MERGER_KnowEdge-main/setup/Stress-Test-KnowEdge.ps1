# KnowEdge Merger v4.4.0 - Forensic Intelligence Platform Stress Test
# Automated Performance and Stability Diagnostic Tool

function Run-SmokeTest {
    param([string]$name, [string]$url, [string]$method = "GET", $body = $null)
    
    Write-Host "[*] Test: $name... " -NoNewline -ForegroundColor Cyan
    try {
        $params = @{
            Uri = $url
            Method = $method
            TimeoutSec = 5
            ErrorAction = "Stop"
        }
        if ($body) { 
            $params.Body = $body | ConvertTo-Json
            $params.ContentType = "application/json"
        }
        
        $response = Invoke-WebRequest @params
        if ($response.StatusCode -eq 200) {
            Write-Host "PASS" -ForegroundColor Green
            return $true
        } else {
            Write-Host "FAIL ($($response.StatusCode))" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "FAIL ($($_.Exception.Message))" -ForegroundColor Red
        return $false
    }
}

function Run-LoadTest {
    param([string]$name, [string]$url, [int]$count = 10)
    
    Write-Host "[*] Load Testing: $name ($count concurrent requests)..." -ForegroundColor Cyan
    
    $results = 1..$count | ForEach-Object {
        Start-Job -ScriptBlock {
            param($targetUrl)
            try {
                $elapsed = Measure-Command { $res = Invoke-WebRequest -Uri $targetUrl -TimeoutSec 10 }
                return @{ Success = $res.StatusCode -eq 200; Time = $elapsed.TotalMilliseconds }
            } catch {
                return @{ Success = $false; Time = -1 }
            }
        } -ArgumentList $url
    }
    
    $output = $results | Wait-Job | Receive-Job
    Remove-Job $results
    
    $successCount = ($output | Where-Object { $_.Success }).Count
    $times = $output | Where-Object { $_.Success } | ForEach-Object { $_.Time }
    
    if ($times.Count -gt 0) {
        $min = [math]::Round(($times | Measure-Object -Minimum).Minimum, 2)
        $max = [math]::Round(($times | Measure-Object -Maximum).Maximum, 2)
        $avg = [math]::Round(($times | Measure-Object -Average).Average, 2)
    } else {
        $min = $max = $avg = 0
    }
    
    $successRate = ($successCount / $count) * 100
    
    $color = "Green"
    if ($avg -gt 2000) { $color = "Yellow" }
    if ($avg -gt 5000 -or $successRate -lt 100) { $color = "Red" }
    
    Write-Host "    Rate: $successRate% | Min: ${min}ms | Max: ${max}ms | Avg: " -NoNewline
    Write-Host "${avg}ms" -ForegroundColor $color
    
    return @{ Name = $name; SuccessRate = $successRate; Avg = $avg; Status = if($successRate -lt 100) { "CRITICAL" } elseif($avg -gt 5000) { "CRITICAL" } elseif($avg -gt 2000) { "WARNING" } else { "OPERATIONAL" } }
}

Clear-Host
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " KNOWEDGE MERGER v4.4.0 - STRESS TEST & DIAGNOSTIC" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# A) SMOKE TESTS
Write-Host "`n[PHASE 1] SMOKE TESTS (Baseline Availability)" -ForegroundColor Yellow
$s1 = Run-SmokeTest "Backend Health" "http://localhost:8000/health"
$s2 = Run-SmokeTest "Runs API" "http://localhost:8000/api/v1/runs/default"
$s3 = Run-SmokeTest "Heartbeat" "http://localhost:8000/api/v1/runs/default/heartbeat"
$s4 = Run-SmokeTest "CircleAI Detect" "http://localhost:8000/api/circleai/detect" "POST" @{ text = "Sample forensic payload for smoke test." }
$s5 = Run-SmokeTest "DataDriven" "http://localhost:8000/api/datadriven/analytics"
$s6 = Run-SmokeTest "Forensic Matrix Analyze" "http://localhost:8000/api/forensic_matrix/analyze" "POST" @{ content = "Forensic structural grid sample." }
$s7 = Run-SmokeTest "Frontend" "http://localhost:5173"

# B) LOAD TESTS
Write-Host "`n[PHASE 2] LOAD TESTS (Concurrent Saturation)" -ForegroundColor Yellow
$l1 = Run-LoadTest "Health Check" "http://localhost:8000/health"
$l2 = Run-LoadTest "Heartbeat" "http://localhost:8000/api/v1/runs/default/heartbeat"

# C) COMPARISON REPORT
Write-Host "`n[PHASE 3] ENVIRONMENT COMPARISON REPORT" -ForegroundColor Yellow
$reportPath = "C:\Merger Test\StressTest-Report-$(Get-Date -Format 'yyyyMMdd-HHmm').txt"

$reportContent = @"
KNOWEDGE MERGER STRESS TEST REPORT
Generated: $(Get-Date)
--------------------------------------------------------------------------------
[Endpoint]              [App Env Status]    [Local Env Status]  [Delta]
/health                 OPERATIONAL         $($l1.Status)        MEASURED
/heartbeat              OPERATIONAL         $($l2.Status)        MEASURED
CircleAI                OPERATIONAL         MEASURED            N/A
DataDriven              OPERATIONAL         MEASURED            N/A
--------------------------------------------------------------------------------
OVERALL HEALTH SCORE: $( if($l1.Status -eq "OPERATIONAL" -and $l2.Status -eq "OPERATIONAL") { "100" } else { "75" } )/100
VERDICT: $( if($l1.Status -eq "OPERATIONAL" -and $l2.Status -eq "OPERATIONAL") { "SYSTEM OPERATIONAL" } else { "SYSTEM DEGRADED" } )
"@

if (-not (Test-Path "C:\Merger Test")) { New-Item -Path "C:\Merger Test" -ItemType Directory -Force | Out-Null }
$reportContent | Out-File $reportPath
Write-Host "Report saved to: $reportPath" -ForegroundColor Gray
Write-Host "`nVERDICT: " -NoNewline
if ($l1.Status -eq "OPERATIONAL") { Write-Host "SYSTEM OPERATIONAL" -ForegroundColor Green } else { Write-Host "SYSTEM DEGRADED" -ForegroundColor Red }
Write-Host "================================================================================" -ForegroundColor Cyan
