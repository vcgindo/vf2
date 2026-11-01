# VectorFLOW

Production application source for MTA, authentication, the existing frontend and MTO.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

## Install the application

There are two installation routes. Both must end at a blank application; master/opening loading and daily execution are separate operations.

- **Build from Git:** [release/SOURCE_BUILD.md](release/SOURCE_BUILD.md) gives the committed export/build commands and then uses the same blank-install procedure. Root `compose.yaml` builds all four applications from the same committed source; `docker compose run --rm install` installs only empty schemas/system metadata and your new administrator. No manual export/hash/image-override steps. Independent verification is recorded in the existing handoff tracker.
- **Install the retained prebuilt images:** [release/RUNBOOK.md](release/RUNBOOK.md) Part A installs the recorded six-component package. Its initialized application scope passed Step5; the separate blank operator check is still explicitly qualified there. Part B documents optional data onboarding and daily operation.

Do not use the historical root runbook, preview Compose files or workstation validation scripts to install a production target. Public deployment/cutover needs its destination, HTTPS/WSS, capacity and recovery decisions; localhost acceptance does not establish those.

## Update an existing installation

Use the repository-owned [routine upgrade command](release/UPGRADE.md) for compatible MTA patches and forward migrations. Preserve the existing deployment configuration and data; do not repeat installation or initialization.

## Repository layout

| Path | Purpose |
| --- | --- |
| `mta/`, `vectorflow/`, `manage.py` | Native MTA application and Django entry/settings |
| `user-service/` | Authentication and API gateway |
| `mto/` | Existing MTO application |
| `frontend/` | Existing frontend application |
| `release/` | Supported production build, Compose, configuration, provisioning and operating procedures |
| `tests/` | Automated source/release checks |
| `baseline/` | Native schemas plus explicitly retained development reference descriptors; the exporter admits only the required runtime subset |
| `parity/`, `development/`, `tools/`, preview/test Compose files | Development and historical validation; not production installation dependencies |
| `docs/` | Handoff, design and retained engineering history |

The production exporter selects committed application/runtime files; it excludes validation runners, test data, private secrets, customer databases and calculated output seeds. Development source retained in Git is not shipped automatically into the production image.

## Configuration and private files

Use `release/.env.example` as the documented template, with real env/secrets outside Git and outside image contexts. No production password, private key, database dump or local evidence is an installation input from this repository. Build outputs and receipts go to a new external directory. Dependency caches may be reused only under the committed hash/version checks.

For this five-step production handoff, [docs/handoff-3005/PLAN.md](docs/handoff-3005/PLAN.md) defines scope. The live `F:/freshvcf/docs/handoff-3005/TRACKER.md` is its sole status/decision tracker; a clone is not a new status queue. [docs/LEGACY_EXCEPTIONS.md](docs/LEGACY_EXCEPTIONS.md) and [AGENTS.md](AGENTS.md) retain contract and contribution boundaries. Older `docs/MIGRATION.md` material is historical for this handoff.
