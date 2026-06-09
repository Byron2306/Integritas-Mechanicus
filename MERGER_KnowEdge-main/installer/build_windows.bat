@echo off
title KnowEdge Merger — Windows Build Pipeline
color 0B
echo [BUILD] KnowEdge Merger V5.0.0 Windows Build Pipeline
echo [1/4] Installing npm dependencies...
npm install
echo [2/4] Building React app...
npm run build
echo [3/4] Build complete. dist/ folder ready.
echo [4/4] To create MSI installer, open installer/setup.iss in Inno Setup Compiler.
echo.
echo [DONE] Build pipeline complete.
pause
