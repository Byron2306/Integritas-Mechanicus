@echo off
title KnowEdge Merger - Backend Server
cd /d %~dp0..
call .venv\Scripts\activate
echo Starting KnowEdge Merger Backend on port 8000...
python app.py
