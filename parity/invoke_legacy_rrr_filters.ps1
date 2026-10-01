param([Parameter(Mandatory=$true)][string]$InputPath,[Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
$vfRoot=[IO.Path]::GetFullPath('D:/freshvcf-build/evidence/')
$vfInput=[IO.Path]::GetFullPath($InputPath)
$vfOutput=[IO.Path]::GetFullPath($OutputPath)
if (-not $vfInput.StartsWith($vfRoot,[StringComparison]::OrdinalIgnoreCase) -or
    -not $vfOutput.StartsWith($vfRoot,[StringComparison]::OrdinalIgnoreCase) -or
    [IO.File]::Exists($vfOutput)) { throw 'New owned evidence output required' }
$vfDll='F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll'
$vfHash=(Get-FileHash $vfDll).Hash.ToLowerInvariant()
if ($vfHash -ne '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346') { throw 'Canonical DLL changed' }
$vfValues=Get-Content -LiteralPath $vfInput -Raw | ConvertFrom-Json -AsHashtable
$vfAssembly=[Reflection.Assembly]::LoadFrom($vfDll)
$vfType=$vfAssembly.GetType('VectorFlowAPIs.VectorFlow.Processors.Commons.CommonsProcessor',$true)
$vfMethod=$vfType.GetMethod('filterQueryForReports')
$vfFilterType=$vfMethod.GetParameters()[0].ParameterType
$vfOptions=[System.Text.Json.JsonSerializerOptions]::new()
$vfOptions.PropertyNameCaseInsensitive=$true
$vfInstance=[Activator]::CreateInstance($vfType)
$vfCases=@()
foreach ($vfCase in $vfValues.cases) {
    $vfFilterJson=$vfCase.payload.filters | ConvertTo-Json -Depth 40 -Compress
    $vfFilter=[System.Text.Json.JsonSerializer]::Deserialize($vfFilterJson,$vfFilterType,$vfOptions)
    # Exact RRR alias tuple selected by GenericFunction.ApplyFiltersForReports.
    $vfParameters=New-Object object[] 9
    $vfParameters[0]=$vfFilter
    $vfParameters[1]='a';$vfParameters[2]='a';$vfParameters[3]='a'
    $vfParameters[4]='c';$vfParameters[5]='d';$vfParameters[6]='b'
    $vfParameters[7]='';$vfParameters[8]=''
    $vfMethod.Invoke($vfInstance,$vfParameters) | Out-Null
    $vfCases+=,@{id=$vfCase.id;sql_filter=[string]$vfParameters[7];sql_join_filter=[string]$vfParameters[8]}
}
$vfResult=@{assembly_sha256=$vfHash;cases=$vfCases;
    runtime=[Runtime.InteropServices.RuntimeInformation]::FrameworkDescription;
    input_sha256=(Get-FileHash $vfInput).Hash.ToLowerInvariant();
    authority='Actual pinned DLL filterQueryForReports invocation; exact GenericFunction RRR alias tuple; no source-transcribed filter generator'}
[IO.File]::WriteAllText($vfOutput,($vfResult | ConvertTo-Json -Depth 60),[Text.UTF8Encoding]::new($false))
Write-Output 'Canonical DLL RRR filter queries saved'
