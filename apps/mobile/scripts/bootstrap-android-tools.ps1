param(
    [string]$JavaHome = "D:\develop\Java\jdk-25"
)

$ErrorActionPreference = "Stop"
$mobileRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$toolsRoot = "C:\Users\Public\CampusMeetAndroid"
$sdkRoot = Join-Path $toolsRoot "android-sdk"
$downloads = Join-Path $toolsRoot "downloads"
$gradleRoot = Join-Path $toolsRoot "gradle-9.1.0"
$commandToolsZip = Join-Path $downloads "commandlinetools-win-15859902_latest.zip"
$gradleZip = Join-Path $downloads "gradle-9.1.0-bin.zip"

if (-not (Test-Path -LiteralPath (Join-Path $JavaHome "bin\java.exe"))) {
    throw "JDK not found at $JavaHome"
}

New-Item -ItemType Directory -Force $downloads, $sdkRoot | Out-Null
if (-not $toolsRoot.StartsWith("C:\Users\Public\CampusMeetAndroid", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Unsafe Android tools cache path."
}

function Get-VerifiedDownload {
    param(
        [string]$Uri,
        [string]$Destination,
        [string]$ExpectedSha256 = ""
    )
    if (Test-Path -LiteralPath $Destination) {
        $existingIsValid = (Get-Item -LiteralPath $Destination).Length -gt 0
        if ($existingIsValid -and $ExpectedSha256) {
            $existingHash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant()
            $existingIsValid = $existingHash -eq $ExpectedSha256.ToLowerInvariant()
        }
        if (-not $existingIsValid) {
            Remove-Item -LiteralPath $Destination -Force
        }
    }
    if (-not (Test-Path -LiteralPath $Destination)) {
        & curl.exe --location --fail --retry 3 --retry-delay 2 --output $Destination $Uri
        if ($LASTEXITCODE -ne 0) {
            throw "Download failed: $Uri"
        }
    }
    if ($ExpectedSha256) {
        $actual = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $ExpectedSha256.ToLowerInvariant()) {
            throw "Checksum mismatch for $Destination"
        }
    }
}

Get-VerifiedDownload `
    -Uri "https://dl.google.com/android/repository/commandlinetools-win-15859902_latest.zip" `
    -Destination $commandToolsZip `
    -ExpectedSha256 "90ae805d20434428bffcb699c290860f19bb5f66a67e6b330067e3de801fb04a"

if (-not (Test-Path -LiteralPath (Join-Path $sdkRoot "cmdline-tools\latest\bin\sdkmanager.bat"))) {
    $extractRoot = Join-Path $toolsRoot "command-tools-extract"
    if (Test-Path -LiteralPath $extractRoot) {
        Remove-Item -LiteralPath $extractRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force $extractRoot | Out-Null
    & tar.exe -xf $commandToolsZip -C $extractRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Android command-line tools extraction failed."
    }
    $latestRoot = Join-Path $sdkRoot "cmdline-tools\latest"
    New-Item -ItemType Directory -Force $latestRoot | Out-Null
    Copy-Item -Path (Join-Path $extractRoot "cmdline-tools\*") -Destination $latestRoot -Recurse -Force
}

Get-VerifiedDownload `
    -Uri "https://services.gradle.org/distributions/gradle-9.1.0-bin.zip" `
    -Destination $gradleZip

if (-not (Test-Path -LiteralPath (Join-Path $gradleRoot "bin\gradle.bat"))) {
    & tar.exe -xf $gradleZip -C $toolsRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Gradle extraction failed."
    }
}

$env:JAVA_HOME = $JavaHome
$env:ANDROID_HOME = $sdkRoot
$env:ANDROID_SDK_ROOT = $sdkRoot
$sdkManager = Join-Path $sdkRoot "cmdline-tools\latest\bin\sdkmanager.bat"
$licenseAnswers = ("y" + [Environment]::NewLine) * 30
$licenseAnswers | & $sdkManager --sdk_root=$sdkRoot --licenses | Out-Host
& $sdkManager --sdk_root=$sdkRoot "platforms;android-36" "build-tools;36.0.0" "platform-tools"
if ($LASTEXITCODE -ne 0) {
    throw "Android SDK package installation failed."
}

$sdkProperty = $sdkRoot.Replace("\", "/")
"sdk.dir=$sdkProperty" | Set-Content -LiteralPath (Join-Path $mobileRoot "local.properties") -Encoding Ascii

[PSCustomObject]@{
    JavaHome = $JavaHome
    AndroidSdk = $sdkRoot
    Gradle = Join-Path $gradleRoot "bin\gradle.bat"
}
