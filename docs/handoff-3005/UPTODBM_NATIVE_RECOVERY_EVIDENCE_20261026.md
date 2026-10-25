# Native UptoDBM recovery evidence — 26 October 2026

This appendix records evidence, not a new execution queue or scope release.
`F:/freshvcf/docs/handoff-3005/TRACKER.md` remains the sole status authority.
The full shared lifecycle goal is incomplete.

## Qualified native interruption boundary

Human approval `call_b3ea06a1f0df495d87b7e577a8ee7741` authorized a separately
initialized stockout test, its explicit TEST dispositions, one intentional
worker exit after BPR, exact fencing and frozen recovery. It used the unchanged
native release `a83ed4b8d24a38f888de1697d584a7c6fd4519cc`, image
`sha256:5d000e2a8a551808a98c2a409749ebd399f43b39e6d010b45839bba8c3c1920d`.

The test's own 23 October predecessor is
`08fb80da-28e5-4758-b775-57459235e9a9`. Complete comparison with the retained
canonical-roster predecessor found exactly one expected difference:
`Lineage.initialization_id`. All business values matched. The independent
initialization identity was retained, not normalized in stored outputs.

The 24 October run is `f1969f82-b703-48b4-9827-90f85047f563`. An external proof
driver terminated its own native process with exit code 86 at the call into
DBM, after accepted BPR and its files. Native product files were not patched.
The host observed the terminal exit, absent worker container and zero remaining
database clients before fencing; the checkpoint marker alone was insufficient.

- Unfenced retry was denied while attempt
  `2e06d096-4687-42cf-9801-983fd97c7786` remained ACTIVE.
- The packaged fencing command marked that exact attempt FAILED using its
  inspected worker token. A subsequent release with the old token was denied.
- Recovery attempt `01ca7e77-0fc7-4e40-82af-8f776330aea5` reached RELEASED on
  the same captured run. PRE_BPR/BPR identities, snapshot digests, frozen input,
  predecessor output and existing files remained exact; one DBM was accepted.
- A released repeat made zero `prepare_day`, `produce_bpr` and `produce_dbm`
  calls and preserved run, phase, attempt, command, read-reference and master
  revision headers.
- Exact ordered typed readback verified DBM state, eight BOR history rows,
  eleven RRR history rows and the ten-member InputData archive. NULLs and
  duplicate ordering were included.

This qualifies one same-release abrupt-exit boundary. It does not qualify
other interruption windows, an old process attempting a delayed commit,
arbitrary cross-release recovery, paired native Full/split equality or scale.

## Positive action qualification remains unproved

The recovered stockout trial computed no current suggestions. Its declared
consumption of 11 and 40 with zero stock triggers canonical spike suspension:
the thresholds are `CEILING(Norm/3)`, respectively 4 and 12. Both pairs receive
reason 2048 and disabled red flags. The positive expectation failed; no Apply
or Sleep action was executed. The failed assertion and diagnostic rows remain.

Human approval `call_d44a754951074860b6ffb06683736d84` then authorized a separate
balanced two-day low-stock fixture. Its 23 October predecessor
`0b18b6e5-d48f-4c82-b6d9-208ef211894f` completed, but the pre-successor check
found supply-issue suspension, reason 128, for both intended targets.

An independent read-only review traced the exact approved 24 October facts
through canonical `10. SupplyIssue.sql`, lines 27–87:

| Pair | Norm / RLT | Receipts, 22–24 Oct | Required receipts | Stocks, 22–24 Oct |
|---|---|---|---|---|
| SEASON / WH8 | 12 / 3 | 0 + 1 + 1 = 2 | 4 | 1, 2, 0 |
| Z9 / PARENT | 36 / 3 | 0 + 0 + 0 = 0 | 12 | 3, 3, 0 |

Neither has stock strictly above two-thirds Norm to exclude it from the supply
rule. The rule replaces nominated memberships with disabled current-day rows
before evaluating receipt-based release. Neither receipt total can release its
membership. A disabled predecessor is not universally disqualifying: sufficient
successor receipts can release it before Rule 1. These exact facts cannot.

The low-stock trial therefore stopped before any 24 October capture or
calculation. Its predecessor, inputs and failure evidence are retained. No
further fixture, settings change, recommendation seeding or assertion weakening
was used to obtain positive coverage. The two positive-fixture designs were
insufficient; this is not evidence of a business-rule defect. A future positive
scenario needs complete eligibility analysis before another execution decision.

## Evidence and preservation

Evidence root:
`D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/uptodbm-private-20261025`.

- `positive-stockout-test/bounded-recovery-result.json` consolidates the actual
  exit/fence/recovery, released repeat, typed history and failed expectation.
- `positive-stockout-test/post-recovery-complete-diagnostic.json` retains the
  complete typed DBM state used to explain spike suppression.
- `low-stock-positive-test/eligibility-gate-result.json` records the exact
  supply-rule assessment and confirms that only its predecessor exists.
- `low-stock-positive-test/prior-native-trials-preservation.json` and
  `private-preservation-proof.json` verify earlier native trials, database
  identities, old copied-run headers and global role attributes.
- `protected-source-after-lowstock.json` verifies source HBA and owner headers,
  zero replication slots/workers, and unchanged 8080 readiness response.
- `low-stock-positive-test/bounded-test-stop-proof.json` confirms the private
  PostgreSQL container stopped with identical mounts and its volume retained.

Measured retained private storage/evidence was 2,759,269,093 bytes, below 4 GiB.
PG remained at 384 MiB/0.5 CPU; one worker at most used 4 GiB/2 CPU with no ports.
Serving 8080, accepted earlier runs, frontend visual design and MTO API were
unchanged. No browser, positive action, UI-latency, production configuration,
large-data deployment or whole-lifecycle acceptance follows from this appendix.
