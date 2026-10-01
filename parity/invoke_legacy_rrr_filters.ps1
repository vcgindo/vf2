param([Parameter(Mandatory=$true)][string]$InputPath,[Parameter(Mandatory=$true)][string]$OutputPath,
    [ValidateSet('RRR','BTR')][string]$Report='RRR')
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
    # Exact report alias tuple selected by GenericFunction.ApplyFiltersForReports.
    $vfParameters=New-Object object[] 9
    $vfParameters[0]=$vfFilter
    $vfAliases=if ($Report -eq 'BTR') { @('E','E','E','sa','la','sla') } else { @('a','a','a','c','d','b') }
    for ($vfIndex=0;$vfIndex -lt 6;$vfIndex++) { $vfParameters[$vfIndex+1]=$vfAliases[$vfIndex] }
    $vfParameters[7]='';$vfParameters[8]=''
    $vfMethod.Invoke($vfInstance,$vfParameters) | Out-Null
    $vfCases+=,@{id=$vfCase.id;sql_filter=[string]$vfParameters[7];sql_join_filter=[string]$vfParameters[8]}
}
$vfResult=@{assembly_sha256=$vfHash;cases=$vfCases;
    runtime=[Runtime.InteropServices.RuntimeInformation]::FrameworkDescription;
    input_sha256=(Get-FileHash $vfInput).Hash.ToLowerInvariant();
    report=$Report;authority="Actual pinned DLL filterQueryForReports invocation; exact GenericFunction $Report alias tuple; no source-transcribed filter generator"}
[IO.File]::WriteAllText($vfOutput,($vfResult | ConvertTo-Json -Depth 60),[Text.UTF8Encoding]::new($false))
Write-Output "Canonical DLL $Report filter queries saved"
