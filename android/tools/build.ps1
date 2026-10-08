param([string]$SdkPath, [string]$JavaHome, [string]$GradleExecutable)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
if ($JavaHome) { $env:JAVA_HOME = $JavaHome }
if (-not $env:JAVA_HOME) {
    $installedJdk = 'C:\Program Files\Java\jdk-17'
    if (Test-Path -LiteralPath $installedJdk) { $env:JAVA_HOME = $installedJdk }
    else { throw 'Set JAVA_HOME to JDK 17 or pass -JavaHome.' }
}
if ($SdkPath) {
    $resolvedSdk = (Resolve-Path -LiteralPath $SdkPath).Path.Replace('\', '/').Replace(':', '\:')
    Set-Content -LiteralPath (Join-Path $projectRoot 'local.properties') -Value "sdk.dir=$resolvedSdk" -Encoding ascii
}
if (-not (Test-Path -LiteralPath 'local.properties') -and -not $env:ANDROID_HOME -and -not $env:ANDROID_SDK_ROOT) {
    throw 'Install Android SDK 36 and Build Tools 36.0.0, then pass -SdkPath.'
}
$env:GRADLE_USER_HOME = Join-Path $projectRoot '.gradle-user-home'
$env:ANDROID_USER_HOME = Join-Path $projectRoot '.tools/android-user-home'
New-Item -ItemType Directory -Force -Path $env:ANDROID_USER_HOME | Out-Null
if ($GradleExecutable) { & $GradleExecutable :app:assembleDebug :app:testDebugUnitTest :app:lintDebug --no-daemon --console=plain }
else { & (Join-Path $projectRoot 'gradlew.bat') :app:assembleDebug :app:testDebugUnitTest :app:lintDebug --no-daemon --console=plain }
if ($LASTEXITCODE -ne 0) { throw "Android build failed: $LASTEXITCODE" }
Write-Output (Join-Path $projectRoot 'app/build/outputs/apk/debug/app-debug.apk')
