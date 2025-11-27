# Agentic Codebase Refactor Prompt

## Mission

Perform a **systematic, autonomous refactoring** of an existing codebase to reduce technical debt, improve code quality, and ensure maintainability. Execute the full refactoring lifecycle from analysis to completion without requiring user intervention.

---

## Critical Execution Rules

### Autonomy Requirements

1. **DO NOT ASK** - Execute all identified refactoring items without asking permission. You have authority to address all P1-P4 items.
2. **COMPLETE THE CYCLE** - A refactor is not complete until the post-refactor report exists. Never stop after "the code is done."
3. **MAINTAIN MOMENTUM** - After completing one item, immediately proceed to the next. Do not pause for confirmation between items.

### Mandatory Deliverables

The refactor produces exactly TWO reports:

| Report | Purpose | When Created |
|--------|---------|--------------|
| `REFACTOR_BASELINE_REPORT.md` | Snapshot of codebase BEFORE refactoring | First, before any changes |
| `REFACTOR_COMPLETION_REPORT.md` | Snapshot of codebase AFTER refactoring | Last, after all changes |

**CRITICAL: The completion report MUST mirror the baseline report structure exactly.** Every section, every table, every metric in the baseline must have a corresponding entry in the completion report for direct comparison.

---

## Phase 1: Baseline Analysis

Create `REFACTOR_BASELINE_REPORT.md` with these sections:

### Required Sections

1. **Test Coverage Analysis**
   - Overall coverage percentage
   - Total tests and pass/fail status
   - Per-module coverage table

2. **Code Complexity Metrics**
   - Cyclomatic complexity summary (A/B/C/D/E counts)
   - Average complexity score
   - Functions with highest complexity (B+ rated)
   - Maintainability index per module

3. **Dependency Analysis**
   - Module coupling metrics (afferent/efferent/instability)
   - Circular dependency detection
   - External dependencies list

4. **Lines of Code**
   - Source lines
   - Test lines
   - Total lines

5. **Architectural Issues**
   - God classes (>500 lines)
   - Long methods (>50 lines)
   - Medium methods (30-50 lines)
   - Deep nesting (>4 levels)

6. **SOLID Violations**
   - SRP violations with location
   - OCP/LSP/ISP/DIP concerns

7. **Dead Code / Unused Code**
   - Potentially unused items
   - Definitely unused items

8. **Linting Status**
   - Linter results

9. **Technical Debt Inventory**
   - Prioritized table (P1-P4) with severity, effort, and notes

10. **Summary & Recommendations**
    - Overall health assessment
    - Recommended priority order

---

## Phase 2: Execute Refactoring

### Execution Order

1. **P1 items first** - Critical bugs/issues
2. **P2 items second** - Architecture improvements  
3. **P3 items third** - Code cleanup
4. **P4 items last** - Nice-to-have improvements

### TDD Requirements

For each refactoring item:

1. **RED**: Write failing test (if adding new component)
2. **GREEN**: Implement minimal code to pass
3. **REFACTOR**: Clean up while keeping tests green

For behavior-preserving refactors, existing tests serve as the safety net.

### Commit Requirements

- Atomic commits: ≤50 lines OR 2-3 TDD tests per commit
- Run linter before every commit
- Commit message format: `<type>: <description>`

### DO NOT

- Ask "should I continue?" between items
- Ask "what would you like to do next?"
- Stop after completing code changes
- Create reports with different structures

---

## Phase 3: Completion Report

**IMMEDIATELY after completing all refactoring items**, create `REFACTOR_COMPLETION_REPORT.md`.

### Structure Requirements

The completion report MUST contain:

1. **IDENTICAL section structure** to the baseline report
2. **Side-by-side comparison data** showing baseline vs. post-refactor values
3. **Change indicators** (+/- or ✅) for improved metrics

### Required Sections (mirroring baseline)

1. **Test Coverage Analysis**
   - Same table format as baseline
   - Add "Baseline | Post-Refactor | Change" columns

2. **Code Complexity Metrics**
   - Same table format as baseline
   - Show before/after for complexity counts
   - Show before/after for average complexity
   - Show before/after for maintainability index

3. **Dependency Analysis**
   - Same table format as baseline
   - Note any new modules or changed coupling

4. **Lines of Code**
   - Same table format as baseline
   - Show before/after counts

5. **Completed Items**
   - Table of all P1-P4 items with status and commit hash

6. **Architectural Changes**
   - New components created
   - Methods refactored
   - SOLID violations addressed

7. **Files Changed**
   - List of all modified/created files

8. **Remaining Technical Debt**
   - Any items deferred with justification

9. **Verification**
   - Test results
   - Coverage results
   - Linting results

10. **Commits**
    - Ordered list of all commits made

---

## Completion Criteria

The refactor is COMPLETE when:

- [ ] All P1-P4 items addressed (or explicitly deferred with justification)
- [ ] All tests passing
- [ ] Coverage maintained or improved
- [ ] No linting errors
- [ ] `REFACTOR_BASELINE_REPORT.md` exists
- [ ] `REFACTOR_COMPLETION_REPORT.md` exists
- [ ] Completion report structure mirrors baseline report exactly
- [ ] Final commit made for completion report

---

## Anti-Patterns to Avoid

| Anti-Pattern | Correct Behavior |
|--------------|------------------|
| "Should I proceed with P2 items?" | Just proceed. You have authority. |
| "What would you like to do next?" | Check the technical debt inventory and do the next item. |
| "The refactoring is complete." (without report) | Create the completion report THEN declare complete. |
| Completion report with different sections than baseline | Mirror the baseline structure exactly. |
| Asking for permission to create the completion report | Just create it. It's a mandatory deliverable. |

---

## Example Flow

```
1. Create REFACTOR_BASELINE_REPORT.md
2. Address P1 items → commit each
3. Address P2 items → commit each
4. Address P3 items → commit each
5. Address P4 items → commit each
6. Create REFACTOR_COMPLETION_REPORT.md (mirroring baseline structure)
7. Commit completion report
8. Declare refactor complete
```

No user interaction required between steps 1-8.
