# VectorFLOW operator runbooks

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

- Fresh Git clone → Compose build → one blank-install command → Compose up: [release/SOURCE_BUILD.md](release/SOURCE_BUILD.md).
- Retained prebuilt image package and separate native data onboarding: [release/RUNBOOK.md](release/RUNBOOK.md).

Installation creates a blank application. Loading masters/opening and executing a daily run are separate operations. The former root development procedures are retained in Git history, not an alternative production installation route. Existing services and databases must not be reset or replaced by copying an old procedure.
