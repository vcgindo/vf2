param([Parameter(Mandatory=$true)][string]$InputPath,[Parameter(Mandatory=$true)][string]$OutputPath,
    [ValidateSet('RRR','BTR','DBM','BufferTrends','ExcessGrid','ExcessCount')][string]$Report='RRR')
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
if ($Report -in @('DBM','BufferTrends','ExcessGrid','ExcessCount')) {
    # DBMProcessor.GetDBMData's filter property chooses the exact overload.
    $vfDbmType=$vfAssembly.GetType('VectorFlowAPIs.VectorFlow.Processors.DBMProcessor',$true)
    $vfRequestMethod=$vfDbmType.GetMethod('GetDBMData')
    if ($Report -eq 'BufferTrends') {
        $vfRequestMethod=$vfAssembly.GetType('VectorFlowAPIs.VectorFlow.Processors.Replenishment.SCIH.SCIHProcessor',$true).GetMethod('GetBufferGraphData')
    }
    if ($Report -in @('ExcessGrid','ExcessCount')) {
        $vfRequestMethod=$vfAssembly.GetType('VectorFlowAPIs.VectorFlow.Processors.Replenishment.SCIH.PlanningProcessor',$true).GetMethod('ReviewExcessInventory')
    }
    $vfFilterType=$vfRequestMethod.GetParameters()[0].ParameterType.GetProperty('filters').PropertyType
    $vfMethod=@($vfType.GetMethods() | Where-Object { $_.Name -eq 'filterQuery' -and
        $_.GetParameters().Count -eq 6 -and $_.GetParameters()[0].ParameterType -eq $vfFilterType })[0]
    if ($null -eq $vfMethod) { throw 'Exact deployed DBM filter overload missing' }
}
$vfOptions=[System.Text.Json.JsonSerializerOptions]::new()
$vfOptions.PropertyNameCaseInsensitive=$true
$vfInstance=[Activator]::CreateInstance($vfType)
$vfCases=@()
foreach ($vfCase in $vfValues.cases) {
    $vfFilterJson=$vfCase.payload.filters | ConvertTo-Json -Depth 40 -Compress
    $vfFilter=[System.Text.Json.JsonSerializer]::Deserialize($vfFilterJson,$vfFilterType,$vfOptions)
    if ($Report -in @('DBM','BufferTrends','ExcessGrid','ExcessCount')) {
        $vfSql='';$vfJoin=''
        $vfActive=@('availabilityFilter','supplyChainFilter','coverageFilter','productFilter','locationFilter','colorFilter') |
            Where-Object { $vfCase.payload.filters.ContainsKey($_) -and $null -ne $vfCase.payload.filters[$_] }
        if (@($vfActive).Count -gt 0) {
            $vfParameters=New-Object object[] 6
            $vfParameters[0]=$vfFilter;$vfParameters[1]='e';$vfParameters[2]='i';$vfParameters[3]='f'
            if ($Report -in @('BufferTrends','ExcessGrid','ExcessCount')) {
                $vfParameters[1]='sa';$vfParameters[2]='la';$vfParameters[3]='sla'
            }
            $vfParameters[4]='';$vfParameters[5]=''
            $vfMethod.Invoke($vfInstance,$vfParameters) | Out-Null
            $vfSql=[string]$vfParameters[4];$vfJoin=[string]$vfParameters[5]
            if ($Report -eq 'DBM') {
                $vfSql=$vfSql.Replace('a.ParentWhCode','b.ParentWhCode')
                $vfJoin=$vfJoin.Replace('a.ParentWhCode','b.ParentWhCode')
            }
            if ($Report -in @('ExcessGrid','ExcessCount')) {
                $vfSql=$vfSql.Replace('pic','a.PipelineInventoryColor').Replace('ohic','a.PhysicalInventoryColor')
                if ($Report -eq 'ExcessGrid') {
                    $vfSql=$vfSql.Replace('tags','a.tags').Replace('Git','a.git').Replace(' Norm',' a.Norm').Replace('Stock','a.Stock')
                }
            }
        }
    } else {
        # Exact report alias tuple selected by GenericFunction.ApplyFiltersForReports.
        $vfParameters=New-Object object[] 9
        $vfParameters[0]=$vfFilter
        $vfAliases=if ($Report -eq 'BTR') { @('E','E','E','sa','la','sla') } else { @('a','a','a','c','d','b') }
        for ($vfIndex=0;$vfIndex -lt 6;$vfIndex++) { $vfParameters[$vfIndex+1]=$vfAliases[$vfIndex] }
        $vfParameters[7]='';$vfParameters[8]=''
        $vfMethod.Invoke($vfInstance,$vfParameters) | Out-Null
        $vfSql=[string]$vfParameters[7];$vfJoin=[string]$vfParameters[8]
    }
    $vfCases+=,@{id=$vfCase.id;sql_filter=$vfSql;sql_join_filter=$vfJoin}
}
$vfResult=@{assembly_sha256=$vfHash;cases=$vfCases;
    runtime=[Runtime.InteropServices.RuntimeInformation]::FrameworkDescription;
    input_sha256=(Get-FileHash $vfInput).Hash.ToLowerInvariant();
    report=$Report;authority="Actual pinned DLL Commons filter invocation; exact deployed $Report alias/call gate; no source-transcribed filter generator"}
[IO.File]::WriteAllText($vfOutput,($vfResult | ConvertTo-Json -Depth 60),[Text.UTF8Encoding]::new($false))
Write-Output "Canonical DLL $Report filter queries saved"
