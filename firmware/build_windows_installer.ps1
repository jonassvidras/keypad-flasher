param(
    [string]$Python = 'py',
    [string]$PythonVersion = '-3'
)

$ErrorActionPreference = 'Stop'
$firmware = $PSScriptRoot
$imageRelative = 'release\KeypadOpen-v2.hex'
$image = Join-Path $firmware $imageRelative
$digest = (Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLowerInvariant()
$expected = '631c148775cec49ad15d1b5c2ae9d164493c9ff42332eb0aa6210d0e39fd8da5'
if ($digest -ne $expected) {
    throw 'Firmware image differs from the pinned build. Packaging stopped.'
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$packageName = 'KeypadOpenInstaller'
$output = Join-Path $firmware "dist\$packageName-$stamp"
$outputPath = [System.IO.Path]::GetFullPath($output)
$distPath = [System.IO.Path]::GetFullPath((Join-Path $firmware 'dist'))
if (-not $outputPath.StartsWith($distPath + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Build output must remain within firmware/dist.'
}
$work = Join-Path $env:TEMP "keypad-installer-work-$stamp"
$venv = Join-Path $env:TEMP 'keypad-installer-pyinstaller-6.22.3'
$venvPython = Join-Path $venv 'Scripts\python.exe'
if (Test-Path -LiteralPath $output) {
    throw "Output already exists: $output"
}
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $Python $PythonVersion -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create isolated Python environment.' }
}
& $venvPython -m pip install --disable-pip-version-check 'pyinstaller==6.22.3' 'pyinstaller-hooks-contrib==2026.9'
if ($LASTEXITCODE -ne 0) { throw 'Could not install pinned PyInstaller.' }

$data = @(
    "${image}:release",
    "$(Join-Path $firmware 'flasher\index.html'):flasher",
    "$(Join-Path $firmware 'flasher\app.mjs'):flasher",
    "$(Join-Path $firmware 'flasher\style.css'):flasher",
    "$(Join-Path $firmware 'flasher\board.svg'):flasher"
)
$arguments = @(
    '-m', 'PyInstaller', '--onedir', '--console', '--contents-directory', '.',
    '--name', $packageName, '--distpath', (Join-Path $work 'dist'),
    '--workpath', (Join-Path $work 'work'), '--specpath', $work
)
foreach ($entry in $data) { $arguments += @('--add-data', $entry) }
$arguments += (Join-Path $firmware 'flasher.py')
& $venvPython @arguments
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

$built = Join-Path (Join-Path $work 'dist') $packageName
New-Item -ItemType Directory -Path (Split-Path -Parent $output) -Force | Out-Null
Move-Item -LiteralPath $built -Destination $output
Copy-Item -LiteralPath (Join-Path $firmware 'flasher\WINDOWS_PACKAGE.md') -Destination (Join-Path $output 'README.md')
Copy-Item -LiteralPath (Join-Path $firmware 'LICENSE') -Destination (Join-Path $output 'LICENSE')
Copy-Item -LiteralPath (Join-Path (Split-Path -Parent $firmware) 'THIRD_PARTY.md') -Destination (Join-Path $output 'THIRD_PARTY.md')
New-Item -ItemType Directory -Path (Join-Path $output 'LICENSES') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path (Split-Path -Parent $firmware) 'LICENSES\CH55xDuino-LGPL-2.1.txt') -Destination (Join-Path $output 'LICENSES\CH55xDuino-LGPL-2.1.txt')
Write-Host "Windows installer built at $output"
Write-Host 'wchisp.exe is not bundled. The app offers an opt-in verified download.'
