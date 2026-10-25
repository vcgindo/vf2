# Retained TEST PostBPR delivery — 25 October 2026

This appendix records the bounded implementation and observed delivery. The sole status authority remains `F:/freshvcf/docs/handoff-3005/TRACKER.md`. It does not release UptoDBM, PostDBM, production configurations, or G3 continuous-availability work.

## Approved completion and preserved calculation

Human decision `call_018484042fc542ebab4ab493e37e00cb` approved late completion of the omitted BPR allocation histories and explicit dispositions for this retained SUPPLIED-INSTANCE TEST run. The original accepted BPR receipt and snapshot were not rewritten. The supplementary completion is recorded as late; the original UptoBPR stop is not retroactively described as including it.

| Owner | Identity |
|---|---|
| Same run / date | `e0735ad3-b98d-45c5-9bad-38bc5b0e5df8` / 24 October 2026 |
| Preserved BPR | `486ffe8a-ae78-4de9-90e5-0f01eb6ede97`, digest `863bcc7fd80bd4089bee87142afddc5fe1d8d1da840f099819e5efe9f486006d` |
| Supplementary history | `987e8b6b93d8da2d85a304e4a26bd77b0d7722c58faffaa1631c11018ad432a3` |
| PostBPR attempt | `d7aa7e71-20c5-4d36-bb92-e88e17d6246f` |
| DAY_FINAL | `5c76e0af-e459-45c5-871e-d4fba63564b1`, digest `75e66087f102219ab1cc0192737b2ef3c8de125182564941cb66e9c31e0542ce` |
| Terminal output | `63e61ba736f163d188a9364a537efb3087d719481cc2ddfb80edd6d5213ee904` |

The retained predecessor's 4 BOR and 5 RRR allocation-history rows were combined with the accepted current populations under the canonical 90-day rules, yielding exactly 8 BOR and 10 RRR rows. Typed immutable ownership, rollback, idempotence, guard coverage and unchanged ingestion epochs were verified. Terminal publication reused this completion rather than appending the history again.

PostBPR ran once on the same accepted day. Intake, BPR, Pick and InputData were not replayed. The original failed attempts, successful predecessor, Full49, eight scoped commands, action revision12, original phase files, BPR remark and reference remain preserved. The terminal next opening equals the accepted closing state; no next day was executed.

The earlier Apply was consumed by canonical DBM suspension processing: the target's acceptance table is empty, and its stock suspension contains DeltaNorm12, start24-Oct and wait-until27-Oct. The master Norm remains36. This is not a claim that it became48, nor an implementation change to make it do so.

## Serving identity

| Boundary | Active identity |
|---|---|
| MTA source | `a9b1c053f9988319f9aba8085978be8dd2479efa` |
| MTA image | `sha256:7a517dd29dfbf8981d5b5fa40e3f6a905c4da6b1fb988fa205b51c190871d8c9` |
| MTA container | `vectorflow-mta-postbpr-a9b1c053`, ID `6cd5d3a11ebb64c2b0b30727490b0928267f8237e32663adc840d0fd159aa6bd` |
| PostgreSQL | Same owned `vftest_fresh_lifecycleg2_uptobprui_20261025`, OID402363, schema223 |
| Native selection | `postbpr-terminal-selection-a9b1c053.json`, selection digest `34133afa49d53ce0532468e6ac547b155071d47eacc26bcd84888f0a2a7d0dc3` |
| Publication | 20/20 READY; seal `db3cdbff42dfcc5f1e64f5a1d6d4eee86e35e0b6906cca767b91bf2f6d10c8a7` |
| Original configuration | `8c5d0744cd920f1e68ead239ce4b1bfa77d43600824330a3ccdba89e664d7d3d` |
| Planning summary | `aede579d-75d4-4de4-a2e8-3f0d4021e792`, digest `3cb72fabdb3c967bc1b98f1e743ad1c558e55808bdb005cac068663547759ccc` |

Only the MTA backend alias was transferred. Auth remains container `5fddae62c1bc1d7eb4c5b5e2a2ebd23b51784f3e8729be3188ae5d2224ebef02`, with its original start time. Frontend assets, visual design, gateway configuration and MTO are unchanged. Previous MTA containers are stopped and retained. No public port was added.

The original five prepared-reader flags and immutable configuration remain unchanged. A rejected attempt to edit that configuration rolled back completely. The final code selects existing validated prepared readers only for this exact completed TEST owner. Startup still requires the full sealed publication and summary; each reader retains its own receipt checks. No guard was bypassed or receipt rewritten.

## Verification

All evidence paths below are relative to `D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/`.

| Proof | Result / evidence |
|---|---|
| Migration and ownership | `bpr-history-rollback-proof-v3.log`, catalogue proof-v2, supported schema activation-v2; guard coverage and ingestion epochs preserved |
| Native computation/readback | `postbpr-native-execution-024d2d3b.log`, `uptobpr-ui-evidence/postbpr-terminal-readback.json`; full input/output and exact history/action/next-opening checks |
| Focused reader tests | 56 PASS in `postbpr-reader-mode-tests.log`; includes unchanged configuration and wrong-owner/status/completion rejection |
| Final publication | `postbpr-readmode-selection.log`; full native audit, all20 layers and summary readback, exact atomic selection |
| Served report APIs | `postbpr-final-http.log`; Planning, BPR8, BTR8, DBM empty, RRR4, BOR1, BOROA1, RRROA5, InTransit1 and empty OpenRequests; scope checks |
| History APIs | `postbpr-final-history-http.log`; daily graph, historical availability and selected research history succeed |
| Original downloads | Same final HTTP proof; four Pick CSVs, InputData.zip and BOR_OrderAllocation.csv return original checksums; missing entitlement and empty BOR scope return403 |
| Apply consumption | `postbpr-action-consumption-readback.log`; read-only canonical suspension result described above |
| Actual restart | `postbpr-final-restart-proof.json`; same selection, auth process unchanged, readiness restored in29.814s |
| Browser | `uptobpr-ui-evidence/postbpr-browser-proof.json`; Chrome extension only, normal fixture login, Planning charts/grid, BTR8, BPR8, DBM empty and download-link creation |

After the backend restart, the same authenticated Chrome tab reloaded Planning with its date and all quadrant counts in1.440s in one browser call. Counts were0/0,0/0,0,8. This is a small-fixture observation, not matched-load or general performance acceptance. Populated report API calls took0.32–0.903s; the six file calls took0.992–1.35s. API timings exclude browser rendering.

Final Pick and BOR browser requests created download links. The earlier human-confirmed arrival of all six original files remains retained; final browser filesystem arrival was not independently inspected. No post-terminal Apply/Sleep mutation was performed.

## Retained limits

- The implementation is qualified only for this exact retained TEST run and its successful predecessor without terminal actions. Initialization-owned BTR and other predecessor cases are not newly qualified.
- PreDBM, PostDBM, PostBTR and site-final hooks are explicit test-only no-ops. Optional BTR30/60/90 and location file exports, post-backups and outbound DBM/finish emails are explicitly excluded. Required captured calculations, populations, histories and native completion checks remain required.
- RuntimeReports is the explicitly approved empty test roster. Missing production configuration was not defaulted.
- Existing UptoBPR limitations on unqualified writes, legacy GIT behavior and earlier browser action evidence remain applicable. Completing allocation history does not establish arbitrary history editing or new site behavior.
- No whole-application, matched-scale, uninterrupted replacement or general production acceptance is claimed. Empty states were checked on the exercised surfaces; this does not certify every UI route.

The standalone PostBPR command reports computation completion separately from downstream application delivery. Its original computation result is retained; later selection, serving and browser proofs in this appendix are not a rewritten calculation receipt.
