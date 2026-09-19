$ErrorActionPreference = 'Stop'

$archive = Join-Path $PSScriptRoot 'CampusMeet-win32-x64.zip'
$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\CampusMeet'
$stagingRoot = "$installRoot.new"
$backupRoot = "$installRoot.old"

Get-Process CampusMeet -ErrorAction SilentlyContinue | Stop-Process -Force
foreach ($path in @($stagingRoot, $backupRoot)) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}

New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null
Expand-Archive -LiteralPath $archive -DestinationPath $stagingRoot -Force

if (Test-Path -LiteralPath $installRoot) {
    Move-Item -LiteralPath $installRoot -Destination $backupRoot
}
Move-Item -LiteralPath $stagingRoot -Destination $installRoot
if (Test-Path -LiteralPath $backupRoot) {
    Remove-Item -LiteralPath $backupRoot -Recurse -Force
}

$executable = Join-Path $installRoot 'CampusMeet.exe'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'CampusMeet.lnk'))
$shortcut.TargetPath = $executable
$shortcut.WorkingDirectory = $installRoot
$shortcut.IconLocation = "$executable,0"
$shortcut.Save()

Start-Process -FilePath $executable
