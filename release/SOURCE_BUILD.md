# Build an installable release from a clean Git clone

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

This builds the four application images from one committed production export. PostgreSQL and Redis remain the exact official digests in `images.lock.json`. It never starts a serving application or installs/loads a database. Blank installation and optional business input/loading/daily execution remain separate operations in [RUNBOOK.md](RUNBOOK.md).

Use a new clone, checkout the approved full revision, and keep it clean. Python3 and Docker Linux/amd64 are required; no host npm/Node installation is needed. First builds need access to the pinned dependency distributions, or an independently verified dependency cache. Choose a new output directory outside the clone. Do not build an uncommitted checkout, reuse a failed output directory, substitute a mutable base tag or import a workstation env/secrets file.

```powershell
# In your clean clone, after checking out the approved full commit:
$Revision = git rev-parse HEAD
$PublicCipher = (Get-Content -Raw release/windows-final-release.json | ConvertFrom-Json).public_client_cipher_key
python -B -m release.build_release --repository . --revision $Revision `
  --output C:/VectorFLOW-Builds/NEW-RELEASE --image-prefix vectorflow-git `
  --public-origin http://127.0.0.1:8080 --websocket-origin ws://127.0.0.1:8080 `
  --public-client-cipher $PublicCipher
if ($LASTEXITCODE -ne 0) { throw 'Build failed; retain output/logs and stopped attempts' }
```

The client cipher is intentionally public browser build configuration and must match auth. It is not a signing/database/RSA secret. The current frontend still compiles its WebSocket origin at build time; this source-build procedure does not implement the separately proposed runtime port improvement.

The script exports only admitted committed production files, creates independent source/native descriptors and builds the finite MTA context with eight hash-checked wheels. An optional `--wheelhouse` accepts only that exact wheel roster; absent wheels are downloaded at their pinned hashes. Auth/MTO use their pinned dependency locks. Frontend uses `npm ci` and its committed lock; its build-only helper retains the existing checks/minification while bounding module/minifier/checker parallelism. No prior application image, local node_modules or patched Docker layer is a source input.

Builds run sequentially, with 4GiB/2CPU limits per backend build and 6GiB/2CPU for frontend, no swap allowance beyond RAM and a30minute per-component deadline. Host free-space monitoring stops at14GiB consumption or20GiB free, conservatively including unrelated host usage; it is not a hard Docker storage quota. Failed builds retain logs and stopped attempts. Do not prune Docker or increase capacity as an automatic remedy.

`build-receipt.json` records the source/native hashes and actual four image IDs. The script also writes `installation-release.json`, `source-build-images.yaml` and `operator.env.template`, pins the PostgreSQL/Redis images locally and supplies the exact runtime/installer identities to the existing runbook. It does not require the old runtime ZIP. A build exit does not claim functional acceptance; the blank/connected checks remain required. Never substitute new images into an old immutable package or source-sealed database.

## Install these newly built images as a blank application

Use the same PowerShell session below and then follow [RUNBOOK.md Part A, steps2–6](RUNBOOK.md#2-generate-private-secrets-and-configure-the-new-target). This replaces only its prebuilt-ZIP step1. Choose a new installation root. Do not execute Part B until the blank checkpoint passes.

```powershell
$ErrorActionPreference = 'Stop'
$DocsRoot = (Get-Location).Path # clean clone containing this procedure
$BundleRoot = [IO.Path]::GetFullPath('C:/VectorFLOW-Builds/NEW-RELEASE')
$AppRoot = Join-Path $BundleRoot 'export'
$Release = Get-Content -Raw "$BundleRoot/installation-release.json" | ConvertFrom-Json
$ImageOverridePath = Join-Path $BundleRoot 'source-build-images.yaml'
$InstallRoot = [IO.Path]::GetFullPath('C:/VectorFLOW-Clean')
if (Test-Path -LiteralPath $InstallRoot) { throw 'Use a NEW directory; do not overwrite' }
$PrivateRoot = Join-Path $InstallRoot 'private'
$ReceiptsRoot = Join-Path $InstallRoot 'receipts'
New-Item -ItemType Directory -Path $PrivateRoot,$ReceiptsRoot | Out-Null
function Invoke-VFDocker {
  $Result = & docker @args
  if ($LASTEXITCODE -ne 0) { throw 'Docker failed: stop and preserve the command/output' }
  $Result
}
foreach ($Property in $Release.images.PSObject.Properties) {
  $Actual = Invoke-VFDocker image inspect $Property.Value --format '{{.Id}}'
  if ($Actual -ne $Property.Value) { throw "Wrong local image: $($Property.Name)" }
}
```

The public URL/WebSocket origin chosen at build time must match installation. Part A's retained-package warning about its compiled8080 socket refers to that old package; these new images use the origins supplied to the build. Changing `VF_HTTP_PORT` after building does not rebuild browser JavaScript. For another origin, build from the same unchanged source with that explicit origin. HTTPS/WSS still requires actual host/TLS configuration and deployment approval. Runbook step3's composite-revision qualification applies only to the old prebuilt package; this route uses one committed revision for all four applications.

To transfer this build without Git/Python/compilers on the destination, save the six IDs in `$Release.images` with `docker image save`, transfer that image archive plus this build output's export/installation files and the runbook, and run `docker image load` before installation. Keep private secrets separate. Do not relabel the old verified runtime ZIP as this new build.

Current source-build acceptance is pending the active clean-clone exercise; the previously accepted prebuilt package remains unchanged.
