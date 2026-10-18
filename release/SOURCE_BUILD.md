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

`build-receipt.json` records the source/native hashes and actual four image IDs. A build exit does not claim functional acceptance. Before delivery compare application/dependency contents and execute the bounded blank/connected checks against the explicitly frozen Step5 baseline. Then produce an exact-image installation override and transferable archive for those new IDs; do not silently substitute them into an old immutable package or source-sealed database.

Current source-build acceptance is pending the active clean-clone exercise; the previously accepted prebuilt package remains unchanged.
