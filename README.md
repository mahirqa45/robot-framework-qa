# Release Quality Platform

An engineering portfolio project for evaluating release readiness across client-specific business configurations.

**Status:** Design phase. The capabilities below are planned; there is no executable platform yet.

## Problem
A global pass percentage can hide a critical failure affecting one client. Release decisions need evidence of required coverage, completed execution, business impact, and reliable test results.

## First demonstration
A synthetic order-management application supports three fictional clients:
- Atlas: standard pricing and basic order permissions.
- Beacon: negotiated discounts and approval thresholds.
- Cedar: regional tax rules and restricted roles.

Introduce a Beacon discount regression. Tests should detect the incorrect amount, preserve the evidence, and block that release. Correct the defect, rerun the required checks, and demonstrate a passing gate. Use deterministic fixtures and integer minor currency units.

## Planned architecture
- Sample application: Python service, minimal UI, SQLite persistence, and deterministic seed data.
- Test adapters: pytest for API and data checks; Robot Framework for selected business journeys.
- Configuration: versioned client profiles and test-to-requirement mappings.
- Result ingestion: normalize results into a shared schema while retaining original reports.
- Policy engine: evaluate per-client release gates and produce machine-readable decisions.
- Reporting: a static HTML report first; interactive history and triage later.
- CI: GitHub Actions runs the client matrix and preserves evidence.

## Initial gate policy
A release passes only when every required client and test is accounted for, execution completes, and all required checks pass.
- Required test failed: BLOCK.
- Required test missing, skipped, or duplicated: BLOCK.
- Unknown result status, malformed evidence, or execution error: BLOCK.
- Missing expected client: BLOCK.
- Retry passes do not erase an initial failure; retry history is retained.
- A high overall pass rate cannot override a required failure.

A gate is a configurable decision aid, not proof that a release is defect-free.

## Build milestones
1. **Working vertical slice:** sample application; three client fixtures; pricing and permission API tests; result normalization; release gate; CI evidence; deliberate-defect demonstration.
2. **Business workflow coverage:** Robot Framework order and approval journeys; persisted-data checks; screenshots and traceable requirement IDs.
3. **History and reliability:** immutable run records; repeated-failure grouping; flaky-test candidates; investigation evidence.
4. **Risk-based selection:** explicit component-to-test mappings, mandatory critical tests, and full-suite fallback for unknown changes.
5. **Portfolio polish:** architecture decisions, measured experiments, walkthrough, and reproducible setup.

## Intended structure
- `app/`: sample application and fixtures
- `clients/`: client configurations
- `tests/api/`, `tests/ui/`, `tests/data/`: test suites
- `quality/`: result adapters and policy engine
- `policies/`: gate rules and required-test manifests
- `docs/`: strategy, decisions, and demonstrations
- `reports/`: generated output, excluded from source control
- `.github/workflows/`: automated validation

## Evidence and measurement
Measure execution time, detection of deliberately introduced defects, and triage grouping accuracy against labeled examples. Label all benchmark data as synthetic. Report observed results and limitations; do not claim production savings or employer outcomes.

## Engineering standards
Use synthetic data and fictional clients. Keep secrets outside the repository. Test the policy engine against absent results, inconsistent statuses, client isolation failures, and boundary conditions. Keep dependencies reproducible and document design tradeoffs.

## Working branch
Development begins on `feature/ui-automation`. Despite the original branch name, this project covers release quality across API, UI, and data layers.
