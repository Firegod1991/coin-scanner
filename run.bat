@echo off
cd /d "%~dp0"
".venv\Scripts\pythonw.exe" -m scanner
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m scanner
  pause
)

