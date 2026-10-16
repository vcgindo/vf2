param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
$vfRoot=[IO.Path]::GetFullPath('D:/freshvcf-build/evidence/')
$vfOutput=[IO.Path]::GetFullPath($OutputPath)
if (-not $vfOutput.StartsWith($vfRoot,[StringComparison]::OrdinalIgnoreCase) -or
    [IO.File]::Exists($vfOutput) -or $env:VFTEST_PROFILE -ne 'fresh') { throw 'Owned new output and Fresh lease required' }
$vfDll='F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll'
$vfSha=(Get-FileHash $vfDll).Hash.ToLowerInvariant()
if ($vfSha -ne '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346') { throw 'Canonical DLL changed' }
[void][Reflection.Assembly]::LoadFrom('F:/VFlow_Local/local-runtime/mta-latest/runtimes/win/lib/netcoreapp2.1/System.Data.SqlClient.dll')
$vfAssembly=[Reflection.Assembly]::LoadFrom($vfDll)
$vfMethod=$vfAssembly.GetType('VectorFlowAPIs.Filters.GenericFunction',$true).GetMethod('GetDataSet')
$vfConnection='Server=localhost;Database=VFTEST_Fresh_BPR;Integrated Security=True;TrustServerCertificate=True;Pooling=False;Connect Timeout=10'
$vfResults=@()
foreach ($vfCase in @(@{id='valid-null';sql='SELECT CAST(NULL AS nvarchar(max)) AS expedite'},
    @{id='syntax-error';sql='SELECT 1 ORDER BY'},
    @{id='ambiguous-column';sql='SELECT norm FROM (SELECT 1 norm) a CROSS JOIN (SELECT 2 norm) b'})) {
    $vfParameters=New-Object object[] 2
    $vfParameters[0]=$vfConnection
    $vfParameters[1]="EXECUTE AS LOGIN = 'freshvcf_oracle_replay' WITH NO REVERT; "+$vfCase.sql
    $vfData=$vfMethod.Invoke($null,$vfParameters)
    $vfResults+=,@{id=$vfCase.id;type=$vfData.GetType().FullName;tables=$vfData.Tables.Count;
        row_counts=@($vfData.Tables | ForEach-Object { $_.Rows.Count })}
}
$vfResult=@{assembly_sha256=$vfSha;method=$vfMethod.ToString();cases=$vfResults;
    qualification='Actual deployed GetDataSet on constant SELECTs under Fresh restricted principal; source-equivalent failures, not hosted HTTP'}
[IO.File]::WriteAllText($vfOutput,($vfResult | ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
