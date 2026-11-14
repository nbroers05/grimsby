# Replaces the hourly "Grimsby brain" task (old brain.py) with "Grimsby loop": starts loop.pyw at log-on, and
# every hour as a watchdog (if the loop is already running, the new copy exits at once). No time limit.
$root = Split-Path -Parent $PSScriptRoot
$pyw  = Join-Path $root ".venv\Scripts\pythonw.exe"
$user = "$env:USERDOMAIN\$env:USERNAME"
$action   = New-ScheduledTaskAction -Execute $pyw -Argument "`"$(Join-Path $root 'loop.pyw')`"" -WorkingDirectory $root
$logon    = New-ScheduledTaskTrigger -AtLogOn -User $user
$hourly   = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Hours 1)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
            -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "Grimsby loop" -Action $action -Trigger @($logon, $hourly) -Settings $settings `
    -Description "Grimsby's brain v2 (drive/): a tick every 90 s while the PC is on." -Force | Out-Null
Disable-ScheduledTask -TaskName "Grimsby brain" -ErrorAction SilentlyContinue | Out-Null
Start-ScheduledTask -TaskName "Grimsby loop"
Get-ScheduledTask -TaskName "Grimsby loop", "Grimsby brain" | Select-Object TaskName, State
