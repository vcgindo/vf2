param([Parameter(Mandatory=$true)][string]$InputPath,[Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
$vfRoot=[IO.Path]::GetFullPath('D:/freshvcf-build/evidence/')
$vfInput=[IO.Path]::GetFullPath($InputPath)
$vfOutput=[IO.Path]::GetFullPath($OutputPath)
if (-not $vfInput.StartsWith($vfRoot,[StringComparison]::OrdinalIgnoreCase) -or
    -not $vfOutput.StartsWith($vfRoot,[StringComparison]::OrdinalIgnoreCase) -or
    [IO.File]::Exists($vfOutput) -or $env:VFTEST_PROFILE -ne 'fresh') { throw 'New owned evidence and Fresh lease caller required' }
$vfDll='F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll'
$vfSha=(Get-FileHash $vfDll).Hash.ToLowerInvariant()
if ($vfSha -ne '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346') { throw 'Canonical DLL changed' }
# Caller holds exclusive_replay and validates owned database files/schema.
# Only a constant SELECT is executed, under the existing restricted principal.
$vfSqlClient='F:/VFlow_Local/local-runtime/mta-latest/runtimes/win/lib/netcoreapp2.1/System.Data.SqlClient.dll'
[void][Reflection.Assembly]::LoadFrom($vfSqlClient)
$vfAssembly=[Reflection.Assembly]::LoadFrom($vfDll)
$vfMethod=$vfAssembly.GetType('VectorFlowAPIs.Filters.GenericFunction',$true).GetMethod('ExecuteScalar').MakeGenericMethod([object])
$vfConnection='Server=localhost;Database=VFTEST_Fresh_BPR;Integrated Security=True;TrustServerCertificate=True;Pooling=False;Connect Timeout=10'
$vfValues=Get-Content -LiteralPath $vfInput -Raw | ConvertFrom-Json -AsHashtable
$vfResults=@()
foreach ($vfCase in $vfValues.cases) {
    $vfLiteral=if ($null -eq $vfCase.sql_value) { 'CAST(NULL AS nvarchar(max))' } else { "N'"+$vfCase.sql_value.Replace("'","''")+"'" }
    $vfQuery="EXECUTE AS LOGIN = 'freshvcf_oracle_replay' WITH NO REVERT; SELECT "+$vfLiteral
    if ($vfCase.ContainsKey('sql_error_207') -and $vfCase.sql_error_207 -eq $true) {
        # Bounded SQL binding failure to verify the deployed scalar helper's
        # error handling. The actual GIT query failure is recorded separately.
        $vfQuery="EXECUTE AS LOGIN = 'freshvcf_oracle_replay' WITH NO REVERT; SELECT MissingColumn FROM (SELECT 1 AS KnownColumn) s"
    }
    $vfResult=$vfMethod.Invoke($null,@($vfConnection,$vfQuery))
    $vfType=if ($null -eq $vfResult) { 'null' } else { $vfResult.GetType().FullName }
    # Exact ReviewExcessInventory/GetMonitorGITParent/transporter null fallback.
    if ($null -eq $vfResult) { $vfResult=[Collections.Generic.List[string]]::new() }
    $vfWire=[System.Text.Json.JsonSerializer]::Serialize($vfResult,$vfResult.GetType())
    $vfResults+=,@{id=$vfCase.id;runtime_type=$vfType;json=$vfWire}
}
$vfOutputValue=@{assembly_sha256=$vfSha;sqlclient_sha256=(Get-FileHash $vfSqlClient).Hash.ToLowerInvariant();
    runtime=[Runtime.InteropServices.RuntimeInformation]::FrameworkDescription;
    input_sha256=(Get-FileHash $vfInput).Hash.ToLowerInvariant();cases=$vfResults;
    qualification='Actual ExecuteScalar<object> over retained SQL JSON constants, Fresh restricted principal; no table writes or hosted HTTP claim'}
[IO.File]::WriteAllText($vfOutput,($vfOutputValue | ConvertTo-Json -Depth 60),[Text.UTF8Encoding]::new($false))
Write-Output 'Canonical Planning scalar deserialization saved'
