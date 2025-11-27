# Refactor Action Plan

**Session Directory:** `.refactor/20251127-173920/`  
**Baseline Commit:** `6ae4cca7cd176756e27122b63f83280cbd18e50d`  
**Created:** 2025-11-27T17:39:20

---

## Session Resume Instructions

To resume this refactor:
1. Navigate to `.refactor/` and find the most recent timestamped directory
2. Read this action plan
3. Check the "Status" column in the action table
4. Find the first "PENDING" item
5. Execute from that point

---

## Quick Status

- **Total Actions:** 10
- **Completed:** 8
- **Cancelled:** 1
- **Deferred:** 1
- **Current Phase:** COMPLETE

---

## Action Table

| ID | Debt ID | Action | Category | Files | Est. Lines | Status | Commit Hash |
|----|---------|--------|----------|-------|------------|--------|-------------|
| A1 | D7 | Fix unused variable linting error | P1-Linting | tests/test_bugtracker.py | -1 | DONE | 2fb450a |
| A2 | D4 | Replace assert with explicit None checks | P2-Security | src/plugins/bugtracker.py | +16 | DONE | 869f8a3 |
| A3 | D10 | Add path traversal protection to bugtracker | P2-Security | src/plugins/bugtracker.py | +10 | DONE | 27c526f |
| A4 | D5 | Add automatic rate limiter cleanup | P2-Performance | src/security/ratelimiter.py, server.py | +15 | DONE | 105eb88 |
| A5 | D6 | Integrate plugin cleanup into server lifecycle | P2-Performance | src/server.py | +10 | DONE | 749bde9 |
| A6 | D2 | Extract get_tools() schemas to constant | P2-Architecture | src/plugins/bugtracker.py | +5, -210 | DONE | 235270d |
| A7 | D3 | Reduce _update_bug complexity (CC=18) | P2-Complexity | src/plugins/bugtracker.py | +30 | DONE | c691548 |
| A8 | D8 | Add handler registry to BugTrackerPlugin | P3-OCP | src/plugins/bugtracker.py | +15 | DONE | aefb146 |
| A9 | D9 | Optimize _search_bugs_global N+1 pattern | P3-Performance | src/plugins/bugtracker.py | +20 | CANCELLED | - |
| A10 | D1 | Split bugtracker.py into package (optional) | P4-Architecture | src/plugins/bugtracker/ | +50 | DEFERRED | - |

---

## Parallel Groups

### Sequential Group SG1 (P1 - Critical)
Must be done first to unblock CI:
- A1: Fix linting error

### Parallel Group PG1 (P2 - Security)
These can be executed in parallel:
- A2: Replace assert statements
- A3: Add path traversal protection

### Parallel Group PG2 (P2 - Performance)
These can be executed in parallel:
- A4: Rate limiter cleanup
- A5: Plugin cleanup

### Sequential Group SG2 (P2 - Architecture/Complexity)
Should be done after PG1 and PG2:
- A6: Extract schemas (before A7)
- A7: Reduce _update_bug complexity

### Parallel Group PG3 (P3 - Improvements)
Can be done in parallel, lower priority:
- A8: Handler registry
- A9: Optimize N+1 pattern

### Deferred (P4)
Optional, requires significant effort:
- A10: Split into package

---

## Detailed Action Specifications

### A1: Fix unused variable linting error
**Addresses:** D7 - Unused variable `bug1_id` in test  
**Category:** P1-Linting

**Context:**
At `tests/test_bugtracker.py:1441`, variable `bug1_id` is assigned but never used, causing ruff error F841.

**Pre-conditions:**
- None

**Steps:**
1. Open tests/test_bugtracker.py
2. At line 1441, either:
   - Remove the variable assignment if not needed, OR
   - Prefix with `_` to indicate intentionally unused: `_bug1_id`
3. Run `ruff check tests/` to verify fix

**Files Changed:**
- `tests/test_bugtracker.py` (-1 line or rename)

**Tests:**
- All existing tests must pass

**Acceptance Criteria:**
- [ ] `ruff check tests/` passes with no errors
- [ ] All tests pass

**Commit Message:** `fix(tests): remove unused variable bug1_id in test_bugtracker [D7]`

---

### A2: Replace assert with explicit None checks
**Addresses:** D4 - assert used as control flow (stripped with -O)  
**Category:** P2-Security

**Context:**
At lines 746, 792, 836, and 948 of `bugtracker.py`, `assert store is not None` is used after `_get_store()` returns. With Python's `-O` flag, assert statements are stripped, which would cause None reference errors.

**Pre-conditions:**
- None

**Steps:**
1. RED: Write test that ensures error handling works when store is None
2. GREEN: Replace each `assert store is not None` with explicit check:
   ```python
   if store is None:
       return ToolResult(
           content=[{"type": "text", "text": "Bug tracker not initialized for this project"}],
           is_error=True,
       )
   ```
3. REFACTOR: Ensure consistent error message

**Files Changed:**
- `src/plugins/bugtracker.py` (+16 lines, -4 lines)
- `tests/test_bugtracker.py` (+10 lines)

**Tests:**
- New: 1-2 tests for None store handling
- Existing: All tests must pass

**Acceptance Criteria:**
- [ ] No assert statements used as control flow
- [ ] `ruff check src/ --select=S101` reports no issues in bugtracker.py
- [ ] All tests pass

**Commit Message:** `fix(bugtracker): replace assert with explicit None checks [D4]`

---

### A3: Add path traversal protection to bugtracker
**Addresses:** D10 - project_path lacks traversal protection  
**Category:** P2-Security

**Context:**
At `bugtracker.py:649`, `project_path` is validated only for existence and being a directory. An attacker could potentially use path traversal to access unauthorized directories.

**Pre-conditions:**
- None

**Steps:**
1. RED: Write test that verifies path traversal attempts are rejected
2. GREEN: Add validation using `sanitize_path` or equivalent:
   ```python
   from src.security.validator import sanitize_path
   
   # In _init_bugtracker:
   try:
       # Resolve to canonical path and verify it's within allowed bounds
       project = Path(arguments["project_path"]).resolve()
   except (OSError, ValueError) as e:
       return ToolResult(content=[{"type": "text", "text": "Invalid project path"}], is_error=True)
   ```
3. REFACTOR: Consider adding configurable base path restriction

**Files Changed:**
- `src/plugins/bugtracker.py` (+10 lines)
- `tests/test_bugtracker.py` (+15 lines)

**Tests:**
- New: 2-3 tests for path validation
- Existing: All tests must pass

**Acceptance Criteria:**
- [ ] Path traversal attempts rejected
- [ ] Symlink resolution used
- [ ] All tests pass

**Commit Message:** `security(bugtracker): add path traversal protection to project_path [D10]`

---

### A4: Add automatic rate limiter cleanup
**Addresses:** D5 - Rate limiter buckets never auto-cleaned  
**Category:** P2-Performance

**Context:**
At `ratelimiter.py:46`, `_buckets` is a `defaultdict` that grows unbounded. While `cleanup()` method exists at line 58, it's never called automatically. Over time, this can cause memory exhaustion.

**Pre-conditions:**
- None

**Steps:**
1. RED: Write test that verifies cleanup is called periodically
2. GREEN: Modify `check_rate_limit()` to call cleanup probabilistically:
   ```python
   def check_rate_limit(self, tool_name: str) -> bool:
       # Probabilistic cleanup (1 in 100 calls)
       if random.randint(1, 100) == 1:
           self.cleanup()
       # ... rest of method
   ```
3. Alternative: Use TTLCache from cachetools instead of defaultdict
4. REFACTOR: Consider making cleanup interval configurable

**Files Changed:**
- `src/security/ratelimiter.py` (+10 lines)
- `tests/test_ratelimiter.py` (+15 lines)

**Tests:**
- New: 2-3 tests for automatic cleanup
- Existing: All tests must pass

**Acceptance Criteria:**
- [ ] Stale buckets cleaned up automatically
- [ ] Cleanup doesn't impact performance significantly
- [ ] All tests pass

**Commit Message:** `perf(ratelimiter): add automatic cleanup of stale buckets [D5]`

---

### A5: Integrate plugin cleanup into server lifecycle
**Addresses:** D6 - Plugin cleanup not integrated  
**Category:** P2-Performance

**Context:**
`WebSearchPlugin.close()` exists but is never called by `MCPServer`. This causes HTTP connection pool leaks when the server shuts down.

**Pre-conditions:**
- None

**Steps:**
1. RED: Write test that verifies plugins are closed when server closes
2. GREEN: Modify `MCPServer.close()` to iterate plugins and call close():
   ```python
   def close(self) -> None:
       # Close plugins that have close() method
       for plugin in self._dispatcher.get_plugins():
           if hasattr(plugin, 'close') and callable(plugin.close):
               plugin.close()
       self._security_engine.close()
   ```
3. GREEN: Add `get_plugins()` method to ToolDispatcher if needed
4. REFACTOR: Consider making close() part of PluginBase protocol

**Files Changed:**
- `src/server.py` (+8 lines)
- `src/plugins/dispatcher.py` (+3 lines)
- `tests/test_server.py` (+15 lines)

**Tests:**
- New: 2-3 tests for plugin cleanup
- Existing: All tests must pass

**Acceptance Criteria:**
- [ ] Plugins with close() method are cleaned up on server close
- [ ] HTTP connection pools released
- [ ] All tests pass

**Commit Message:** `perf(server): integrate plugin cleanup into server lifecycle [D6]`

---

### A6: Extract get_tools() schemas to constant
**Addresses:** D2 - get_tools() is 210 lines in bugtracker  
**Category:** P2-Architecture

**Context:**
`BugTrackerPlugin.get_tools()` at line 389 is 210 lines of schema definitions. This is data, not logic, and makes the class harder to navigate.

**Pre-conditions:**
- None

**Steps:**
1. Extract schema definitions to module-level constant:
   ```python
   _BUGTRACKER_TOOL_SCHEMAS: list[ToolDefinition] = [
       ToolDefinition(
           name="init_bugtracker",
           description="...",
           input_schema={...}
       ),
       # ... all tools
   ]
   ```
2. Simplify get_tools() to:
   ```python
   def get_tools(self) -> list[ToolDefinition]:
       return _BUGTRACKER_TOOL_SCHEMAS.copy()
   ```
3. REFACTOR: Consider using a factory if schemas need dynamic values

**Files Changed:**
- `src/plugins/bugtracker.py` (+5 lines, refactored 210 lines)

**Tests:**
- Existing: All tests must pass

**Acceptance Criteria:**
- [ ] Schemas extracted to module-level constant
- [ ] get_tools() is <10 lines
- [ ] All tests pass

**Commit Message:** `refactor(bugtracker): extract tool schemas to module constant [D2]`

---

### A7: Reduce _update_bug complexity (CC=18)
**Addresses:** D3 - _update_bug has cyclomatic complexity of 18  
**Category:** P2-Complexity

**Context:**
`_update_bug()` at line 809 has 91 lines and CC=18. It handles validation, change tracking, history creation, and persistence all in one method.

**Pre-conditions:**
- A6 completed (cleaner file)

**Steps:**
1. RED: Add characterization tests if any behavior is unclear
2. GREEN: Extract change tracking helper:
   ```python
   def _track_field_change(
       self, current: str | list | None, new: str | list | None, field_name: str
   ) -> tuple[str, str, str] | None:
       """Returns (field_name, old_value, new_value) if changed, else None."""
       if current != new and new is not None:
           return (field_name, str(current), str(new))
       return None
   ```
3. GREEN: Extract history entry creation:
   ```python
   def _create_history_entry(
       self, changes: list[tuple[str, str, str]], note: str | None
   ) -> HistoryEntry:
       return HistoryEntry(
           timestamp=datetime.now(UTC).isoformat(),
           action="updated",
           changes={field: {"from": old, "to": new} for field, old, new in changes},
           note=note,
       )
   ```
4. REFACTOR: Simplify _update_bug to orchestrate helpers

**Files Changed:**
- `src/plugins/bugtracker.py` (+30 lines, -20 lines)
- `tests/test_bugtracker.py` (+10 lines)

**Tests:**
- New: Tests for helper functions
- Existing: All tests must pass

**Acceptance Criteria:**
- [ ] _update_bug CC < 10
- [ ] Helper functions have single responsibility
- [ ] All tests pass

**Commit Message:** `refactor(bugtracker): reduce _update_bug complexity from 18 to <10 [D3]`

---

### A8: Add handler registry to BugTrackerPlugin
**Addresses:** D8 - OCP violation in BugTrackerPlugin.execute  
**Category:** P3-OCP

**Context:**
`execute()` at line 601 uses an if/elif chain to route tool calls. This violates OCP since adding a new tool requires modifying the method.

**Pre-conditions:**
- A6 and A7 completed

**Steps:**
1. Add handler registry in __init__:
   ```python
   def __init__(self) -> None:
       self._handlers: dict[str, Callable[[dict[str, Any]], ToolResult]] = {
           "init_bugtracker": self._init_bugtracker,
           "add_bug": self._add_bug,
           "get_bug": self._get_bug,
           "update_bug": self._update_bug,
           "close_bug": self._close_bug,
           "list_bugs": self._list_bugs,
           "search_bugs_global": self._search_bugs_global,
       }
   ```
2. Simplify execute():
   ```python
   def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
       handler = self._handlers.get(tool_name)
       if handler is None:
           return ToolResult(content=[...], is_error=True)
       return handler(arguments)
   ```

**Files Changed:**
- `src/plugins/bugtracker.py` (+15 lines, -30 lines)

**Tests:**
- Existing: All tests must pass

**Acceptance Criteria:**
- [ ] Handler registry pattern implemented
- [ ] execute() is <10 lines
- [ ] All tests pass

**Commit Message:** `refactor(bugtracker): add handler registry for OCP compliance [D8]`

---

### A9: Optimize _search_bugs_global N+1 pattern
**Addresses:** D9 - N+1 query pattern in _search_bugs_global  
**Category:** P3-Performance

**Context:**
`_search_bugs_global()` at line 979 opens a new database connection for each indexed project, resulting in O(N) database operations.

**Pre-conditions:**
- None

**Steps:**
1. RED: Add performance test with many projects
2. GREEN: Collect all matching bugs first, then aggregate:
   - Option A: Use a single in-memory aggregation
   - Option B: Consider ATTACH DATABASE for SQLite
   - Option C: Use concurrent.futures for parallel queries
3. REFACTOR: Consider caching project list

**Files Changed:**
- `src/plugins/bugtracker.py` (+20 lines, -10 lines)
- `tests/test_bugtracker.py` (+10 lines)

**Tests:**
- New: Performance test with multiple projects
- Existing: All tests must pass

**Acceptance Criteria:**
- [ ] Reduced from O(N) connections to O(1) or parallel
- [ ] All tests pass

**Commit Message:** `perf(bugtracker): optimize _search_bugs_global to reduce DB operations [D9]`

---

### A10: Split bugtracker.py into package (OPTIONAL)
**Addresses:** D1 - bugtracker.py is 1005 lines  
**Category:** P4-Architecture

**Context:**
The file has grown to 1005 lines with models, storage, schemas, and plugin logic. This makes it harder to maintain.

**Pre-conditions:**
- A6, A7, A8, A9 completed
- Evaluate if still needed after other refactors

**Steps:**
1. Create package structure:
   ```
   src/plugins/bugtracker/
   ├── __init__.py           # Re-exports
   ├── models.py             # Bug, RelatedBug, HistoryEntry
   ├── store.py              # BugStore, project index functions
   ├── schemas.py            # _BUGTRACKER_TOOL_SCHEMAS
   └── plugin.py             # BugTrackerPlugin
   ```
2. Update imports across codebase
3. Verify all tests pass

**Files Changed:**
- Create `src/plugins/bugtracker/` package
- Update `src/plugins/__init__.py`
- Update `main.py` imports
- Update test imports

**Tests:**
- All tests must pass without modification to test logic

**Acceptance Criteria:**
- [ ] Package structure created
- [ ] All imports updated
- [ ] All tests pass

**Commit Message:** `refactor(bugtracker): split into package for maintainability [D1]`

---

## Execution Checklist

### Phase P1 (Critical)
- [ ] A1: Fix linting error

### Phase P2 (High)
- [ ] A2: Replace assert statements
- [ ] A3: Add path traversal protection
- [ ] A4: Automatic rate limiter cleanup
- [ ] A5: Plugin cleanup integration
- [ ] A6: Extract schemas
- [ ] A7: Reduce _update_bug complexity

### Phase P3 (Medium)
- [ ] A8: Handler registry
- [ ] A9: Optimize N+1 pattern

### Phase P4 (Optional)
- [ ] A10: Split into package

---

## Post-Refactor Verification

After all actions complete:
1. Run full test suite: `uv run pytest -v`
2. Run coverage: `uv run pytest --cov=src --cov-fail-under=95`
3. Run linter: `uv run ruff check src/ tests/`
4. Run type checker: `uv run pyright src/`
5. Create completion report
