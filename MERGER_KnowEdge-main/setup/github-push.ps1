# KnowEdge Merger GitHub Initial Push Script — V4.3.2
# This script initializes a local git repo and pushes it to a private GitHub repository.

Write-Host "--- KnowEdge Merger GitHub Sync V4.3.2 ---" -ForegroundColor White

# 1. Dependency Checks
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[Git] Missing. Installing via winget..." -ForegroundColor Yellow
    winget install Git.Git -e --silent
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "[GH CLI] Missing. Installing via winget..." -ForegroundColor Yellow
    winget install GitHub.cli -e --silent
}

# 2. Authentication
Write-Host "[Auth] Re-authenticating with GitHub..." -ForegroundColor Cyan
gh auth login --web

# 3. Git Init
if (-not (Test-Path ".git")) {
    Write-Host "[Git] Initializing repository..." -ForegroundColor Cyan
    git init
    git branch -M main
}

# 4. Add & Commit
Write-Host "[Git] Staging files..." -ForegroundColor Cyan
git add -A
git commit -m "KnowEdge Merger V4.3.2-THREADED — Initial private repository push"

# 5. Remote & Push
Write-Host "[GitHub] Creating private repository and pushing..." -ForegroundColor Cyan
try {
    gh repo create knowedge-merger --private --source=. --push --description "KnowEdge Merger V4.3.2 — NWU Academic Integrity & AI Forensics Platform"
} catch {
    Write-Host "[Alert] Repo might already exist or push failed. Checking remote..." -ForegroundColor Yellow
    if (-not (git remote get-url origin -ErrorAction SilentlyContinue)) {
        gh repo set-default knowedge-merger
    }
    git push -u origin main
}

Write-Host ""
Write-Host "[SUCCESS] Repository synchronized with GitHub." -ForegroundColor Green
gh repo view --web
