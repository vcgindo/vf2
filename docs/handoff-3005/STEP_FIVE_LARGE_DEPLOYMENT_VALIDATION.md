# VectorFLOW — manual local build and CSV execution

Use [the root runbook](../../RUNBOOK.md) for the complete clone, environment parameters, build/install/start, initialization and daily-run commands. All generic defaults and the optional local bridge YAML now come from the cloned repository.

The current Windows environment was inspected on 29 October 2026: the existing manual checkout is `I:/VectorFLOW` on 8080; the separate V2 checkout is `D:/VectorFLOW-Small` on 8091. Keep their databases, input bindings and private configuration separate. The root runbook uses a new `I:/VectorFLOW-8089` checkout and copies the unbound V3 package into its default `data/input` directory. Execution records default to `data/operations`.

Port 8089 and the example optional subnet `100.127.240.32/27` were unused when checked against current Docker, Windows and WSL state. Recheck the subnet if a VPN/network changes or another installation uses it. No inherited external trial YAML, build-image override, initialized binding or old `.env` belongs in this fresh installation.

V3 opens on 7 April 2026. Run its supplied dates in order: **2026-04-08**, **2026-04-09**, **2026-04-10**, **2026-04-11**. Wait for each daily command to return **PUBLISHED** before the next command or browser check. The completed captured-input recovery is retained evidence; this fresh build/initialization/browser run has its own timings and outcome.
