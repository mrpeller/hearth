# Keep Hearth running on Windows 10 / 11.
#
#   Right-click > Run with PowerShell (it asks for administrator rights), or from an admin PowerShell:
#     .\scripts\install_service.ps1              start Hearth hidden at sign-in, open the firewall
#     .\scripts\install_service.ps1 -KeepAwake   ...and stop the laptop sleeping while it's plugged in
#     .\scripts\install_service.ps1 -Uninstall   remove all of that
param([switch]$KeepAwake, [switch]$Uninstall)
$ErrorActionPreference = "Stop"

# Firewall rules and power settings need administrator rights: relaunch elevated if needed.
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    $passOn = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"")
    if ($KeepAwake) { $passOn += "-KeepAwake" }
    if ($Uninstall) { $passOn += "-Uninstall" }
    Start-Process powershell -Verb RunAs -ArgumentList $passOn -Wait
    exit
}

$root = Split-Path -Parent $PSScriptRoot
$task = "Hearth"
$user = "$env:USERDOMAIN\$env:USERNAME"

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $task -Confirm:$false -ErrorAction SilentlyContinue
    Get-NetFirewallRule -DisplayName "Hearth*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    Write-Host "Hearth's start-up task and firewall rules are removed."
    Read-Host "Press Enter to close"
    exit
}

# 1. Start hidden whenever this user signs in, restart if it ever stops, no time limit.
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$root\start.ps1`"" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $task -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Hearth will start hidden whenever $env:USERNAME signs in."

# 2. Let the TV and phones reach Hearth (web on 8765, ad blocker on 53) on home networks.
Get-NetFirewallRule -DisplayName "Hearth*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName "Hearth web (TCP 8765)" -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow -Profile Private,Domain | Out-Null
New-NetFirewallRule -DisplayName "Hearth ad blocker (UDP 53)" -Direction Inbound -Protocol UDP -LocalPort 53 -Action Allow -Profile Private,Domain | Out-Null
$net = (Get-NetConnectionProfile | Where-Object { $_.IPv4Connectivity -ne "Disconnected" } | Select-Object -First 1)
if ($net -and $net.NetworkCategory -eq "Public") {
    Write-Host "Your Wi-Fi is set to 'Public', which blocks the TV. Setting '$($net.Name)' to Private..."
    Set-NetConnectionProfile -InterfaceIndex $net.InterfaceIndex -NetworkCategory Private
}
Write-Host "Firewall opened for the TV and phones on your home network."

# 3. Optional: never sleep while plugged in, and keep running with the lid closed.
if ($KeepAwake) {
    powercfg /change standby-timeout-ac 0
    powercfg /change hibernate-timeout-ac 0
    powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
    powercfg /setactive SCHEME_CURRENT
    Write-Host "This laptop now stays awake while plugged in, even with the lid closed (on battery it sleeps as usual)."
}

Start-ScheduledTask -TaskName $task
Write-Host "Hearth is starting. Open http://localhost:8765 to check."
Read-Host "Press Enter to close"
