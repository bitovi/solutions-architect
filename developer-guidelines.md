# Developer Guidelines

This document defines the workflow developers follow when making changes across our system. It applies to all feature work, bug fixes, and refactors that touch one or more service repositories.

## System Overview

Our system is composed of multiple service repositories. The one most important is `api-tests` which contains the overall integration tests to validate overall system behavior.

---

## Workflow

Every change follows a strict **test-first, incremental implementation** cycle. The three phases are:

1. **Write failing integration tests** (`api-tests`)
2. **Implement across service repos** (in dependency order)
3. **Run, diagnose, and refine** (feedback loop)

*************************************************
TODO: STEPS TO RUN THE TESTS
    - how are repos updated?
    - how are tests executed?
    - what about cross-repo infra?
    - i think this should all be delegated to actions that can be invoked by mcp or local scripts in here to run the tests in the cloud
    - need to decide where the temp code is living during work. probably a same-name branch in each repo
    - a temporal workflow could iterate on progress by running the cli or other github agents in each repo and then running the integration tests each time to create a feedback loop
*************************************************

### Phase 1 — Update Integration Tests

Before touching any service code, update the `api-tests` repository to describe the **new expected behavior**.

1. Read the relevant operation plan in `operations/` to understand the contract changes (new fields, updated request/response shapes, changed calculations).
2. Add or modify integration test cases in `api-tests` that assert the new behavior end-to-end.
3. Commit the updated tests. This snapshot captures what "done" looks like before any implementation begins.

> The goal is to define a baseline of when the services are working together as expected.

### Phase 2 — Implement Across Service Repos

With failing integration tests in hand, implement the changes in each service repo. The operation plan specifies a suggested implementation order by the numbering of each file. The filename suggests what repo needs to be updated.

For **each** repo in the sequence:

1. **Read the operation plan section** for that repo to understand the exact changes: schema updates, new fields, logic changes, and affected files.
2. **Update the repo's local tests first** (unit tests, contract tests, e2e tests) to reflect the new behavior within that service. These local tests should also fail initially.
3. **Implement the code changes** to make the local tests pass.
4. **Run the local test suite** and confirm all local tests pass before moving to the next repo.

Repeat for each subsequent repo in the dependency chain.

### Phase 3 — Feedback Loop (Test and Refine)

Once all repos have been updated:

1. **Run the full integration test suite** (`api-tests`) against the running services.
2. **Diagnose failures.** Integration test failures at this stage typically indicate:
   - A contract mismatch between services (field name typo, wrong type, missing `omitempty`/`@IsOptional`)
   - A logic error in one service's calculation or data passing
   - A configuration issue (wrong service URL, missing auth header forwarding)
3. **Fix the issue in the appropriate repo**, re-run that repo's local tests, then re-run the integration tests.
4. **Repeat** until all integration tests pass.

This loop is where the bulk of debugging happens. Keep iterations tight — fix one thing, test, assess.

---

## Workflow Summary

```
┌─────────────────────────────────────────────────┐
│  1. Update api-tests with new expected behavior  │
│     → Tests should FAIL                          │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│  2. For each repo (in dependency order):         │
│     a. Update local tests (should FAIL)          │
│     b. Implement code changes                    │
│     c. Local tests PASS → move to next repo      │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│  3. Run integration tests                        │
│     ├─ All pass → DONE                           │
│     └─ Failures → Diagnose, fix, loop back       │
└─────────────────────────────────────────────────┘
```

---

## Key Principles

- **Integration tests are the spec.** They are written before implementation and define when the work is complete. This might not be correctly updated on the first try but will be refined/fixed in the later phases (typical TDD loop).
- **Local tests mirror the integration expectation.** Each repo's local tests should cover that repo's slice of the new behavior. When all local tests pass across all repos, the integration tests should also pass (or be very close). Some behaviors might not be feasible in local tests, requiring complex mocks, and those can be validated in the integration tests only.
- **Small, verifiable steps.** Implement one repo at a time. Confirm local tests pass before moving on. Don't try to implement everything at once and debug a wall of failures.
- **The feedback loop is normal.** Expect to go through multiple cycles of integration test → diagnose → fix. Cross-service changes rarely work perfectly on the first pass.
