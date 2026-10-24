param(
    [string]$ArduinoCli = 'arduino-cli'
)

$ErrorActionPreference = 'Stop'
$indexUrl = 'https://raw.githubusercontent.com/DeqingSun/ch55xduino/ch55xduino/package_ch55xduino_mcs51_index.json'
$version = '0.0.25'
$platform = Join-Path $env:LOCALAPPDATA "Arduino15\packages\CH55xDuino\hardware\mcs51\$version"
$example = Join-Path $platform 'libraries\Generic_Examples\examples\05.USB\qmkCompatibleKeyboard\src\userQmkCompatibleKeyboard'

if (-not (Test-Path -LiteralPath $example)) {
    throw "CH55xDuino $version is missing. Run: $ArduinoCli core install CH55xDuino:mcs51@$version --additional-urls $indexUrl"
}

$stage = Join-Path $env:TEMP ("keypad-open-build-" + [guid]::NewGuid().ToString('N'))
$sketch = Join-Path $stage 'KeypadOpen'
$dependency = Join-Path $sketch 'src\userQmkCompatibleKeyboard'
New-Item -ItemType Directory -Path $dependency -Force | Out-Null
Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'KeypadOpen') -File | Copy-Item -Destination $sketch
Get-ChildItem -LiteralPath $example -File | Where-Object Name -NotIn @('via.c', 'via.h') | Copy-Item -Destination $dependency
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'KeypadOpen\via.h') -Destination $dependency
$descriptorPath = Join-Path $dependency 'USBconstant.c'
$descriptor = Get-Content -LiteralPath $descriptorPath -Raw
$updatedDescriptor = $descriptor.Replace('0x91, 0x83, // OUTPUT', '0x91, 0x02, // OUTPUT')
if ($updatedDescriptor -eq $descriptor) {
    throw 'Unexpected CH55xDuino Raw HID descriptor; refusing to build.'
}
$consumerDescriptor = @'
    ,0x05, 0x0c, 0x09, 0x01, 0xa1, 0x01,
    0x85, 0x03, 0x15, 0x00, 0x26, 0xff, 0x00,
    0x75, 0x10, 0x95, 0x01, 0x09, 0x00,
    0x19, 0x00, 0x2a, 0xff, 0x00,
    0x81, 0x00, 0xc0,
'@
$marker = '                // //todo: add media control'
if (-not $updatedDescriptor.Contains($marker)) { throw 'Unexpected keyboard descriptor; refusing to add consumer report.' }
$updatedDescriptor = $updatedDescriptor.Replace($marker, $consumerDescriptor)
$productPattern = '(?s)__code uint16_t ProductDescriptor\[\] = \{.*?\};'
$manufacturerPattern = '(?s)__code uint16_t ManufacturerDescriptor\[\] = \{.*?\};'
if ([regex]::Matches($updatedDescriptor, $productPattern).Count -ne 1 -or
    [regex]::Matches($updatedDescriptor, $manufacturerPattern).Count -ne 1 -or
    -not [regex]::IsMatch([regex]::Match($updatedDescriptor, $productPattern).Value, "'C'\s*,\s*'H'\s*,\s*'5'\s*,\s*'5'\s*,\s*'x'\s*,\s*'d'") -or
    -not [regex]::Match($updatedDescriptor, $manufacturerPattern).Value.Contains("'D', 'e', 'q', 'i', 'n', 'g'")) {
    throw 'Unexpected CH55xDuino USB strings; refusing to build.'
}
$product = "__code uint16_t ProductDescriptor[] = {`n    (((10 + 1) * 2) | (DTYPE_String << 8)),`n    'K', 'e', 'y', 'p', 'a', 'd', 'O', 'p', 'e', 'n',`n};"
$manufacturer = "__code uint16_t ManufacturerDescriptor[] = {`n    (((18 + 1) * 2) | (DTYPE_String << 8)),`n    'K', 'e', 'y', 'p', 'a', 'd', 'O', 'p', 'e', 'n', ' ',`n    'P', 'r', 'o', 'j', 'e', 'c', 't',`n};"
$updatedDescriptor = [regex]::Replace($updatedDescriptor, $productPattern, $product)
$updatedDescriptor = [regex]::Replace($updatedDescriptor, $manufacturerPattern, $manufacturer)
[System.IO.File]::WriteAllText($descriptorPath, $updatedDescriptor)

$transportPath = Join-Path $dependency 'USBHIDKeyboardMouse.c'
$transport = Get-Content -LiteralPath $transportPath -Raw
$transportMarker = '  } else if (reportID == 8) {'
if (-not $transport.Contains($transportMarker)) { throw 'Unexpected USB transport; refusing to add consumer report.' }
$transport = $transport.Replace($transportMarker, @'
  } else if (reportID == 3) {
    Ep1Buffer[64] = 3;
    Ep1Buffer[65] = consumerUsage;
    Ep1Buffer[66] = 0;
    UEP1_T_LEN = 3;
  } else if (reportID == 8) {
'@)
$transport = $transport.Replace('__xdata uint8_t keyboardLedStatus = 0;', @'
__xdata uint8_t keyboardLedStatus = 0;
__data uint8_t consumerUsage = 0;
'@)
$transport += @'

void Consumer_pulse(uint8_t usage) {
  consumerUsage = usage;
  USB_EP1_send(3);
  consumerUsage = 0;
  USB_EP1_send(3);
}
'@
[System.IO.File]::WriteAllText($transportPath, $transport)

$output = Join-Path $PSScriptRoot 'build'
New-Item -ItemType Directory -Path $output -Force | Out-Null
& $ArduinoCli compile --fqbn 'CH55xDuino:mcs51:ch552:clock=24internal,usb_settings=user266,bootloader_pin=p36,upload_method=usb' --additional-urls $indexUrl --output-dir $output $sketch
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Built firmware in $output. No device was flashed."
