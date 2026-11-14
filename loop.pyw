"""Grimsby's brain loop without a console window. Task Scheduler starts this with .venv\Scripts\pythonw.exe at
log-on (and every hour as a watchdog; a second copy exits at once because of the lock in drive/live/.lock).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)

from drive.run import main  # noqa: E402

sys.exit(main())
