@echo off
rem Run Grimsby's brain v2 loop with a console (Task Scheduler uses loop.pyw). Example: run --test --ticks 20 --fast
"%~dp0.venv\Scripts\python.exe" -m drive.run %*
