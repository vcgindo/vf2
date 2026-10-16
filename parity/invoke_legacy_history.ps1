param([Parameter(Mandatory=$true)][string]$InputPath,[Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
$vfRoot=[System.IO.Path]::GetFullPath('D:/freshvcf-build/evidence/')
$vfInput=[System.IO.Path]::GetFullPath($InputPath)
$vfOutput=[System.IO.Path]::GetFullPath($OutputPath)
if (-not $vfInput.StartsWith($vfRoot,[StringComparison]::OrdinalIgnoreCase) -or
    -not $vfOutput.StartsWith($vfRoot,[StringComparison]::OrdinalIgnoreCase) -or [IO.File]::Exists($vfOutput)) { throw 'New owned evidence output required' }
$vfDll='F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll'
$vfHash=(Get-FileHash $vfDll).Hash.ToLowerInvariant()
if ($vfHash -ne '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346') { throw 'Canonical DLL changed' }
$vfValues=Get-Content -LiteralPath $vfInput -Raw | ConvertFrom-Json -AsHashtable
$vfAssembly=[Reflection.Assembly]::LoadFrom($vfDll)
$vfType=$vfAssembly.GetType('VectorFlowAPIs.VectorFlow.Processors.Replenishment.SCIH.SCIHProcessor',$true)
$vfList=[Collections.Generic.List[Collections.Generic.Dictionary[string,string]]]::new()
foreach ($vfPair in $vfValues.selected) {
    $vfRow=[Collections.Generic.Dictionary[string,string]]::new()
    $vfRow.Add('SKUCode',$vfPair.SKUCode); $vfRow.Add('WhCode',$vfPair.WhCode); $vfList.Add($vfRow)
}
$vfParameters=New-Object object[] 2
$vfParameters[0]=$vfList; $vfParameters[1]=[string]$vfValues.auth
$vfQuery=$vfType.GetMethod('GetResearchInsightDataQuery').Invoke($null,$vfParameters)
function Get-VFPercentage([int]$Value,[int]$Total) {
    if ($Total -eq 0) { return '0' }
    return [Math]::Round(([decimal]::Parse($Value.ToString())/[decimal]$Total)*[decimal]100,2).ToString()
}
$vfColours=@('B','R','Y','G','BU','W'); $vfGraphs=@{}
foreach ($vfCase in $vfValues.graphs.Keys) {
    $vfCaseData=$vfValues.graphs[$vfCase]; $vfAbs=@(); $vfRelative=@(); $vfTotals=@{}
    foreach ($vfColour in $vfColours) { $vfTotals[$vfColour]=[int]0 }
    foreach ($vfRow in $vfCaseData.counts) {
        $vfDate=([datetime]::Parse($vfCaseData.labels[0][$vfRow.D])).ToString('dd-MM-yyyy')
        $vfAbsolute=@{dt=$vfDate}; $vfPercentage=@{dt=$vfDate}; $vfTotal=[int]0
        foreach ($vfColour in $vfColours) {
            $vfCount=if ($null -eq $vfRow[$vfColour]) { [int]0 } else { [int]$vfRow[$vfColour] }
            $vfAbsolute[$vfColour.ToLowerInvariant()]=$vfCount.ToString()
            $vfTotals[$vfColour]=[int]($vfTotals[$vfColour]+$vfCount); $vfTotal=[int]($vfTotal+$vfCount)
        }
        foreach ($vfColour in $vfColours) { $vfPercentage[$vfColour.ToLowerInvariant()]=Get-VFPercentage ([int]$vfRow[$vfColour]) $vfTotal }
        $vfAbs+=,$vfAbsolute; $vfRelative+=,$vfPercentage
    }
    $vfTotal=[int]0; foreach ($vfColour in $vfColours) { $vfTotal=[int]($vfTotal+$vfTotals[$vfColour]) }
    $vfSumA=@{category='Absolute Value'}; $vfSumP=@{category='Percentage'}
    foreach ($vfColour in $vfColours) {
        $vfSumA['sum'+$vfColour]=$vfTotals[$vfColour].ToString()
        $vfSumP['sum'+$vfColour]=Get-VFPercentage $vfTotals[$vfColour] $vfTotal
    }
    $vfGraphs[$vfCase]=@{absolute=$vfAbs;percentage=$vfRelative;summary=@($vfSumA,$vfSumP);avail=(Get-VFPercentage ($vfTotal-$vfTotals.B) $vfTotal)}
}
$vfHistory=@{}
foreach ($vfStart in @(1,31,61)) {
    $vfEnd=$vfStart+29; $vfTotal=[int]0; $vfBlack=[int]0
    foreach ($vfRow in $vfValues.availability[($vfStart-1)..($vfEnd-1)]) {
        foreach ($vfColour in $vfColours) { $vfTotal=[int]($vfTotal+[int]$vfRow[$vfColour]) }
        $vfBlack=[int]($vfBlack+[int]$vfRow.B)
    }
    $vfHistory[('availability_{0:00}_{1}' -f $vfStart,$vfEnd)]=[double](Get-VFPercentage ($vfTotal-$vfBlack) $vfTotal)
}
$vfOptions=[System.Text.Json.JsonSerializerOptions]::new([System.Text.Json.JsonSerializerDefaults]::Web)
$vfHistoryWire=[System.Text.Json.JsonSerializer]::Serialize($vfHistory,$vfHistory.GetType(),$vfOptions) | ConvertFrom-Json -AsHashtable
$vfResult=@{assembly_sha256=$vfHash;research_query=[string]$vfQuery;graphs=$vfGraphs;availability=@($vfHistoryWire);
    runtime=[Runtime.InteropServices.RuntimeInformation]::FrameworkDescription;culture=[Globalization.CultureInfo]::CurrentCulture.Name;
    input_sha256=(Get-FileHash $vfInput).Hash.ToLowerInvariant();
    qualification='Actual DLL research query builder; graph/history response math is a source transcription executed on .NET decimal, not invocation of the DB-coupled processor or legacy HTTP host'}
[IO.File]::WriteAllText($vfOutput,($vfResult | ConvertTo-Json -Depth 60),[Text.UTF8Encoding]::new($false))
Write-Output 'Canonical query and independent .NET response formatting saved'
