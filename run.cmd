@echo off
rem Run Grimsby's brain with his own venv. Example: run --no-git --action draw
"%~dp0.venv\Scripts\python.exe" "%~dp0brain.py" %*
