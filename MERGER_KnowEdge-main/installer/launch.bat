@echo off
title KnowEdge Merger V5.0.0 — NWU Forensic Intelligence Platform
color 0B
echo.
echo  ██╗  ██╗███╗   ██╗ ██████╗ ██╗    ██╗███████╗██████╗  ██████╗ ███████╗
echo  ██║ ██╔╝████╗  ██║██╔═══██╗██║    ██║██╔════╝██╔══██╗██╔════╝ ██╔════╝
echo  █████╔╝ ██╔██╗ ██║██║   ██║██║ █╗ ██║█████╗  ██║  ██║██║  ███╗█████╗
echo  ██╔═██╗ ██║╚██╗██║██║   ██║██║███╗██║██╔══╝  ██║  ██║██║   ██║██╔══╝
echo  ██║  ██╗██║ ╚████║╚██████╔╝╚███╔███╔╝███████╗██████╔╝╚██████╔╝███████╗
echo  ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚══╝╚══╝ ╚══════╝╚═════╝  ╚═════╝ ╚══════╝
echo.
echo  MERGER — NWU FORENSIC INTELLIGENCE PLATFORM V5.0.0
echo  ASYMMETRIC OPTIMIZATION ^& TRI-ARTIFACT SYNTHESIS
echo  NWU CERTIFIED ^| AUTHORISED PERSONNEL ONLY
echo.
echo  [BOOT] Starting Python backend...
start /B python app.py
timeout /t 3 /nobreak >nul
echo  [BOOT] Launching UI...
start http://localhost:5173
echo  [READY] KnowEdge Merger is running.
echo  [INFO] Close this window to stop the server.
pause
