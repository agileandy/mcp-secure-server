# Agentic Codebase Refactor Prompt (v2.0)

## Mission

Perform a **systematic, autonomous refactoring** of an existing codebase to reduce technical debt, improve code quality, and ensure maintainability. Execute the full refactoring lifecycle from research to completion, producing a **detailed action plan** that supports execution across multiple coding sessions without context loss.

---

## Critical Execution Rules

### Autonomy Requirements

1. **DO NOT ASK** - Execute all identified refactoring items without asking permission. You have authority to address all P1-P4 items.
2. **COMPLETE THE CYCLE** - A refactor is not complete until the post-refactor report exists. Never stop after "the code is done."
3. **MAINTAIN MOMENTUM** - After completing one item, immediately proceed to the next. Do not pause for confirmation between items.
4. **LEVERAGE PARALLELISM** - Use sub-agents for independent analysis tasks (see Phase 1) and independent refactoring items (see Phase 3).

### Report Output Directory Structure

All refactor artifacts MUST be written to a timestamped directory structure:

```
.refactor/
└── YYYYMMDD-HHMMSS/
    ├── REFACTOR_BASELINE_REPORT.md
    ├── REFACTOR_ACTION_PLAN.md
    └── REFACTOR_COMPLETION_REPORT.md
```

**Directory Creation:**
1. Create `.refactor/` in the project root if it doesn't exist
2. Create a timestamped subdirectory using format `YYYYMMDD-HHMMSS` (e.g., `20251127-143022`)
3. Write all artifacts to this timestamped directory
4. Add `.refactor/` to `.gitignore` if reports should not be committed, OR commit the reports for historical tracking

**Session Resume:** When resuming a refactor, use the MOST RECENT timestamped directory (sorted lexicographically).

**Rationale:** This structure enables:
- Multiple refactor cycles on the same codebase over time
- Historical comparison between refactor sessions
- Clean separation of refactor artifacts from source code
- Session resumability without filename conflicts

### Mandatory Deliverables

The refactor produces exactly THREE artifacts in the timestamped directory:

| Artifact | Purpose | When Created |
|----------|---------|--------------|
| `REFACTOR_BASELINE_REPORT.md` | Snapshot of codebase BEFORE refactoring | Phase 1, before any changes |
| `REFACTOR_ACTION_PLAN.md` | Detailed, session-resumable action plan | Phase 2, after baseline |
| `REFACTOR_COMPLETION_REPORT.md` | Snapshot of codebase AFTER refactoring | Phase 4, after all changes |

**CRITICAL:** The completion report MUST mirror the baseline report structure exactly. Every section, every table, every metric in the baseline must have a corresponding entry in the completion report for direct comparison.

---

## Phase 0: Research Current Best Practices

**MANDATORY FIRST STEP** - Before any code analysis, research current best practices for the codebase's primary language.

### Research Requirements

1. **Web Search** - Perform web searches for:
   - `"{language} refactoring best practices {current_year}"`
   - `"{language} code quality tools {current_year}"`
   - `"{language} performance optimization patterns"`
   - `"{language} security best practices"`
   - `"{language} exception handling patterns"`

2. **Document Findings** - Include a "Research Findings" section at the top of the baseline report containing:
   - Current recommended static analysis tools
   - Current type checking standards
   - Current security scanning approaches
   - Performance profiling recommendations
   - Any language-specific refactoring patterns that have emerged recently

3. **Tool Verification** - Verify which recommended tools are available/applicable to this codebase and note any that should be added.

**Rationale:** Language ecosystems evolve. This step ensures the refactor applies current practices, not outdated patterns baked into a static prompt.

---

## Phase 1: Baseline Analysis

### Setup

1. Create the output directory: `.refactor/YYYYMMDD-HHMMSS/`
2. Record the current git commit hash as the baseline reference

### Parallel Analysis Strategy

Launch sub-agents in parallel to gather baseline metrics. Each sub-agent should focus on one analysis domain:

| Sub-Agent | Responsibility | Output |
|-----------|----------------|--------|
| **Coverage Analyzer** | Test coverage metrics, test type inventory | Coverage section data |
| **Complexity Analyzer** | Cyclomatic complexity, maintainability index | Complexity section data |
| **Dependency Analyzer** | Module coupling, circular dependencies, external deps | Dependency section data |
| **Architecture Analyzer** | God classes, long methods, deep nesting, SOLID violations | Architecture section data |
| **Security Analyzer** | Input validation, exception handling, error exposure | Security section data |
| **Performance Analyzer** | Async patterns, I/O blocking, memory management | Performance section data |
| **Type Safety Analyzer** | Type annotation coverage, type checker results | Type safety section data |

Consolidate sub-agent outputs into `.refactor/YYYYMMDD-HHMMSS/REFACTOR_BASELINE_REPORT.md`.

### Required Sections

#### 0. Research Findings (from Phase 0)
- Best practices discovered
- Recommended tools
- Language-specific patterns to apply

#### 1. Test Coverage Analysis
- Overall coverage percentage
- Total tests and pass/fail status
- Per-module coverage table
- Branch coverage analysis
- Test type inventory (unit, integration, e2e, property-based)

#### 2. Code Complexity Metrics
- Cyclomatic complexity summary (A/B/C/D/E counts)
- Average complexity score
- **ALL functions rated B or higher** (not just "highest") with file:line reference
- Maintainability index per module
- Cognitive complexity where tooling supports it

#### 3. Dependency Analysis
- Module coupling metrics (afferent/efferent/instability)
- Circular dependency detection
- External dependencies list with version constraints
- **Dependency health check** (outdated, deprecated, or vulnerable dependencies)

#### 4. Type Safety Analysis
- Type annotation coverage percentage
- Type checker results (mypy/pyright/equivalent for language)
- `# type: ignore` or equivalent suppression count
- Untyped function signatures list

#### 5. Exception Handling Analysis
- Bare `except` or equivalent anti-patterns
- Exception types caught vs. raised
- Error recovery patterns (retry, circuit breaker, fallback)
- Logging of exception context
- **Unhandled exception paths** in I/O operations (network, file, database)

#### 6. Security Analysis
- Input validation completeness
- Output encoding/escaping
- Path traversal prevention
- Injection vulnerability patterns
- Sensitive data exposure (logging, error messages)
- **Rate limiting and DoS protection review**

#### 7. Performance Analysis
- Synchronous I/O in async contexts
- Connection pooling usage
- Caching patterns and cache invalidation
- Memory management (cleanup, TTL, bounded collections)
- **N+1 query patterns** (if applicable)
- Resource cleanup (context managers, finalizers)

#### 8. Architectural Issues
- God classes (>500 lines)
- Long methods (>50 lines) - **MUST be refactored**
- Medium methods (30-50 lines) - **MUST be analyzed for SRP**
- Deep nesting (>4 levels)
- **Classes with >10 public methods** (SRP smell)

#### 9. SOLID Violations
- SRP violations with specific decomposition recommendations
- OCP violations with extension point recommendations
- LSP violations with inheritance hierarchy concerns
- ISP violations with interface segregation recommendations
- DIP violations with abstraction recommendations

#### 10. Dead Code / Unused Code
- Definitely unused (remove)
- Potentially unused (investigate, then remove or document public API status)
- **Unreachable code paths**

#### 11. Code Duplication
- Duplicated logic blocks (>10 lines)
- Near-duplicates that could be parameterized
- Copy-paste inheritance patterns

#### 12. Linting & Formatting Status
- Linter results (zero tolerance for errors)
- Formatter compliance

#### 13. Lines of Code
- Source lines
- Test lines
- Comment ratio

#### 14. Technical Debt Inventory

**Priority Definitions:**

| Priority | Definition | SLA |
|----------|------------|-----|
| P1 | Bugs, security vulnerabilities, missing dependencies | Must fix |
| P2 | Architecture violations (SRP, coupling), performance blockers | Must fix |
| P3 | Long methods, high complexity, exception handling gaps | Must fix |
| P4 | Code cleanup, dead code removal, nice-to-have | Should fix |

**Inventory Table Format:**

| ID | Item | Category | Severity | Effort | Priority | Location (file:line) | Acceptance Criteria |
|----|------|----------|----------|--------|----------|---------------------|---------------------|

**Categories:** Architecture, Complexity, Security, Performance, Exception Handling, Type Safety, Dead Code, Duplication, SOLID

#### 15. Summary & Recommendations
- Overall health assessment
- Risk areas
- Recommended priority order

---

## Phase 2: Action Plan Generation

**CRITICAL:** Generate a detailed action plan that enables **session-resumable execution**. Each action must be independently executable without requiring context from previous sessions.

### Create `.refactor/YYYYMMDD-HHMMSS/REFACTOR_ACTION_PLAN.md`

#### Structure Requirements

```markdown
# Refactor Action Plan

**Session Directory:** .refactor/YYYYMMDD-HHMMSS/
**Baseline Commit:** {commit_hash}
**Created:** {timestamp}

## Session Resume Instructions
To resume this refactor:
1. Navigate to `.refactor/` and find the most recent timestamped directory
2. Read this action plan
3. Check the "Status" column in the action table
4. Find the first "PENDING" item
5. Execute from that point

## Quick Status
- Total Actions: X
- Completed: Y
- Remaining: Z
- Current Phase: [P1/P2/P3/P4]

## Action Table

| ID | Debt ID | Action | Category | Files | Estimated Lines | Status | Commit Hash |
|----|---------|--------|----------|-------|-----------------|--------|-------------|
| A1 | D1 | Add httpx to pyproject.toml | P1-Dependency | pyproject.toml | 1 | PENDING | - |
| A2 | D2 | Extract RateLimiter from SecurityEngine | P2-SRP | security/engine.py, security/ratelimiter.py (new) | 80 | PENDING | - |
| ... | ... | ... | ... | ... | ... | ... | ... |

## Detailed Action Specifications

### A1: Add httpx to pyproject.toml
**Addresses:** D1 - Missing httpx dependency
**Category:** P1-Dependency

**Context:** (Enough context to execute without reading other files)
The websearch plugin imports httpx but it's not declared in pyproject.toml dependencies.

**Steps:**
1. Open pyproject.toml
2. Add `httpx>=0.27` to `[project.dependencies]`
3. Run `uv lock` to update lockfile
4. Verify with `uv run python -c "import httpx"`

**Tests:** N/A (dependency management)

**Acceptance Criteria:**
- [ ] httpx listed in pyproject.toml
- [ ] uv.lock updated
- [ ] `import httpx` succeeds

**Commit Message:** `fix(deps): add missing httpx dependency [D1]`

---

### A2: Extract RateLimiter from SecurityEngine
**Addresses:** D2 - SecurityEngine SRP violation (rate limiting responsibility)
**Category:** P2-SRP

**Context:**
SecurityEngine.check_rate_limit() and related state (_request_counts, _request_timestamps) 
should be extracted to a dedicated RateLimiter class.

**Pre-conditions:**
- All existing tests pass
- Understand current rate limiting behavior from tests

**Steps:**
1. RED: Write test_ratelimiter.py with tests for:
   - RateLimiter.check() returns True when under limit
   - RateLimiter.check() returns False when over limit
   - RateLimiter respects window expiry
   - RateLimiter.reset() clears state
2. GREEN: Create src/security/ratelimiter.py with RateLimiter class
3. GREEN: Implement minimal code to pass tests
4. REFACTOR: Update SecurityEngine to delegate to RateLimiter
5. Verify all existing tests still pass

**Files Changed:**
- src/security/ratelimiter.py (new, ~60 lines)
- src/security/engine.py (modified, -30 lines)
- src/security/__init__.py (modified, +1 line export)
- tests/test_ratelimiter.py (new, ~100 lines)

**Tests:**
- New: 10-15 unit tests for RateLimiter
- Existing: All SecurityEngine tests must pass unchanged

**Acceptance Criteria:**
- [ ] RateLimiter class exists with single responsibility
- [ ] SecurityEngine delegates to RateLimiter
- [ ] 100% coverage on new RateLimiter
- [ ] All existing tests pass
- [ ] No behavior change (characterization tests verify)

**Commit Message:** `refactor(security): extract RateLimiter from SecurityEngine [D2]`

---
(Continue for all actions...)
```

### Action Plan Requirements

1. **Self-Contained Actions** - Each action specification must contain enough context to execute independently. A developer (or agent) resuming mid-refactor should not need to read previous actions.

2. **Explicit Debt ID Linkage** - Every action must reference the Debt ID from the baseline report's Technical Debt Inventory.

3. **Commit Message Template** - Include the Debt ID in commit messages: `type(scope): description [D{n}]`

4. **Parallelizable Actions Marked** - Actions that can be executed in parallel should be grouped:
   ```markdown
   ## Parallel Group PG1 (P1 fixes)
   These actions have no interdependencies and can be executed by parallel sub-agents:
   - A1: Add httpx dependency
   - A3: Fix version constant
   
   ## Sequential Group SG1 (SecurityEngine decomposition)
   These actions must be executed in order:
   - A2: Extract RateLimiter
   - A4: Extract NetworkValidator
   - A5: Extract AuditFacade
   ```

5. **Status Tracking** - Action plan must be updated after each commit:
   - PENDING → IN_PROGRESS → COMPLETED
   - Add commit hash when completed

---

## Phase 3: Execute Refactoring

### Execution Strategy

1. **Parallel Execution for Independent Items**
   - Launch sub-agents for items in the same Parallel Group
   - Each sub-agent executes one action and reports completion
   - Consolidate results before proceeding to dependent groups

2. **Sequential Execution for Dependent Items**
   - Execute Sequential Groups in order
   - Verify tests pass after each action before proceeding

### TDD Requirements

For each refactoring action:

1. **RED**: Write failing test (if adding new component)
2. **GREEN**: Implement minimal code to pass
3. **REFACTOR**: Clean up while keeping tests green

For behavior-preserving refactors, existing tests serve as the safety net. Add characterization tests if behavior is unclear.

### Commit Requirements

- Atomic commits: ≤50 lines OR 2-3 TDD tests per commit
- Run linter before every commit
- **Commit message format:** `<type>(<scope>): <description> [D{n}]`
  - The `[D{n}]` suffix links to the baseline report debt item
  - Example: `refactor(security): extract RateLimiter from SecurityEngine [D2]`

### After Each Action

1. Mark action as COMPLETED in `REFACTOR_ACTION_PLAN.md`
2. Add commit hash to action entry
3. Update "Quick Status" section
4. Commit the action plan update: `docs: mark action A{n} complete`

### Complexity Reduction Standards

**B-rated functions (complexity 6-10) MUST be analyzed:**

- If function has multiple responsibilities → Extract methods
- If function has deep nesting → Introduce early returns or guard clauses
- If function has many conditionals → Consider strategy pattern or lookup tables
- Document decision if leaving unchanged with rationale

**A-rating (complexity ≤5) is the TARGET for all functions.**

### Exception Handling Standards

All I/O operations (network, file, database, subprocess) MUST have:

1. **Specific exception types caught** - No bare `except:` or `except Exception:`
2. **Appropriate recovery** - Retry, fallback, or clean failure
3. **Context preservation** - Log exception with context before re-raising or wrapping
4. **Resource cleanup** - Use context managers or try/finally

### Security Standards

1. **Input validation at boundaries** - All external input validated before processing
2. **Output encoding** - Data encoded appropriately for output context
3. **Error messages** - No sensitive data (paths, credentials, stack traces) exposed to callers
4. **Timeouts on all I/O** - No unbounded waits
5. **Resource limits** - Bounded collections, TTLs on caches, rate limiting on endpoints

### Performance Standards

1. **No synchronous I/O in async functions** - Use async equivalents or run in executor
2. **Connection pooling** - HTTP clients and database connections pooled
3. **Bounded memory** - Caches have max size and TTL, rate limit state cleaned up
4. **Lazy loading** - Heavy resources loaded on demand

---

## Phase 4: Completion Report

**IMMEDIATELY after completing all refactoring actions**, create `.refactor/YYYYMMDD-HHMMSS/REFACTOR_COMPLETION_REPORT.md`.

### Parallel Metric Collection

Launch the same sub-agents as Phase 1 to collect post-refactor metrics in parallel.

### Structure Requirements

The completion report MUST contain:

1. **IDENTICAL section structure** to the baseline report
2. **Side-by-side comparison data** showing baseline vs. post-refactor values
3. **Change indicators** (+/- or ✅/❌) for each metric
4. **Regression explanations** - Any metric that got worse MUST have an explanation

### Required Sections (mirroring baseline)

1. **Summary**
   - Session directory reference
   - Baseline commit → Final commit
   - Overall health: Baseline → Post-Refactor
   - Key improvements
   - Any regressions with justification

2. **Test Coverage Analysis**
   - Same table format as baseline with "Baseline | Post-Refactor | Change" columns

3. **Code Complexity Metrics**
   - Same table format as baseline
   - Show before/after for complexity counts
   - Show before/after for each B+ rated function
   - **Any function still B-rated must have documented justification**

4. **Dependency Analysis**
   - Same table format as baseline
   - Note any new modules or changed coupling

5. **Type Safety Analysis**
   - Same table format as baseline
   - Type annotation coverage change

6. **Exception Handling Analysis**
   - Same table format as baseline
   - Unhandled paths addressed

7. **Security Analysis**
   - Same table format as baseline
   - Vulnerabilities addressed

8. **Performance Analysis**
   - Same table format as baseline
   - Improvements made

9. **Lines of Code**
   - Same table format as baseline
   - Show before/after counts

10. **Completed Actions**
    - Table of all actions with status, commit hash, and debt ID reference

    | Action ID | Debt ID | Description | Status | Commit |
    |-----------|---------|-------------|--------|--------|
    | A1 | D1 | Add httpx dependency | ✅ | abc123 |
    | A2 | D2 | Extract RateLimiter | ✅ | def456 |

11. **Commit Log with Traceability**

    | Commit | Message | Debt ID(s) Addressed | Category |
    |--------|---------|---------------------|----------|
    | abc123 | fix(deps): add missing httpx dependency [D1] | D1 | P1-Dependency |
    | def456 | refactor(security): extract RateLimiter from SecurityEngine [D2] | D2 | P2-SRP |

12. **Architectural Changes**
    - New components created
    - Methods refactored with before/after metrics
    - SOLID violations addressed

13. **Files Changed**
    - List of all modified/created/deleted files

14. **Remaining Technical Debt**
    - Any items explicitly deferred with justification
    - New debt discovered during refactor (if any)
    - **@todo markers added to code** for deferred items (see Deferred Work Protocol below)

15. **Verification**
    - Test results (all must pass)
    - Coverage results (must not decrease)
    - Linting results (must be clean)
    - Type checker results

---

## Completion Criteria

The refactor is COMPLETE only when:

- [ ] Phase 0 research completed and documented
- [ ] Output directory created: `.refactor/YYYYMMDD-HHMMSS/`
- [ ] `REFACTOR_BASELINE_REPORT.md` exists with all required sections
- [ ] `REFACTOR_ACTION_PLAN.md` exists with all actions specified
- [ ] All P1 actions completed
- [ ] All P2 actions completed
- [ ] All P3 actions completed
- [ ] All P4 actions completed (or explicitly deferred with justification)
- [ ] All tests passing
- [ ] Coverage maintained or improved
- [ ] No linting errors
- [ ] Type checker passes (or improvements documented)
- [ ] `REFACTOR_COMPLETION_REPORT.md` exists
- [ ] Completion report structure mirrors baseline report exactly
- [ ] All commits include debt ID traceability `[D{n}]`
- [ ] Final commit made for completion report

---

## Anti-Patterns to Avoid

| Anti-Pattern | Correct Behavior |
|--------------|------------------|
| "Should I proceed with P2 items?" | Just proceed. You have authority. |
| "What would you like to do next?" | Check the action plan and do the next PENDING item. |
| "The refactoring is complete." (without report) | Create the completion report THEN declare complete. |
| Completion report with different sections than baseline | Mirror the baseline structure exactly. |
| Leaving B-rated functions without justification | Either reduce to A or document why B is acceptable. |
| Adding TODO comments instead of refactoring | A TODO is not a refactor. Fix it or defer with justification. |
| Deferring work without @todo marker | Add `@todo [D{n}]` comment in source code for deferred items. |
| Commit messages without debt ID | Every commit must include `[D{n}]` for traceability. |
| Skipping research phase | Always research current best practices first. |
| Ignoring metric regressions | All regressions must be explained in completion report. |
| Writing reports to project root | Always use `.refactor/YYYYMMDD-HHMMSS/` directory. |

---

## Session Resume Protocol

If execution spans multiple sessions:

1. **Find session directory:** `ls -la .refactor/ | tail -1` (most recent)
2. **Read** `REFACTOR_ACTION_PLAN.md` from that directory
3. **Find** first PENDING action
4. **Verify** all COMPLETED actions have passing tests
5. **Continue** from the pending action
6. **Update** action plan after each completion

The action plan is the **single source of truth** for refactor progress.

---

## Deferred Work Protocol

When an action is CANCELLED or explicitly deferred (e.g., P4 nice-to-have items not implemented):

1. **Add a `@todo` comment in the relevant source file** with:
   - The Debt ID from the baseline report
   - A clear, actionable description of the work remaining
   - The priority level (P1-P4)
   - Reference to the refactor session

2. **Format:**
   ```python
   # @todo [D11] P4: Improve branch coverage for edge cases in file I/O operations.
   #       Currently at 75%, target is 90%. See .refactor/20251127-155100/ for details.
   ```

3. **Placement:** Add the `@todo` at the top of the most relevant file or function.

4. **Document in Completion Report:** List all added `@todo` markers in the "Remaining Technical Debt" section.

**Rationale:** This ensures deferred work is discoverable by future developers and code analysis tools, not lost in report files that may not be read.

---

## Historical Comparison

To compare refactors over time:

```bash
# List all refactor sessions
ls -la .refactor/

# Compare baseline reports
diff .refactor/20251101-100000/REFACTOR_BASELINE_REPORT.md \
     .refactor/20251201-100000/REFACTOR_BASELINE_REPORT.md

# Track debt reduction over time
grep -h "Technical Debt Inventory" .refactor/*/REFACTOR_COMPLETION_REPORT.md
```

---

## Example Flow

```
Session 1:
1. Phase 0: Web search for {language} best practices 2024/2025
2. Create directory: .refactor/20251127-143022/
3. Phase 1: Launch parallel sub-agents for baseline analysis
4. Phase 1: Consolidate into .refactor/20251127-143022/REFACTOR_BASELINE_REPORT.md
5. Phase 2: Generate .refactor/20251127-143022/REFACTOR_ACTION_PLAN.md
6. Phase 3: Execute A1-A5 (P1 items)
7. Commit action plan updates
8. (Session ends)

Session 2:
1. Find session: .refactor/20251127-143022/
2. Read REFACTOR_ACTION_PLAN.md
3. Verify A1-A5 complete
4. Execute A6-A12 (P2 items, using parallel sub-agents where marked)
5. Commit action plan updates
6. (Session ends)

Session 3:
1. Find session: .refactor/20251127-143022/
2. Read REFACTOR_ACTION_PLAN.md
3. Verify A1-A12 complete
4. Execute A13-A20 (P3-P4 items)
5. Phase 4: Launch parallel sub-agents for completion metrics
6. Phase 4: Create .refactor/20251127-143022/REFACTOR_COMPLETION_REPORT.md
7. Final commit
8. Declare refactor complete
```

No user interaction required between phases.

---

## Appendix A: Commit Message Types

| Type | When to Use |
|------|-------------|
| `fix` | Bug fixes, missing dependencies |
| `refactor` | Code restructuring without behavior change |
| `perf` | Performance improvements |
| `security` | Security fixes |
| `test` | Adding or updating tests |
| `docs` | Documentation changes |
| `chore` | Tooling, config, non-code changes |

---

## Appendix B: Key Improvements from v1.0

| Gap in v1 | Addressed in v2 |
|-----------|-----------------|
| No best practices research | Phase 0 mandatory web search |
| Reports in project root | Timestamped `.refactor/YYYYMMDD-HHMMSS/` directory |
| No historical comparison | Multiple refactor sessions preserved |
| Incomplete SRP decomposition | Explicit requirement to address ALL identified SRP violations |
| B-rated functions left unchanged | B-rated must be reduced to A or justified |
| No exception handling analysis | Dedicated section with I/O operation audit |
| No security analysis | Dedicated section with input validation audit |
| No performance analysis | Dedicated section with async/memory audit |
| No type safety analysis | Dedicated section with type checker integration |
| Context lost between sessions | Detailed action plan with self-contained specifications |
| Commits not traceable to debt | Mandatory `[D{n}]` suffix in all commit messages |
| TODO comments accepted as resolution | Explicitly forbidden - must fix or defer with justification |
| No parallel execution guidance | Explicit sub-agent parallelism for analysis and independent actions |
| Regressions not explained | Mandatory explanation for any metric that gets worse |

---

*Prompt version 2.0 - Enhanced for comprehensive refactoring with session resumability, historical tracking, and full traceability*
