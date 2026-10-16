param([Parameter(Mandatory=$true)][string]$InputPath,[Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
$vfRoot=[IO.Path]::GetFullPath('D:/freshvcf-build/evidence/')
$vfInput=[IO.Path]::GetFullPath($InputPath)
$vfOutput=[IO.Path]::GetFullPath($OutputPath)
if (-not $vfInput.StartsWith($vfRoot,[StringComparison]::OrdinalIgnoreCase) -or
    -not $vfOutput.StartsWith($vfRoot,[StringComparison]::OrdinalIgnoreCase) -or
    [IO.File]::Exists($vfOutput)) { throw 'Owned input and new evidence output required' }
$vfDll='F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll'
$vfSha=(Get-FileHash $vfDll).Hash.ToLowerInvariant()
if ($vfSha -ne '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346') { throw 'Canonical DLL changed' }
$vfNewton='F:/VFlow_Local/local-runtime/mta-latest/Newtonsoft.Json.dll'
[void][Reflection.Assembly]::LoadFrom($vfNewton)
$vfInputValue=Get-Content -LiteralPath $vfInput -Raw | ConvertFrom-Json -AsHashtable
$vfResults=@{}
foreach ($vfEntry in $vfInputValue.observations.GetEnumerator()) {
    if ($vfEntry.Value.status -ne 'EXECUTED') { continue }
    $vfSections=@{}
    for ($vfIndex=0; $vfIndex -lt $vfEntry.Value.columns.Count; $vfIndex++) {
        $vfText=$vfEntry.Value.rows[0][$vfIndex]
        $vfRows=[Collections.Generic.List[Collections.Generic.Dictionary[string,string]]]::new()
        if ($null -ne $vfText -and $vfText -ne '') {
            $vfRows=[Newtonsoft.Json.JsonConvert]::DeserializeObject($vfText,$vfRows.GetType())
        }
        $vfSections[$vfEntry.Value.columns[$vfIndex]]=$vfRows
    }
    $vfResults[$vfEntry.Key]=$vfSections
}
$vfResult=@{assembly_sha256=$vfSha;newtonsoft_sha256=(Get-FileHash $vfNewton).Hash.ToLowerInvariant();
    runtime=[Runtime.InteropServices.RuntimeInformation]::FrameworkDescription;
    input_sha256=(Get-FileHash $vfInput).Hash.ToLowerInvariant();observations=$vfResults;
    qualification='Exact source List<Dictionary<string,string>> conversion using deployed Newtonsoft dependency; not invocation of hosted Planning endpoint'}
[IO.File]::WriteAllText($vfOutput,($vfResult | ConvertTo-Json -Depth 60),[Text.UTF8Encoding]::new($false))
