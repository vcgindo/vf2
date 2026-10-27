# VectorFLOW: retain build intermediates within the same allocation

**Superseded by the direct human practical-sizing direction on 28 October 2026. No approval is pending for this redistribution.** The human authorized sufficient bounded RAM and disk for the already approved isolated proof, based on actual capacity. See the current profile in `PRODUCTION_SCOPE_EXECUTION_PROPOSAL.md`. The measurements below remain the reason to preserve and charge builder intermediates; their old slices no longer govern execution.

Fresh inspection measured the retained MTA image at **285,976,387 bytes**, its unchanged Python base at **195,357,458 bytes**, and retained native application files at **10,052,715 bytes**. The roughly 80 MB remaining difference is predominantly installed dependencies. The canonical multistage build can retain that installation in a builder container as well as an image layer. Therefore the approved **64 MiB worker/container writable slice is too small for conservative retention of build intermediates**. The normal build helper also requests automatic intermediate removal; this proof will instead retain them, including a failed builder.

Reallocate the existing **2,048 MiB** operation budget as follows:

| Slice | Approved MiB | Revised MiB |
| --- | ---: | ---: |
| Candidate images and all newly attributable image layers | 1,024 | **640** |
| Build cache and export/context files | 128 | 128 |
| Five small databases, excluding WAL | 480 | 480 |
| WAL | 64 | 64 |
| Compressed evidence and diagnostics | 128 | 128 |
| All retained build/proof/container writable files, allocated container directories and bounded logs | 64 | **448** |
| Private inputs/configuration/secrets | 64 | 64 |
| Unspent operation reserve | 96 | 96 |
| **Total** | **2,048** | **2,048** |

The additional 384 MiB writable allowance comes entirely from the image slice. Count every new image layer once by its independently measured RootFS identity, with existing shared prefixes pinned before the build. Count every retained container's writable and allocated directory bytes separately, conservatively even if a committed image layer shares those contents. No failed or intermediate artifact is excluded. An operation must fit both slices and the unchanged total before it starts; permission for at most two candidate builds does not guarantee that both will fit.

The total ceiling stays **8,116 MiB**, cumulative growth **4,420 MiB**, global reserve **512 MiB**, frozen Step 4 reservation **192,686,244 bytes**, original baseline **3,853,159,872 bytes**. All previous spending remains charged. PG384MiB/0.5CPU and one worker4GiB/2CPU remain unchanged. The builder's active RUN steps will also have explicit 4GiB memory, equal memory-plus-swap limit, and 2CPU limits. Retain intermediates with no forced removal, cleanup or prune.

All other limits and the finite proof in `PRODUCTION_SCOPE_EXECUTION_PROPOSAL.md` remain binding: five isolated normal-name databases, ten logical two-date days/fourteen producing invocations, at most two conditionally permitted candidate builds, no additional business facts, no Terra execution, no frontend/auth/browser/public port or fast8080 change.

**Approve this same-total slice correction:** images 640 MiB and writable/container artifacts 448 MiB; all other approved slices, resource caps, preserved baselines and proof boundaries unchanged. Committed source `2c5add0656434bcc7119fb884b1e9cce713cd865` and non-build preparation can continue while this specific decision is pending.
