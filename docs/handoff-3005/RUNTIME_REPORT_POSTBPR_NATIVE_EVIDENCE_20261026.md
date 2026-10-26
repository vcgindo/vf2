# Bounded PostBPR publication: native evidence checkpoint

Status remains solely in `F:/freshvcf/docs/handoff-3005/TRACKER.md`.
This records the approved publication fixture, not first-item or general G2
acceptance. Frontend design, MTO and the 8080 serving stack are unchanged.

## Build and fixture

- Implementation: `b453a5119954cd873b913ea4e0e02e3937413a0e`.
- Target image: `sha256:84ac4fee1d4aa1c3bf931cd1f81cd772d32f5d7404589e3ebc19a9f1eee50d7b`.
- Native manifest: `1e105d56733d4ee1489ac58e60d5a5093bebd83e5261ef99e1790d3992274dce`.
- Writer-disabled bridge: `96f0b700daa91d083fde9a20772359feb12ae31d`, image
  `sha256:6bc401c8bbebb32a5f451de2701bb5f420e4638abf57f0b4426567f14402d13f`.
- New database: `vftest_fresh_runtime_publication_20261026`, OID 533551.
- Initialization: `a2886943-9ad4-4c84-80aa-16db9822a50a`.
- Independently calculated Full23/24 predecessors:
  `bc93f08c-13e8-45f6-ad0a-1b2ef9212689`, `52e28e9c-1616-441f-9d85-8a986d836d9d`.
- New 25 October UptoBPR run: `bae24882-1a91-4082-90a3-300819d6279b`.
- PostBPR publication: `5aed5230-29b8-4389-b3ad-25ad19d67d2d`, digest
  `e33df8852bde2491f649779a1cd75065ac223d6733899544413f4500f984b392`.
- Read reference: `3822d90d-fba5-4f53-89ec-1647c647913f`, digest
  `660b2102724d93fe0b080f9178f3c24c7d6fe78ce79cada589783795059aeb52`.

Evidence root:
`D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/runtime-publication-20261026`.
The 21-file checksum index is `native-publication-checkpoint.json`, SHA256
`8061efed809db8447a2759dd7acb8833e154e7c08bc27f01e5bb9a5850c456df`.
Earlier component records retain their original qualifications; later proofs
supplement them rather than rewriting their history.

## Verified boundaries

| Boundary | Native evidence and limit |
| --- | --- |
| Sources and files | Actual typed sources independently compared with direct PostgreSQL SELECT results as complete typed occurrence multisets. Spike is 2 rows by 12 columns; Total Requirement is 8 by 107. Complete CSV headers/cells and ZIP member bytes agree. No unordered-query ordering or native 7Zip container-byte claim. |
| Durable owner | The existing scoped claim registers one immutable receipt per placement, with authoritative source/request/configuration/catalogue checks. The new reference distinguishes the nonempty roster from old empty TEST references. Other owner variants remain disabled. |
| Failure and recovery | Three file-writing faults, process exit after complete private files, actual INSERT followed by rollback, 12 invalid candidates, overlapping claim denial, explicit fencing and recovery without BPR replay. Private failures remain preserved. |
| Retry | Two concurrent retries after committed publication return the original result without calculation. The replaced worker token is denied. This is not a concurrent first-INSERT or first-commit acknowledgement-loss witness. |
| Catalogue and custody | Ordered Id7/Id10 private replacement folds against the actual prior catalogue and preserves original files. Missing/tampered accepted CSV is rejected by reads and normal retry; retry does not repair it. The original inode is restored and full hashes rechecked. No second durable catalogue generation is claimed. |
| Permissioned backend | Actual packaged Django metadata and both literal download routes return the verified bytes. Missing identity/entitlement and empty grants deny. An unknown permission ID retains the existing unavailable response. Native installer/runtime ACL and DML denials pass. |
| Auth transport | 19 tests pass for selectors, streaming, identity, entitlement and permission transport using actual committed auth source with retained dependencies. This is separate from the native private MTA HTTP proof, not an authenticated browser/JWT end-to-end download. |
| Dedicated lease foundation | Actual different PostgreSQL PIDs, registered NOINHERIT issuer-to-owner entry/reversion, competitor exclusion, session loss/replacement and outer-Django-transaction denial pass. No operational registrar is enabled or qualified. |
| Compatibility | Supported 0228 namespace upgrades through 0229/0230; actual late-admission failure rolls back. Exact 92-entry portable catalogue contract is enforced. Native Django check, no model drift and no pending migration pass. Actual writer-disabled bridge reads the new receipt and reference after compatible code admission in this new DB. |
| Retained milestones | Baseline and target decode identical complete retained UptoBPR/DBM phases and PostBPR/PostDBM outputs, preserving old request/configuration and row fingerprints. Old databases receive no writes or migrations. Historical stops are not claimed currently selectable on their older schema. |

The Spike CSV/member SHA256 is
`504ebdb41356e7489ad9ccd944cd542cfec323ef112c02c9bdf467de0b488469`;
Total Requirement CSV SHA256 is
`f9f967aa2fc5d9b323ef8d95bef0e3297b53388b3f2f98d7b04a0e654d3a9630`.

## Migration register and preserved failures

`fresh_mta.0229_runtime_report_publication` adds the receipt model following
0228; `0230_runtime_report_publication_guards` installs its ownership/immutability
SQL and the finite read-reference extension. Both are now applied and immutable.
The supported upgrade is an unextended 0228 namespace; other starting catalogues
deny. Existing registration, certificates, capabilities, predecessor rows and
accepted-state ownership are preserved. There is no fake migration or resealing.

The first SQL syntax, shared-truncate-guard inventory and generated-index matcher
failures were rollback-only and remain retained. The successful schema commit
was followed by an observer error comparing rehearsal OIDs to committed OIDs;
no DDL was repeated. Readback verified the committed receipt's own live guard
and the portable definitions. The retained milestone observer was corrected to
fingerprint actual old columns and serialize the actual CalculationSources
dataclass; original errors remain. The first HTTP observer expected 403 for an
unknown permission ID; existing production behavior correctly denied it as 503.

## Prior checkpoint's unmet proof

The strict first-item exit is still open. Literal connection loss before INSERT
and before COMMIT racing replacement, plus death after the first COMMIT before
acknowledgement, have not been proved by this already-published fixture. Its
receipt must not be removed or rewritten to create that state. The authenticated
gateway download is also not closed by separate auth and private-backend proofs.

A fresh recovery fixture is prepared, not created or authorized, in
`prepared-additional-recovery-fixture.json`, SHA256
`879cce6d5eed89c514851733ff23fd96549d213f1a62a120240e82bff8659852`.
It proposes the same retained feeds/configuration, its own Full23/24 predecessors,
then UptoBPR25, on the same owned PostgreSQL and limits. Capacity preflight projects
3,847,966,890 bytes including the existing 512 MiB reserve, below 4 GiB; this must
be checked again before execution. Existing fixtures and 8080 remain preserved.

RuntimeReports readiness is true for these two files; whole-scope readiness is
false, with configured-artifact and end-to-end gates still pending. Full,
PostBTR/Final, operational publication, other report families, matched latency,
scale, G3, browser delivery and serving cutover are not accepted by this evidence.

## Completed recovery and authenticated gateway supplement

The human delegated approval to controller chat
`01a16a2e-ce92-7440-b834-b3b0e05b68ef`, which approved the exact prepared plan
above. The human subsequently confirmed the same additional-fixture approval
directly. One database was created: `vftest_fresh_runtime_publication_recovery_20261026`,
OID558712. It uses the already qualified target0230 schema, identical retained
inputs/dispositions and independently computed Full23/24 predecessors. No
accepted rows were copied into its calculations.

New UptoBPR25 run `a5d7cc11-1837-4f78-9738-ba178b69cfb3` produced BPR phase
`114606b5-1746-4046-8b88-10a55501224c`. Actual connection termination immediately
before INSERT and after INSERT before COMMIT left no PostBPR receipt. In both
cases a replacement was observed waiting on the live registrar's lock; explicit
fencing and a new claim succeeded only after that connection ended.

Two concurrent first registrars then prepared distinct private candidates.
Exactly one committed publication, `466c291d-fdfd-411f-bc3b-bc038ca928c9`, digest
`1fca201df594ad0f8db971a4b622c4d908d34e51cb01be0413c26a8c2a849c98`.
The winner exited86 in Django's post-COMMIT callback before the registrar
returned. The competing request and subsequent explicitly fenced recovery both
returned that same immutable receipt. All four interrupted/fenced attempts and
the final released attempt remain. There are still exactly two accepted business
phases and no commands; complete decoded BPR/consumer state, predecessor output,
business-table fingerprints and the original PostImporter receipt are unchanged.
Runtime-role readback confirms both recovered files match the original fixture's
complete source-derived CSV/member content.

Real gateway proof uses the original new publication run `bae24882...`, the
existing verified administrator1 and unchanged canonical password login and
CookieJWT authentication. Native scope expansion overwrites forged request
identity/grants. Production MTA startup/request admission, metadata and both GET
downloads pass with exact bytes, filename and MIME. Missing authentication and
an invalid JWT signature return401; unsupported POST returns405. This is actual
HTTP through the auth interceptor and private MTA, not an asserted-user unit
test. Normal login audit/token/last-login effects are expected; credentials,
grants, frontend and MTO contracts are unchanged. Browser/CAPTCHA interaction and
Chrome file arrival are not claimed.

The first three gateway harness attempts remain failures. Inspection established
that the protected MTA already shares PostgreSQL's network namespace on8000;
the proposed fixed-port test server collided, and the metadata assertions
correctly rejected the old backend's report list. The final harness uses an
ephemeral private socket, verifies its own running container and exact
run/selection/native identity before authentication, and compares its admission
digest over HTTP. The temporary upstream hostname is explicitly allowed. No
host port, protected route, service restart or8080 switch was made. Temporary
workers were removed after exact ownership/ID checks.

Final evidence root:
`D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/runtime-publication-recovery-20261026`.

| Artifact | SHA256 |
| --- | --- |
| `first-item-native-proof.json` | `b2f9df95073492fbdcc27da3726276b50c008dec5e60f1d3775c6b4f057a65bb` |
| `recovery-race-proof.json` | `0946abc950f8023261b94e7ca80baaa2e4816a501a340aa003c6e05f28a1d2e5` |
| `final-readback-proof.json` | `b725ad56369c310dc524e13b771021d185d25e126b98d2866b6b3c8621c2d117` |
| `original-preservation-after.json` | `bc2d8a5f42c4fc2c3806d9970e3fc210f7d180a1a64e9564b97ede5304d43186` |
| `../runtime-publication-20261026/auth-gateway-proof/proof.json` | `260a803dc6b7d709c9a92a414c194ce35ecc091dd0812c6b1a1fe1d7fa2177f6` |

All736 original fixture tables match their before fingerprints exactly. Final
accounted storage plus the existing512MiB reserve is3,852,200,695bytes, below4GiB.
The bounded first-item native evidence is complete for independent controller
review. This does not accept broader G2, whole-scope artifact/end-to-end delivery,
later owner variants, browser/cutover, latency or scale, and grants no adjacent
implementation release. The implementation remains b453a511; this supplement
changes evidence/documentation only.
