param([Parameter(Mandatory=$true)][string]$InputPath,[Parameter(Mandatory=$true)][string]$OutputPath,
      [ValidateSet('QuadrantProcessor','ExcessInventoryProcessor','ExpediteProcessor')][string]$Processor='QuadrantProcessor',
      [ValidateSet('parent','child','git')][string]$Direction='parent')
$ErrorActionPreference='Stop'
$vfEvidenceRoot=[System.IO.Path]::GetFullPath('D:/freshvcf-build/evidence/')
$vfInput=[System.IO.Path]::GetFullPath($InputPath)
$vfOutput=[System.IO.Path]::GetFullPath($OutputPath)
if (-not $vfInput.StartsWith($vfEvidenceRoot,[System.StringComparison]::OrdinalIgnoreCase) -or
    -not $vfOutput.StartsWith($vfEvidenceRoot,[System.StringComparison]::OrdinalIgnoreCase) -or
    [System.IO.File]::Exists($vfOutput)) { throw 'Explicit new evidence output required' }
$vfDll='F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll'
$vfSha=(Get-FileHash -LiteralPath $vfDll -Algorithm SHA256).Hash.ToLowerInvariant()
if ($vfSha -ne '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346') { throw 'Canonical DLL differs' }
$vfValues=Get-Content -LiteralPath $vfInput -Raw | ConvertFrom-Json -AsHashtable
$vfMvc='F:/VFlow_Local/local-config/dotnet/shared/Microsoft.AspNetCore.App/6.0.36/Microsoft.AspNetCore.Mvc.Core.dll'
# GetResponse's model graph references MVC. Resolve the installed canonical
# framework assembly without launching or changing its application host.
[void][System.Reflection.Assembly]::LoadFrom($vfMvc)
$vfAssembly=[System.Reflection.Assembly]::LoadFrom($vfDll)
$vfType=$vfAssembly.GetType('VectorFlowAPIs.VectorFlow.Processors.Replenishment.InsightsAndTrends.'+$Processor,$true)
if ($Direction -eq 'git' -and $Processor -ne 'ExpediteProcessor') { throw 'GIT response belongs to ExpediteProcessor' }
$vfMethodName=if ($Processor -eq 'ExpediteProcessor') {
    switch ($Direction) { 'parent' { 'GetParentResponse' } 'child' { 'GetChildResponse' } 'git' { 'GetGoodsInTransitResponse' } }
} else { 'GetResponse' }
$vfMethod=$vfType.GetMethod($vfMethodName)
$vfParameters=New-Object object[] ($vfMethod.GetParameters().Count)
$vfParameters[0]=[System.Data.DataSet]::new()
foreach ($vfTableInput in $vfValues.tables) {
    $vfTable=[System.Data.DataTable]::new()
    foreach ($vfColumn in $vfTableInput.columns) {
        $vfColumnType=switch ($vfColumn.type) { 'int32' { [int] } 'int64' { [long] } 'decimal' { [decimal] } 'string' { [string] } default { throw 'Unknown SQL column type' } }
        [void]$vfTable.Columns.Add($vfColumn.name,$vfColumnType)
    }
    foreach ($vfSource in $vfTableInput.rows) {
        $vfRow=$vfTable.NewRow()
        foreach ($vfColumn in $vfTableInput.columns) {
            $vfValue=$vfSource[$vfColumn.name]
            $vfRow[$vfColumn.name]=if ($null -eq $vfValue) { [DBNull]::Value } else { $vfValue }
        }
        [void]$vfTable.Rows.Add($vfRow)
    }
    [void]$vfParameters[0].Tables.Add($vfTable)
}
foreach ($vfIndex in 1..($vfParameters.Count-1)) {
    $vfParameters[$vfIndex]=[Activator]::CreateInstance($vfMethod.GetParameters()[$vfIndex].ParameterType)
    $vfPrefix=if ($vfIndex -eq 1) { 'll' } else { 'sl' }
    foreach ($vfLevel in 1..5) {
        $vfConfig=[Activator]::CreateInstance($vfAssembly.GetType('VectorFlowAPIs.VectorFlow.Models.UiConfigAttr',$true))
        $vfConfig.header=$vfPrefix.ToUpperInvariant()+$vfLevel
        $vfConfig.colCode=$vfPrefix+$vfLevel
        [void]$vfParameters[$vfIndex].Add($vfConfig)
    }
}
$vfInstance=if ($vfMethod.IsStatic) { $null } else { [Activator]::CreateInstance($vfType) }
$vfResponse=$vfMethod.Invoke($vfInstance,$vfParameters)
$vfJsonOptions=[System.Text.Json.JsonSerializerOptions]::new([System.Text.Json.JsonSerializerDefaults]::Web)
$vfWire=[System.Text.Json.JsonSerializer]::Serialize($vfResponse,$vfResponse.GetType(),$vfJsonOptions) | ConvertFrom-Json -AsHashtable
$vfResult=[ordered]@{assembly_sha256=$vfSha;method=$vfMethod.ToString();
    mvc_sha256=(Get-FileHash -LiteralPath $vfMvc -Algorithm SHA256).Hash.ToLowerInvariant();
    processor=$Processor;serializer='System.Text.Json / web defaults (deployed AddControllers has no JSON override)';
    runtime=[System.Runtime.InteropServices.RuntimeInformation]::FrameworkDescription;
    culture=[System.Globalization.CultureInfo]::CurrentCulture.Name;
    input_sha256=(Get-FileHash -LiteralPath $vfInput -Algorithm SHA256).Hash.ToLowerInvariant();
    response=$vfWire}
[System.IO.File]::WriteAllText($vfOutput,($vfResult | ConvertTo-Json -Depth 30),[System.Text.UTF8Encoding]::new($false))
Write-Output ('Canonical GetResponse invocation saved: '+$vfOutput)
