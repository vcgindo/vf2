# Windows: build from a clean Git clone using Docker commands

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

After cloning, the commands are `docker run`, `docker build` and `docker compose`. Host Python/Node, a previous application image and workstation-only helpers are not required. Committed source/export modules run inside a temporary pinned Python build container. Git is installed in that temporary tool container, not in the production application images.

**Status: this manual Docker-command route has not yet passed a complete fresh installation/functional comparison.** The previous attempt was stopped. Instructions/static checks are not installation acceptance. Run manually, in order, in the same PowerShell7 session; stop at the first failure. Never adopt/reset an old installation or delete its volumes to recover.

## 1. Clone and select the exact commit

Requires Git repository access, Docker Desktop in Linux/amd64 mode with Compose v2, PowerShell7 and internet for pinned images/dependencies. Allow at least35GiB free disk and the declared build/runtime memory caps below; those are not production-volume sizing proof.

Use new directories. Build/private files remain outside the clone. If you already cloned, start at `Set-Location` with your actual clone path.

```powershell
$ErrorActionPreference = 'Stop'
$CloneRoot = 'C:/VectorFLOW/Source'
$BuildRoot = 'C:/VectorFLOW/Build-Step5'
if (Test-Path -LiteralPath $CloneRoot) { throw 'Use a NEW clone directory, or use your existing clean clone' }
if (Test-Path -LiteralPath $BuildRoot) { throw 'Use a NEW build directory' }
New-Item -ItemType Directory -Force -Path (Split-Path $CloneRoot) | Out-Null
git clone --single-branch --branch codex/3006-logistics-integration `
  git@github.com:yurtse/freshvcf.git $CloneRoot
if ($LASTEXITCODE -ne 0) { throw 'Clone failed' }
Set-Location $CloneRoot
$Revision = (git rev-parse HEAD).Trim()
# If the handoff specifies a full commit, checkout THAT commit first and recapture $Revision.
git checkout --detach $Revision
if ($LASTEXITCODE -ne 0 -or (git status --porcelain)) { throw 'Expected a clean committed clone' }
Write-Host "Building commit: $Revision"
function Invoke-VFDocker {
  $Result = & docker @args
  if ($LASTEXITCODE -ne 0) { throw 'Docker failed; stop and retain output' }
  $Result
}
Invoke-VFDocker info --format '{{.OSType}}/{{.Architecture}}'
# Require linux/amd64 or linux/x86_64 before continuing.
Invoke-VFDocker compose version
New-Item -ItemType Directory -Path $BuildRoot | Out-Null
```

Do not pull/edit source between export and build. All four application images below use that one captured commit.

## 2. Select the port in an external env file before building

```powershell
$BuildEnv = Join-Path $BuildRoot 'build.env'
Copy-Item -LiteralPath release/.env.example -Destination $BuildEnv
notepad $BuildEnv
```

Set only `VF_HTTP_PORT` to a free local port, for example8090 if8080 is occupied; save and close the editor. These commands derive both browser origins from that setting. The unchanged frontend compiles its matching WebSocket origin during the build. A later port change needs a matching rebuild; it does not dynamically rewrite the browser bundle.

```powershell
$PortLine = @(Get-Content -LiteralPath $BuildEnv | Where-Object { $_ -match '^VF_HTTP_PORT=' })
[int]$HttpPort = 0
if ($PortLine.Count -ne 1 -or -not [int]::TryParse(($PortLine[0] -split '=',2)[1],[ref]$HttpPort) -or $HttpPort -lt 1 -or $HttpPort -gt 65535) { throw 'Invalid VF_HTTP_PORT' }
if (Get-NetTCPConnection -LocalPort $HttpPort -State Listen -ErrorAction SilentlyContinue) { throw 'Port occupied; choose another, do not replace an existing service' }
$PublicUrl = "http://127.0.0.1:$HttpPort"
$WebSocketUrl = "ws://127.0.0.1:$HttpPort"
$Locks = Get-Content -Raw release/images.lock.json | ConvertFrom-Json
$PublicCipher = (Get-Content -Raw release/windows-final-release.json | ConvertFrom-Json).public_client_cipher_key
foreach ($Name in @('python_mta','python_legacy_services','node_build','nginx','postgres','redis')) {
  Invoke-VFDocker pull --platform linux/amd64 $Locks.$Name
}
```

The client cipher is intentionally public browser configuration, not a database/signing/RSA secret. Auth must match it. This is localhost HTTP/WS only; public HTTPS/WSS requires the actual destination/TLS configuration.

## 3. Prepare the committed build contexts inside Docker

The MTA Dockerfile requires a finite exported application, independent source descriptors and eight hash-pinned wheels. This creates those ordinary build outputs from Git; it does not change the clone, install a database, start a serving application or load any data.

```powershell
$Preparation = @"
import hashlib,json,os
from pathlib import Path
from release.export import export
from release.build_release import wheels
from release.mta_packaging import prepare
root=Path('/out');commit=os.environ['VF_BUILD_REVISION']
record=export('/src',commit,root/'export')
assert record['source_commit']==commit
assert (root/'export/frontend/tsconfig.paths.json').is_file()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_sha=sha(root/'export/release-source.json')
native_sha=sha(root/'export/release-native-source.json')
wheels(root/'export',root/'wheels')
context=prepare(root/'export',root/'mta-context',root/'wheels',commit=commit,source_sha256=source_sha,native_sha256=native_sha)
proof={'source_commit':commit,'source_sha256':source_sha,'native_sha256':native_sha,'packaging_tool_sha256':context['packaging_tool_sha256'],'application_runtime_started':False}
(root/'preparation.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof))
"@
$Preparation | & docker run --rm -i --platform linux/amd64 --memory 2g --memory-swap 2g --cpus 1 `
  --mount "type=bind,source=$CloneRoot,target=/src,readonly" `
  --mount "type=bind,source=$BuildRoot,target=/out" `
  -e "VF_BUILD_REVISION=$Revision" -e PYTHONPATH=/src -e PYTHONDONTWRITEBYTECODE=1 `
  --entrypoint sh $Locks.python_mta -ec `
  'apt-get update >&2; apt-get install -y --no-install-recommends git >&2; git config --global --add safe.directory /src; python -B -'
if ($LASTEXITCODE -ne 0) { throw 'Preparation failed; retain output and do not continue' }
$Prepared = Get-Content -Raw "$BuildRoot/preparation.json" | ConvertFrom-Json
if ($Prepared.source_commit -ne $Revision) { throw 'Wrong prepared source' }
$AppRoot = Join-Path $BuildRoot 'export'
$Tag = $Revision.Substring(0,12)
$Prefix = 'vectorflow-git'
$env:DOCKER_BUILDKIT = '0'
```

Git installed by apt is temporary build tooling only. Application dependencies/base images retain their committed pins. No local `node_modules` or previous application image is an input.

## 4. Build all four application images with Docker

Run sequentially. Backends are bounded to4GiB/2CPU and frontend6GiB/2CPU. The offline MTA build uses its verified context; do not substitute a raw checkout or `docker compose up --build` shortcut. These manual commands have CPU/memory bounds, not an automatic disk/deadline watchdog. Monitor free disk and stop/preserve on a resource failure; do not prune or expand capacity automatically.

```powershell
Invoke-VFDocker build --pull=false --network none --memory 4g --memory-swap 4g `
  --cpu-period 100000 --cpu-quota 200000 --rm=false `
  --build-arg "VF_NATIVE_RELEASE_COMMIT=$Revision" `
  --build-arg "VF_NATIVE_RELEASE_SHA256=$($Prepared.native_sha256)" `
  --build-arg "VF_SOURCE_MANIFEST_SHA256=$($Prepared.source_sha256)" `
  --build-arg "PACKAGING_TOOL_SHA256=$($Prepared.packaging_tool_sha256)" `
  -t "${Prefix}/mta:$Tag" "$BuildRoot/mta-context"
Invoke-VFDocker build --pull=false --memory 4g --memory-swap 4g `
  --cpu-period 100000 --cpu-quota 200000 --rm=false `
  -f "$AppRoot/release/auth.Dockerfile" -t "${Prefix}/auth:$Tag" $AppRoot
Invoke-VFDocker build --pull=false --memory 4g --memory-swap 4g `
  --cpu-period 100000 --cpu-quota 200000 --rm=false `
  -f "$AppRoot/release/mto.Dockerfile" -t "${Prefix}/mto:$Tag" $AppRoot
& docker build --pull=false --memory 6g --memory-swap 6g `
  --cpu-period 100000 --cpu-quota 200000 --rm=false `
  --build-arg REACT_APP_API_HOST=/ --build-arg REACT_APP_VF_API_HOST_MTO=/api/mto `
  --build-arg "REACT_APP_WS_API_HOST=$WebSocketUrl" --build-arg "REACT_APP_SECRET_KEY=$PublicCipher" `
  --build-arg REACT_APP_AG_GRID_LICENSE_KEY= --build-arg FRONTEND_BUILD_HEAP_MIB=4096 `
  -f "$AppRoot/release/frontend.Dockerfile" -t "${Prefix}/frontend:$Tag" $AppRoot `
  2>&1 | Tee-Object -FilePath "$BuildRoot/frontend-build.log"
if ($LASTEXITCODE -ne 0 -or (Select-String -LiteralPath "$BuildRoot/frontend-build.log" -SimpleMatch 'TS5083:')) { throw 'Frontend build failed or required TypeScript configuration missing' }
```

Retain the logs. The existing frontend policy can emit retained lint/type warnings; image emission is not a clean whole-codebase type/lint claim. Missing required configuration is a failure. No frontend/MTO application source is changed.

## 5. Record the exact images for installation

These are generated build outputs, not missing source or manual image patches. They pin the images just built rather than the old packaged images.

```powershell
function Write-JsonFile([string]$Path, $Value) {
  [IO.File]::WriteAllText($Path,($Value | ConvertTo-Json -Depth 16),[Text.UTF8Encoding]::new($false))
}
$Images = [ordered]@{}
foreach ($Name in @('mta','auth','mto','frontend')) {
  $Images[$Name] = (Invoke-VFDocker image inspect "${Prefix}/${Name}:$Tag" --format '{{.Id}}').Trim()
}
foreach ($Name in @('postgres','redis')) {
  $Images[$Name] = (Invoke-VFDocker image inspect $Locks.$Name --format '{{.Id}}').Trim()
}
$Services = [ordered]@{}
foreach ($Name in $Images.Keys) { $Services[$Name]=@{image=$Images[$Name];pull_policy='never'} }
foreach ($Pair in @(@('mta-install','mta'),@('auth-install','auth'),@('mto-install','mto'),@('provision','mta'))) {
  $Services[$Pair[0]]=@{image=$Images[$Pair[1]];pull_policy='never'}
}
$Services['mta-install'].mem_limit='4g'
$Services['mta-install'].memswap_limit='4g'
$Services['mta-install'].cpus='2'
$Restriction = 'DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.'
Write-JsonFile "$BuildRoot/source-build-images.yaml" @{'x-restriction'=$Restriction;services=$Services}
$Release = [pscustomobject]@{
  restriction=$Restriction;code_commit=$Revision
  component_sources=@{mta=$Revision;auth=$Revision;mto=$Revision;frontend=$Revision}
  images=$Images;native_manifest_sha256=$Prepared.native_sha256;mta_source_manifest_sha256=$Prepared.source_sha256
  public_origin=$PublicUrl;websocket_origin=$WebSocketUrl;public_client_cipher_key=$PublicCipher
  optional_raw_inputs=(Get-Content -Raw "$AppRoot/release/windows-final-release.json" | ConvertFrom-Json).optional_raw_inputs
  verification_boundary='Docker build completed; blank/functional runtime acceptance requires actual checks.'
}
Write-JsonFile "$BuildRoot/installation-release.json" $Release
$TemplateValues = @{
  VF_HTTP_PORT="$HttpPort";VF_PUBLIC_URL=$PublicUrl;VF_PUBLIC_WS_URL=$WebSocketUrl
  VF_RELEASE=$Revision;VF_NATIVE_RELEASE_COMMIT=$Revision;VF_NATIVE_RELEASE_SHA256=$Prepared.native_sha256
  VF_SOURCE_MANIFEST_SHA256=$Prepared.source_sha256;VF_CLIENT_CIPHER_KEY=$PublicCipher
}
$TemplateLines = @(Get-Content -LiteralPath "$AppRoot/release/.env.example" | ForEach-Object {
  $Name = ($_ -split '=',2)[0]
  if ($TemplateValues.ContainsKey($Name)) { "$Name=$($TemplateValues[$Name])" } else { $_ }
})
[IO.File]::WriteAllLines("$BuildRoot/operator.env.template",(@("# $Restriction") + $TemplateLines),[Text.UTF8Encoding]::new($false))
```

The exact four applications, PostgreSQL and Redis are now available locally. Building does not install schemas, create accounts or load data.

## Install these newly built images as a blank application

Use the same PowerShell session below and then follow [RUNBOOK.md Part A, steps2–6](RUNBOOK.md#2-generate-private-secrets-and-configure-the-new-target). This replaces only its prebuilt-ZIP step1. Choose a new installation root. Do not execute Part B until the blank checkpoint passes.

```powershell
$ErrorActionPreference = 'Stop'
$DocsRoot = $CloneRoot # clean clone containing this procedure
$BundleRoot = $BuildRoot
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

Source-build acceptance remains pending; the earlier attempt was stopped for delivery review. This runbook does not resume it. The previously accepted prebuilt package remains unchanged.
