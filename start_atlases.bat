@echo off
cd /d "%~dp0"
py -3 scripts\serve_atlases.py
if errorlevel 1 pause
