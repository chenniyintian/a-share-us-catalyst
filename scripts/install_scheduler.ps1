$TaskName = "CatDesk9-Morning-Report"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Resolve-Path "$ScriptDir\.."
$BatPath = "$ScriptDir\run_report.bat"
$LogDir = "$ProjectDir\logs"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$Action = New-ScheduledTaskAction -Execute "cmd.exe" `
    -Argument "/c `"$BatPath`" > `"$LogDir\task.log`" 2>&1" `
    -WorkingDirectory $ProjectDir

$Trigger = New-ScheduledTaskTrigger -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 09:00

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -RestartCount 1 `
    -MultipleInstances IgnoreNew

$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "CatDesk9 daily morning report with email push"

Write-Host "Scheduled task installed: $TaskName"
Write-Host "Run: Mon-Fri 09:00"
Write-Host "Script: $BatPath"
Write-Host "Log: $LogDir\task.log"
Write-Host ""
Write-Host "Commands:"
Write-Host "  query:  schtasks /tn `"$TaskName`" /query /fo LIST /v"
Write-Host "  run:    schtasks /tn `"$TaskName`" /run"
Write-Host "  delete: schtasks /tn `"$TaskName`" /delete /f"
