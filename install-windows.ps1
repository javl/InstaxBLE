# Sets up the InstaxBLE tray launcher on Windows:
#   - creates a virtual environment (winvenv) and installs the dependencies
#   - adds an "Instax Printer" Start menu shortcut
#   - optionally turns on start at login
#
# Run from PowerShell, inside this folder:   .\install-windows.ps1 [-NoAutostart]
# Use a normal Windows folder (e.g. C:\Users\you\InstaxBLE), not \\wsl$\..., so the
# launcher still works at login before WSL has started.
param([switch]$NoAutostart)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if ($root -like '\\*') {
    Write-Warning "This folder is on a network path ($root). The launcher will not work at login until WSL is running. Copy the repo to a Windows folder and run this again."
}

if (-not (Test-Path "$root\winvenv\Scripts\python.exe")) {
    python -m venv "$root\winvenv"
}
& "$root\winvenv\Scripts\python.exe" -m pip install -r "$root\requirements.txt"

$pythonw = "$root\winvenv\Scripts\pythonw.exe"
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Programs')) 'Instax Printer.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = "`"$root\tray.py`""
$shortcut.WorkingDirectory = $root
$shortcut.Description = 'Instax Printer web GUI'
$shortcut.Save()
Write-Host "Created Start menu shortcut: $shortcutPath"

if (-not $NoAutostart) {
    & "$root\winvenv\Scripts\python.exe" "$root\tray.py" --set-autostart on
    Write-Host 'Start at login: on (toggle it from the tray icon menu)'
}
Write-Host 'Done. Search for "Instax Printer" in the Start menu to launch it.'
