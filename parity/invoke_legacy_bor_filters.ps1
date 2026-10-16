param([Parameter(Mandatory=$true)][string]$InputPath,
      [Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath('D:/freshvcf-build/evidence/')
$inputFile=[IO.Path]::GetFullPath($InputPath)
$outputFile=[IO.Path]::GetFullPath($OutputPath)
if (-not $inputFile.StartsWith($root,[StringComparison]::OrdinalIgnoreCase) -or
    -not $outputFile.StartsWith($root,[StringComparison]::OrdinalIgnoreCase) -or
    [IO.File]::Exists($outputFile)) { throw 'New owned evidence output required' }
$dll='F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll'
$sha=(Get-FileHash $dll).Hash.ToLowerInvariant()
if ($sha -ne '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346') { throw 'Canonical DLL changed' }
$assembly=[Reflection.Assembly]::LoadFrom($dll)
$method=$assembly.GetType('VectorFlowAPIs.Filters.GenericFunction',$true).GetMethod('ApplyFiltersForReports')
$requestType=$method.GetParameters()[1].ParameterType
$assembly.GetType('VectorFlowAPIs.Startup',$true).GetField('ErrorLogFilePath').SetValue($null,([IO.Path]::GetDirectoryName($outputFile)+[IO.Path]::DirectorySeparatorChar))
$options=[System.Text.Json.JsonSerializerOptions]::new()
$options.PropertyNameCaseInsensitive=$true
$cases=@()
foreach ($case in (Get-Content -LiteralPath $inputFile -Raw | ConvertFrom-Json -AsHashtable).cases) {
    $request=[System.Text.Json.JsonSerializer]::Deserialize(($case.payload | ConvertTo-Json -Depth 40 -Compress),$requestType,$options)
    $arguments=[object[]]@('BOR',$request,'','')
    $method.Invoke($null,$arguments) | Out-Null
    $cases+=,@{id=$case.id;sql_filter=[string]$arguments[2];sql_join_filter=[string]$arguments[3]}
}
$result=@{assembly_sha256=$sha;cases=$cases;input_sha256=(Get-FileHash $inputFile).Hash.ToLowerInvariant();
    authority='Pinned DLL ApplyFiltersForReports BOR invocation, including its exception boundary; no DB connections'}
[IO.File]::WriteAllText($outputFile,($result | ConvertTo-Json -Depth 60),[Text.UTF8Encoding]::new($false))
Write-Output 'Canonical BOR filter queries saved'
