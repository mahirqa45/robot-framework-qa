# Test strategy and architecture decisions

## Scope
The release unit is one version of the synthetic order application across Atlas, Beacon, and Cedar. Required IDs are versioned in policies/release.json. Client profiles live separately from the independent test expectations, so a changed profile cannot silently change both the implementation and its oracle.

## Risks and checks
| Risk | Evidence |
|---|---|
| Incorrect discounts, taxes, or rounding | Independent expected amounts through the HTTP API |
| Privilege mismatch | Positive and negative simulated-role checks |
| Cross-client order leakage | Every other client must receive 404 for an existing order |
| Data loss | API/SQLite comparison and reopen-database integration test |
| Invalid input acceptance | Boundary, type, boolean-as-integer, and malformed JSON checks |
| Incorrect approval routing | Checks immediately on either side of the effective threshold |
| False green release | Adversarial policy tests for missing/duplicate/skipped/inconsistent evidence |

## Decisions
1. Standard-library dependencies keep the first slice reproducible and offline-capable. pytest and Robot Framework adapters can be introduced when their additional capabilities are needed.
2. HTTP checks exercise transport and business logic together; direct SQLite reads are deliberately limited to persistence evidence. The collector owns its isolated server and ephemeral database.
3. Integer currency avoids binary floating-point errors. The sample defines explicit half-up rounding; this is a demo business rule rather than a universal accounting rule.
4. Policy is fail-closed. Unexpected checks also block to expose manifest drift. A future optional-test model requires an explicit policy extension.
5. Each run produces immutable-by-convention JSON artifacts and an escaped HTML report. Evidence is not cryptographically signed; audit-grade integrity is outside this version's scope.
6. Client CI jobs are scoped smoke evidence. A separate full run certifies the complete release; no implicit aggregation can hide missing matrix jobs.
7. No retries are executed by the collector. The gate already evaluates retry histories conservatively for future adapters.

## Acceptance experiment
Run quality.demo. Baseline must pass, enabling the Beacon discount defect must block with Beacon pricing failing and no other client failures, and disabling the defect must pass. The experiment is a regression-detection demonstration, not a mutation coverage measurement.

## Next milestones
- Add Robot Framework browser journeys against a minimal order UI, with common result schema and retained screenshots.
- Add schema validation and adapters for independent runners; preserve execution errors and original artifacts.
- Introduce test history, measured flaky-test candidates, and labeled failure grouping.
- Map changed modules to required tests; unknown change paths must trigger full regression.
- Publish a reproducible walkthrough and measure timings on a documented machine. Avoid extrapolating synthetic results to employer savings.

## Limitations
Role input is a simulation, not authentication. The sample has no real users, network identity boundary, full production security checks, load tests, frontend, historical dashboard, or AI triage. Release-gate PASS only establishes the configured checks passed; it does not establish absence of defects.
