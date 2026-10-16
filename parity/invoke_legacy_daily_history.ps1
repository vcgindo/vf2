param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
$vfRoot=[System.IO.Path]::GetFullPath('D:/freshvcf-build/evidence/')
$vfOutput=[System.IO.Path]::GetFullPath($OutputPath)
if (-not $vfOutput.StartsWith($vfRoot,[System.StringComparison]::OrdinalIgnoreCase) -or [System.IO.File]::Exists($vfOutput)) {
    throw 'Explicit new evidence output required'
}
$vfDll='F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll'
$vfHash=(Get-FileHash -LiteralPath $vfDll -Algorithm SHA256).Hash.ToLowerInvariant()
if ($vfHash -ne '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346') { throw 'Canonical DLL changed' }
$vfAssembly=[System.Reflection.Assembly]::LoadFrom($vfDll)
$vfType=$vfAssembly.GetType('VectorFlowAPIs.VectorFlow.Processors.BORProcessor',$true)
$vfInstance=[Activator]::CreateInstance($vfType)
$vfMethods=@(
    @('GetDailyDataQryForDDG',3),@('GetNormChangeHistoryQryForDDG',3),
    @('GetMasterDataQryForDDG',2),@('GetMonitoringDateQryForDDG',2),
    @('GetNormChangeHistoryQryForDDG',2),@('GetSuggestionHistoryQryForDDG',3),@('GetRunDate',0)
)
$vfFragments=@()
foreach ($vfSpec in $vfMethods) {
    $vfMethod=@($vfType.GetMethods() | Where-Object { $_.Name -eq $vfSpec[0] -and $_.GetParameters().Count -eq $vfSpec[1] })
    if ($vfMethod.Count -ne 1) { throw 'Canonical method roster changed' }
    $vfArgs=New-Object object[] ([int]$vfSpec[1])
    if ($vfArgs.Count -ge 2) { $vfArgs[0]='__FRESH_SKU__'; $vfArgs[1]='__FRESH_LOC__' }
    if ($vfArgs.Count -eq 3) { $vfArgs[2]=[int]90 }
    $vfFragments+=@{method=$vfMethod[0].ToString();sql=[string]$vfMethod[0].Invoke($vfInstance,$vfArgs)}
}
$vfResult=[ordered]@{assembly_sha256=$vfHash;processor=$vfType.FullName;
    runtime=[System.Runtime.InteropServices.RuntimeInformation]::FrameworkDescription;fragments=$vfFragments;
    qualification='Actual DLL query builders only; no SQL execution, application host or serving mutation'}
[System.IO.File]::WriteAllText($vfOutput,($vfResult | ConvertTo-Json -Depth 12),[System.Text.UTF8Encoding]::new($false))
Write-Output 'Canonical daily-history query builders exported'
