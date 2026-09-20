param(
    [string]$ElectronVersion = '38.4.0',
    [string]$AppVersion = '1.0.0',
    [string]$NodePath = 'node'
)

$ErrorActionPreference = 'Stop'
$webRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$outputRoot = Join-Path $webRoot 'desktop-output'
$cacheRoot = Join-Path $webRoot '.desktop-cache'
$electronZip = Join-Path $cacheRoot "electron-v$ElectronVersion-win32-x64.zip"
$stageRoot = Join-Path $outputRoot 'CampusMeet-win32-x64'
$appRoot = Join-Path $stageRoot 'resources\app'
$portableZip = Join-Path $outputRoot "CampusMeet-$AppVersion-win32-x64.zip"
$installerPath = Join-Path $outputRoot "CampusMeet-$AppVersion-x64-setup.exe"

foreach ($path in @($outputRoot, $cacheRoot)) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
}
if (Test-Path -LiteralPath $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}

Push-Location $webRoot
try {
    & $NodePath 'node_modules\typescript\bin\tsc' '-b'
    if ($LASTEXITCODE -ne 0) { throw 'TypeScript build failed.' }
    $env:VITE_API_BASE_URL = ''
    & $NodePath 'node_modules\vite\bin\vite.js' 'build'
    if ($LASTEXITCODE -ne 0) { throw 'Vite build failed.' }
} finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $electronZip)) {
    $downloadUrl = "https://github.com/electron/electron/releases/download/v$ElectronVersion/electron-v$ElectronVersion-win32-x64.zip"
    Invoke-WebRequest -Uri $downloadUrl -OutFile $electronZip
}

Expand-Archive -LiteralPath $electronZip -DestinationPath $stageRoot -Force
Move-Item -LiteralPath (Join-Path $stageRoot 'electron.exe') -Destination (Join-Path $stageRoot 'CampusMeet.exe')
New-Item -ItemType Directory -Path $appRoot -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $webRoot 'desktop\main.cjs') -Destination $appRoot
Copy-Item -LiteralPath (Join-Path $webRoot 'desktop\server.cjs') -Destination $appRoot
Copy-Item -LiteralPath (Join-Path $webRoot 'desktop\package.json') -Destination $appRoot
Copy-Item -LiteralPath (Join-Path $webRoot 'public\campusmeet-mark.png') -Destination (Join-Path $appRoot 'icon.png')
Copy-Item -LiteralPath (Join-Path $webRoot 'dist') -Destination (Join-Path $appRoot 'dist') -Recurse

$defaultApp = Join-Path $stageRoot 'resources\default_app.asar'
if (Test-Path -LiteralPath $defaultApp) {
    Remove-Item -LiteralPath $defaultApp -Force
}

if (Test-Path -LiteralPath $portableZip) {
    Remove-Item -LiteralPath $portableZip -Force
}
Compress-Archive -Path (Join-Path $stageRoot '*') -DestinationPath $portableZip -CompressionLevel Optimal

$iexpressRoot = 'C:\Users\Public\CampusMeetIExpress'
$installerWork = Join-Path $iexpressRoot 'installer-work'
$iexpressTarget = Join-Path $iexpressRoot "CampusMeet-$AppVersion-x64-setup.exe"
if (-not $installerWork.StartsWith($iexpressRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Unsafe IExpress workspace path.'
}
if (Test-Path -LiteralPath $iexpressRoot) {
    Remove-Item -LiteralPath $iexpressRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $installerWork -Force | Out-Null
Copy-Item -LiteralPath $portableZip -Destination (Join-Path $installerWork 'CampusMeet-win32-x64.zip')
Copy-Item -LiteralPath (Join-Path $webRoot 'desktop\install.ps1') -Destination $installerWork

$sedPath = Join-Path $installerWork 'CampusMeet.sed'
$sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=CampusMeet installation completed.
TargetName=$iexpressTarget
FriendlyName=CampusMeet $AppVersion
AppLaunched=powershell.exe -NoProfile -ExecutionPolicy Bypass -File install.ps1
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
[SourceFiles]
SourceFiles0=$installerWork\
[SourceFiles0]
%FILE0%=CampusMeet-win32-x64.zip
%FILE1%=install.ps1
[Strings]
FILE0="CampusMeet-win32-x64.zip"
FILE1="install.ps1"
"@
$sed | Set-Content -LiteralPath $sedPath -Encoding Ascii

$iexpress = Start-Process -FilePath "$env:WINDIR\System32\iexpress.exe" -ArgumentList '/N', $sedPath -Wait -PassThru
if ($iexpress.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $iexpressTarget)) {
    throw 'Windows installer creation failed.'
}
Move-Item -LiteralPath $iexpressTarget -Destination $installerPath -Force

Get-Item -LiteralPath $installerPath, $portableZip | Select-Object FullName, Length, LastWriteTime
