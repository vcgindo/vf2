# Approved initial NMS owner amendment

Approved10October2026 by direct human reply
`call_e4d7b64734034dcba0a990b23ee90b40:0`, “Approve exact initial-NMS amendment”.
Preparation/registration only; no business-day execution or serving release.

This is a single source amendment to approved S1–S5. It authorizes preparation
and registration only, not a business-day call or a serving change. Status is
tracked only in `MIGRATION.md`.

Active canonical `NMSImportData.sql` rebuilds MasterDataRaw from NMSAllItems on
D0 as well as successors. The retained opening has no NMSAllItems rows. Using
external raw_master as a D0 fallback would change that contract.

Approve replacing only that empty opening population with the twenty ordered
rows produced by the existing canonical snapshot function from the approved
initial MasterData, DBMMaster, attributes, descriptions and exclusions. Every
initial Norm remains unchanged; the snapshot produces zero MasterData changes.
This is an explicitly derived initial owner, not a consumed capture or another
run's closing. Preserve all fields, NULLs, duplicate ordinals and row order.
All other business inputs, flags, requests, dates, scopes and policies remain
as approved. The retained twelve-day conserved source horizon does not authorize
execution beyond the separately proposed June 6–8 dates.

Exact artifacts under `D:/freshvcf-build/evidence/mdm-approval-day-20261010-001/`:

| Artifact | SHA256 |
| --- | --- |
| Original registered `mdm-approval-day-input-v1.json`, preserved | `7586426e7b061499e17d5d89d73c33b77c89d8c5671ffa65b3f929c9a536f100` |
| `proposed-initial-nms-owner-v1.json`, derivation evidence | `0b4abcb82622d6d76dd37cc92296a74bad2bc07d1334d1ced13b1aeaaece515e` |
| Proposed new `mdm-approval-day-input-initial-nms-v1.json` | `be33508fd9e5cd6b0224f02502f61b87a0cfb8cdce44cafb3d1f1c3e1384d847` |

Canonical snapshot SQL SHA256:
`f306ea8dc185611197d55d5deb7dd8bf5d1ab5523a581577bc0b8f1ec63a47ab`.
Complete ordered NMS owner digest:
`e99be5d0bdb1fb8f98e424b3cd2dc51fd6b4603a8fd6ffd626f03433e863a1ce`.
The new artifact changes only opening.consumer_context.NMSAllItems and adds
its explicit derivative provenance. Its size is 863,777 bytes. No database
installation, business-day execution or serving selection used this proposal.

Approval permits registering this new identity, pinning its dependent shipment,
source and admission bindings, and completing the existing finite M2 package.
The original artifact and strict source-conflict evidence remain preserved.
Separate frozen execution approval is still required before D0.
