param([Parameter(Mandatory=$true)][string]$InputPath,
      [Parameter(Mandatory=$true)][string]$OutputPath,
      [ValidateSet('headers','csv')][string]$Mode)
$ErrorActionPreference='Stop'
$rrrRoot=[IO.Path]::GetFullPath('D:/freshvcf-build/evidence/')
$rrrInput=[IO.Path]::GetFullPath($InputPath)
$rrrOutput=[IO.Path]::GetFullPath($OutputPath)
if (-not $rrrInput.StartsWith($rrrRoot,[StringComparison]::OrdinalIgnoreCase) -or
    -not $rrrOutput.StartsWith($rrrRoot,[StringComparison]::OrdinalIgnoreCase) -or
    [IO.File]::Exists($rrrOutput)) { throw 'New owned output required' }
$rrrDll='F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll'
$rrrHash=(Get-FileHash $rrrDll).Hash.ToLowerInvariant()
if ($rrrHash -ne '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346') { throw 'Canonical DLL changed' }
$rrrValues=Get-Content -LiteralPath $rrrInput -Raw | ConvertFrom-Json -AsHashtable
$rrrResults=@()
if ($Mode -eq 'headers') {
    $rrrAssembly=[Reflection.Assembly]::LoadFrom($rrrDll)
    $rrrStartup=$rrrAssembly.GetType('VectorFlowAPIs.Startup',$true)
    foreach ($rrrName in @('BPRServerName','BTRServerName')) {
        $rrrStartup.GetField($rrrName).SetValue($null, 'VFTEST_BINDING')
    }
    $rrrType=$rrrAssembly.GetType('VectorFlowAPIs.VectorFlow.Processors.BORProcessor',$true)
    $rrrMethod=$rrrType.GetMethod('BuildHeaderQuery')
    $rrrRequestType=$rrrMethod.GetParameters()[0].ParameterType
    $rrrInstance=[Activator]::CreateInstance($rrrType)
    $rrrOptions=[System.Text.Json.JsonSerializerOptions]::new()
    $rrrOptions.PropertyNameCaseInsensitive=$true
    foreach ($rrrCase in $rrrValues.cases) {
        $rrrRequest=[System.Text.Json.JsonSerializer]::Deserialize(
            ($rrrCase.payload | ConvertTo-Json -Depth 40 -Compress),$rrrRequestType,$rrrOptions)
        $rrrResults+=,@{id=$rrrCase.id;query=$rrrMethod.Invoke($rrrInstance,@($rrrRequest))}
    }
} else {
    $rrrCsvPath='F:/VFlow_Local/local-runtime/mta-latest/CsvHelper.dll'
    $rrrCsvAssembly=[Reflection.Assembly]::LoadFrom($rrrCsvPath)
    $rrrCsvType=$rrrCsvAssembly.GetType('CsvHelper.CsvWriter',$true)
    $rrrConfigType=$rrrCsvAssembly.GetType('CsvHelper.Configuration.CsvConfiguration',$true)
    $rrrWrite=@($rrrCsvType.GetMethods() | Where-Object {
        $_.Name -eq 'WriteField' -and $_.IsGenericMethod -and
        $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1
    })[0].MakeGenericMethod([object])
    foreach ($rrrCase in $rrrValues.cases) {
        $rrrStream=[IO.MemoryStream]::new()
        $rrrWriter=[IO.StreamWriter]::new($rrrStream)
        $rrrConfig=[Activator]::CreateInstance($rrrConfigType,@([Globalization.CultureInfo]::InvariantCulture))
        $rrrConfig.HasHeaderRecord=$false
        $rrrCsv=[Activator]::CreateInstance($rrrCsvType,@($rrrWriter,$rrrConfig,$true))
        foreach ($rrrRecord in $rrrCase.records) {
            foreach ($rrrCell in $rrrRecord) {
                $rrrValue=switch ($rrrCell.type) {
                    'null' { '' }
                    'decimal' { [decimal]::Parse($rrrCell.value,[Globalization.CultureInfo]::InvariantCulture) }
                    'float' { [double]::Parse($rrrCell.value,[Globalization.CultureInfo]::InvariantCulture) }
                    'bool' { [bool]$rrrCell.value }
                    'int' { [long]$rrrCell.value }
                    'str' { [string]$rrrCell.value }
                    default { throw 'Unsupported evidence type' }
                }
                $rrrWrite.Invoke($rrrCsv,@($rrrValue)) | Out-Null
            }
            $rrrCsv.NextRecord()
        }
        $rrrCsv.Flush(); $rrrWriter.Flush()
        $rrrBytes=$rrrStream.ToArray()
        $rrrResults+=,@{id=$rrrCase.id;base64=[Convert]::ToBase64String($rrrBytes)}
        $rrrCsv.Dispose(); $rrrWriter.Dispose(); $rrrStream.Dispose()
    }
}
$rrrResult=@{assembly_sha256=$rrrHash;mode=$Mode;cases=$rrrResults;
    input_sha256=(Get-FileHash $rrrInput).Hash.ToLowerInvariant();
    runtime=[Runtime.InteropServices.RuntimeInformation]::FrameworkDescription}
if ($Mode -eq 'csv') { $rrrResult.csvhelper_sha256=(Get-FileHash $rrrCsvPath).Hash.ToLowerInvariant() }
[IO.File]::WriteAllText($rrrOutput,($rrrResult | ConvertTo-Json -Depth 60),[Text.UTF8Encoding]::new($false))
Write-Output "Canonical RRR export $Mode evidence saved"
