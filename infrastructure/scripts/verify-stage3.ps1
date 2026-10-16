$ErrorActionPreference = 'Stop'
$stage3Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$required = @('frontend/package.json','user-service/manage.py','mto/manage.py','mta/manage.py','mta/migrations/README.md','parity/comparators/exact.py','compose.yaml','docs/stage3/STAGE3_IMPLEMENTATION_STATUS.md','docs/stage3/STAGE3_TARGET_ARCHITECTURE.json','docs/stage3/PORT_PROVENANCE.md')
foreach ($item in $required) { if (!(Test-Path -LiteralPath (Join-Path $stage3Root $item))) { throw "Missing $item" } }
$requiredDocs = @('TARGET_LOGICAL_ARCHITECTURE.md','TARGET_COMPONENT_MODEL.md','MTA_DOMAIN_MODEL.md','MTA_RUN_MODEL.md','MTA_CANONICAL_DATA_MODEL.md','MTA_API_COMPATIBILITY_IMPLEMENTATION.md','MTA_MIGRATION_WAVES.md','MTA_PARITY_ARCHITECTURE.md','MTA_CONFIGURATION_MODEL.md','MTA_DEPLOYMENT_MODEL.md','MTA_OBSERVABILITY_MODEL.md','MTA_TEST_STRATEGY.md','MTA_SECURITY_BOUNDARY.md','MTA_TECHNOLOGY_ADR.md','STAGE3_DECISIONS_AND_GAPS.md','STAGE3_IMPLEMENTATION_STATUS.md')
foreach ($doc in $requiredDocs) { if (!(Test-Path -LiteralPath (Join-Path $stage3Root "docs/stage3/$doc"))) { throw "Missing Stage 3 document $doc" } }
if (Test-Path -LiteralPath (Join-Path $stage3Root 'frontend/node_modules')) { throw 'frontend/node_modules must not be copied' }
foreach ($component in @('frontend','user-service','mto')) { if (Test-Path -LiteralPath (Join-Path $stage3Root "$component/.git")) { throw "$component must not carry source .git metadata" }; if (Test-Path -LiteralPath (Join-Path $stage3Root "$component/.env")) { throw "$component must not carry source .env" } }
$routes = (Get-Content -Raw (Join-Path $stage3Root 'mta/config/api_compatibility_routes.json') | ConvertFrom-Json).routes
if ($routes.Count -ne 123) { throw "Expected 123 API compatibility records; found $($routes.Count)" }
foreach ($expected in @{ TEMPORARILY_FORWARDED_TO_LEGACY = 109; UNRESOLVED = 13; INTERNALLY_REIMPLEMENTED = 1 }.GetEnumerator()) { $actual = @($routes | Where-Object { $_.stage3_classification -eq $expected.Key }).Count; if ($actual -ne $expected.Value) { throw "Expected $($expected.Value) $($expected.Key) routes; found $actual" } }
Push-Location $stage3Root
try {
    $envFile = if (Test-Path -LiteralPath '.env') { '.env' } else { '.env.example' }
    docker compose --env-file $envFile --profile test build mta-test
    if ($LASTEXITCODE -ne 0) { throw 'Failed to build the isolated MTA test image' }
    docker compose --env-file $envFile --profile test run --rm --no-deps mta-test python /app/parity/prepare_new_database.py
    if ($LASTEXITCODE -ne 0) { throw 'Failed to prepare the isolated MTA test database' }
    docker compose --env-file $envFile --profile test run --rm mta-test python manage.py test mta --verbosity 0 --keepdb
    if ($LASTEXITCODE -ne 0) { throw 'MTA test suite failed' }
    docker compose --env-file $envFile --profile test run --rm --no-deps mta-test python -m unittest discover -s /app/parity/tests -t /app
    if ($LASTEXITCODE -ne 0) { throw 'Parity unit test suite failed' }
} finally { Pop-Location }
Write-Output 'Stage3 scaffold verification passed in the isolated test image.'
