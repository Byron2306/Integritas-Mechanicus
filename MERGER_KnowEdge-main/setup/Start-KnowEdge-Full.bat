@echo off
title KnowEdge Merger - Full System
start "Backend" cmd /k "cd /d %~dp0.. && .venv\Scripts\activate && python app.py"
timeout /t 3
start "Frontend" cmd /k "cd /d %~dp0.. && npm run dev"
timeout /t 2
start http://localhost:5173
