# MCP Server Refactor Baseline Report

**Session Directory:** `.refactor/20251127-173920/`  
**Baseline Commit:** `6ae4cca7cd176756e27122b63f83280cbd18e50d`  
**Created:** 2025-11-27T17:39:20  
**Project:** mcp-secure-local v1.0.0

---

## 0. Research Findings (Phase 0)

### Current Best Practices 2024/2025

| Area | Tool/Practice | Status in Codebase |
|------|---------------|-------------------|
| **Linting** | Ruff (replaces flake8, isort, black) | ✅ Configured in pyproject.toml |
| **Type Checking** | Pyright/mypy | ✅ Pyright in dev dependencies |
| **Security Scanning** | Bandit (via ruff S rules) | ✅ Configured |
| **Coverage** | coverage.py with branch coverage | ✅ Configured at 95% threshold |
| **Testing** | pytest with pytest-asyncio | ✅ Configured |
| **Dependency Management** | uv | ✅ Using uv.lock |

### Recommended Improvements

1. **Replace `assert` statements** used as control flow (stripped with `-O`)
2. **Add TypedDict** for structured JSON payloads instead of `dict[str, Any]`
3. **Extract large modules** into packages (bugtracker.py is 1005 lines)
4. Consider **hypothesis** for property-based testing

### Language-Specific Patterns to Apply

- Use `from __future__ import annotations` (already in use)
- Prefer `X | None` over `Optional[X]` (already in use)
- Use context managers for all resource cleanup
- Use handler registries instead of if/elif chains for extensibility

---

## 1. Test Coverage Analysis

### Overall Summary

| Metric | Value |
|--------|-------|
| **Overall Line Coverage** | **97%** (1,152 / 1,185 statements) |
| **Branch Coverage** | **93%** (280 / 302 branches) |
| **Total Tests** | 309 |
| **Passed** | 309 |
| **Failed** | 0 |
| **Test:Source Ratio** | 1.48:1 |

### Per-Module Coverage

| Module | Statements | Missing | Coverage | Branch Cov |
|--------|------------|---------|----------|------------|
| `src/__init__.py` | 1 | 0 | 100% | 100% |
| `src/plugins/__init__.py` | 4 | 0 | 100% | 100% |
| `src/plugins/base.py` | 32 | 4 | 88% | 100% |
| `src/plugins/bugtracker.py` | 281 | 4 | 96% | 88% |
| `src/plugins/dispatcher.py` | 37 | 1 | 94% | 86% |
| `src/plugins/loader.py` | 53 | 3 | 93% | 89% |
| `src/plugins/websearch.py` | 63 | 0 | 100% | 100% |
| `src/protocol/__init__.py` | 5 | 0 | 100% | 100% |
| `src/protocol/jsonrpc.py` | 62 | 2 | 95% | 89% |
| `src/protocol/lifecycle.py` | 49 | 0 | 100% | 100% |
| `src/protocol/tools.py` | 29 | 0 | 100% | 100% |
| `src/protocol/transport.py` | 25 | 0 | 100% | 100% |
| `src/security/__init__.py` | 0 | 0 | 100% | 100% |
| `src/security/audit.py` | 70 | 2 | 95% | 75% |
| `src/security/engine.py` | 67 | 0 | 100% | 100% |
| `src/security/firewall.py` | 104 | 4 | 97% | 98% |
| `src/security/policy.py` | 75 | 2 | 96% | 88% |
| `src/security/ratelimiter.py` | 40 | 0 | 100% | 100% |
| `src/security/validator.py` | 117 | 9 | 94% | 98% |
| `src/server.py` | 71 | 2 | 98% | 100% |

### Branch Coverage Concerns

| Module | Branch Cov | Notes |
|--------|------------|-------|
| `security/audit.py` | 75% | Exit branch at line 192 |
| `plugins/dispatcher.py` | 86% | Error handling paths |
| `plugins/bugtracker.py` | 88% | Error handling paths |
| `security/policy.py` | 88% | Edge cases |

### Test Type Inventory

| Type | Count | Files |
|------|-------|-------|
| Unit Tests | 300 | 13 files |
| Integration Tests | 9 | test_integration.py |
| E2E Tests | 0 | - |
| Property-Based Tests | 0 | - |

---

## 2. Code Complexity Metrics

### Complexity Grade Distribution

| Grade | Range | Count | Percentage |
|-------|-------|-------|------------|
| **A** | 1-5 | 180 | 94.7% |
| **B** | 6-10 | 9 | 4.7% |
| **C** | 11-20 | 1 | 0.5% |
| **D** | 21-30 | 0 | 0% |
| **E** | 31+ | 0 | 0% |

**Average Complexity Score:** 2.53 (A)

### Functions Rated B or Higher (ALL)

| Function | File:Line | Complexity | Grade |
|----------|-----------|------------|-------|
| `BugTrackerPlugin._update_bug` | `src/plugins/bugtracker.py:809` | **18** | **C** |
| `parse_message` | `src/protocol/jsonrpc.py:57` | 10 | B |
| `BugStore.list_bugs` | `src/plugins/bugtracker.py:315` | 8 | B |
| `BugTrackerPlugin.execute` | `src/plugins/bugtracker.py:601` | 8 | B |
| `MCPServer._handle_request` | `src/server.py:112` | 8 | B |
| `sanitize_path` | `src/security/validator.py:43` | 8 | B |
| `NetworkFirewall._resolve_hostname` | `src/security/firewall.py:99` | 7 | B |
| `NetworkFirewall.validate_url` | `src/security/firewall.py:238` | 7 | B |
| `PluginLoader.discover_plugins` | `src/plugins/loader.py:53` | 7 | B |
| `InputValidator._process_arguments` | `src/security/validator.py:221` | 6 | B |
| `PluginLoader._load_plugin` | `src/plugins/loader.py:86` | 6 | B |

### Maintainability Index by Module

| Module | MI Score | Rating |
|--------|----------|--------|
| `src/__init__.py` | 100.00 | A |
| `src/protocol/transport.py` | 80.44 | A |
| `src/plugins/dispatcher.py` | 79.65 | A |
| `src/security/engine.py` | 78.19 | A |
| `src/protocol/lifecycle.py` | 73.09 | A |
| `src/plugins/websearch.py` | 72.13 | A |
| `src/server.py` | 72.10 | A |
| `src/security/audit.py` | 71.83 | A |
| `src/plugins/loader.py` | 71.60 | A |
| `src/security/ratelimiter.py` | 70.43 | A |
| `src/protocol/jsonrpc.py` | 68.86 | A |
| `src/security/policy.py` | 67.18 | A |
| `src/security/firewall.py` | 60.25 | A |
| `src/security/validator.py` | 58.73 | A |
| **`src/plugins/bugtracker.py`** | **35.92** | **A (LOW)** |

---

## 3. Dependency Analysis

### External Dependencies

| Package | Version Constraint | Installed | Status |
|---------|-------------------|-----------|--------|
| `pyyaml` | >=6.0 | 6.0.3 | ✅ Current |
| `jsonschema` | >=4.20 | 4.25.1 | ✅ Current |
| `httpx` | >=0.27 | 0.28.1 | ✅ Current |
| `cachetools` | >=6.2.2 | 6.2.2 | ✅ Current |

### Development Dependencies

| Package | Version Constraint | Status |
|---------|-------------------|--------|
| `pytest` | >=8.0 | ✅ Current (9.0.1) |
| `pytest-cov` | >=4.0 | ✅ Current (7.0.0) |
| `pytest-asyncio` | >=0.23 | ✅ Current (1.3.0) |
| `ruff` | >=0.4 | ✅ Current |
| `pyright` | >=1.1.407 | ✅ Current |

### Module Coupling Summary

| Module | Imports From (Internal) | Imported By | Coupling |
|--------|------------------------|-------------|----------|
| `plugins/base.py` | None | 5 modules | High (core abstraction) |
| `security/engine.py` | 5 modules | 1 module | High (facade) |
| `server.py` | 6 modules | None | High (entry point) |
| `plugins/dispatcher.py` | 1 module | 2 modules | Medium |
| Others | 0-1 modules | 0-1 modules | Low |

### Circular Dependencies

**None detected.** Clean layered architecture.

---

## 4. Type Safety Analysis

| Metric | Value |
|--------|-------|
| Type Annotation Coverage | ~92% |
| Pyright Errors | **0** |
| Pyright Warnings | 0 |
| `# type: ignore` Comments | 0 |
| Uses of `Any` | 91 |
| Untyped Functions | 3 (doctest examples) |

### `Any` Usage Breakdown

| Pattern | Count | Primary Use |
|---------|-------|-------------|
| `dict[str, Any]` | 53 | JSON-RPC payloads |
| `__exit__` params | 9 | Context manager protocol |
| `Any \| None` | 3 | Optional error data |
| `list[Any]` | 1 | SQL parameters |

---

## 5. Exception Handling Analysis

### Anti-Patterns Found

| Pattern | File:Line | Issue |
|---------|-----------|-------|
| Generic `except Exception:` | `src/plugins/websearch.py:121` | Intentional - returns sanitized error |
| Exception message in ToolExecutionError | `src/plugins/dispatcher.py:79` | Chains with `from e` |

### I/O Operations Analysis

| File:Line | Operation | Status |
|-----------|-----------|--------|
| `plugins/websearch.py:142` | httpx.get() | ✅ Catches TimeoutException, HTTPStatusError |
| `plugins/bugtracker.py:201-208` | SQLite | ⚠️ Generic exception catch |
| `security/audit.py:128` | open() | ⚠️ No context manager in body |

### Recovery Patterns

| Pattern | Status |
|---------|--------|
| Retry logic | ❌ Not implemented |
| Circuit breaker | ❌ Not implemented |
| Fallback mechanisms | ⚠️ Partial (plugin isolation) |

---

## 6. Security Analysis

### Ruff Security Scan Results

| File | Line | Code | Issue |
|------|------|------|-------|
| `src/plugins/bugtracker.py` | 746 | S101 | Use of `assert` |
| `src/plugins/bugtracker.py` | 792 | S101 | Use of `assert` |
| `src/plugins/bugtracker.py` | 836 | S101 | Use of `assert` |
| `src/plugins/bugtracker.py` | 948 | S101 | Use of `assert` |

### Critical Findings

| ID | Severity | File:Line | Description |
|----|----------|-----------|-------------|
| SEC-001 | **MEDIUM** | `bugtracker.py:649` | project_path lacks traversal protection |
| SEC-002 | **LOW** | `bugtracker.py:746,792,836,948` | assert used as control flow (stripped with -O) |
| SEC-003 | **LOW** | `dispatcher.py:79` | Exception chaining may leak internals |

### Security Posture

| Category | Score |
|----------|-------|
| Input Validation Framework | 9/10 |
| Path Traversal Protection | 8/10 (bugtracker gap) |
| Network Security | 9/10 |
| Rate Limiting | 9/10 |
| Error Handling | 8/10 |
| **Overall** | **8.5/10** |

---

## 7. Performance Analysis

### Concerns Identified

| Priority | Issue | File:Line | Impact |
|----------|-------|-----------|--------|
| **HIGH** | Rate limiter buckets never auto-cleaned | `ratelimiter.py:46` | Memory leak |
| **MEDIUM** | N+1 query pattern in global search | `bugtracker.py:979-1000` | O(N) latency |
| **MEDIUM** | Plugin cleanup not integrated | `server.py` | Resource leaks |
| **LOW** | Synchronous SQLite operations | `bugtracker.py:201-208` | Blocking I/O |

### Resource Management

| Pattern | Status |
|---------|--------|
| Context managers | ✅ SecurityEngine, AuditLogger, MCPServer |
| Connection pooling | ✅ httpx client pooled in websearch |
| Cache TTL | ✅ DNS cache has TTL |
| Memory bounds | ⚠️ Rate limiter unbounded |
| Plugin cleanup | ❌ Not integrated into server lifecycle |

---

## 8. Architectural Issues

### God Classes (>500 lines or >10 public methods)

| File | Class | Lines | Public Methods | Issue |
|------|-------|-------|----------------|-------|
| `src/plugins/bugtracker.py` | `BugTrackerPlugin` | 636 | 7 | **GOD CLASS** |

### Long Methods (>50 lines)

| Method | File:Line | Lines |
|--------|-----------|-------|
| `get_tools()` | `bugtracker.py:389` | **210** |
| `_update_bug()` | `bugtracker.py:809` | **91** |
| `_init_bugtracker()` | `bugtracker.py:649` | 56 |

### Medium Methods (30-50 lines) - SRP Analysis

| Method | File:Line | Lines | Concern |
|--------|-----------|-------|---------|
| `_add_bug()` | `bugtracker.py` | 48 | OK |
| `_search_bugs_global()` | `bugtracker.py` | 41 | OK |
| `_get_bug()` | `bugtracker.py` | 38 | OK |
| `_load_plugin()` | `loader.py:86` | 43 | Low |
| `_validate_hostname()` | `firewall.py` | 30 | OK |

---

## 9. SOLID Violations

### SRP Violations

| Location | Issue | Severity |
|----------|-------|----------|
| `bugtracker.py` | 1005 lines: models + storage + plugin + schemas | **HIGH** |
| `bugtracker.py` | `get_tools()` is 210 lines of schema definitions | **MEDIUM** |

### OCP Violations

| Location | Issue | Recommendation |
|----------|-------|----------------|
| `bugtracker.py:601` | if/elif chain for tool routing | Add handler registry |
| `server.py:138-149` | if/elif chain for message routing | Consider handler registry |

### DIP Violations

| Location | Issue | Severity |
|----------|-------|----------|
| `server.py:58-61` | Direct instantiation of components | MEDIUM |
| `bugtracker.py:682` | Direct BugStore instantiation | LOW |

### LSP/ISP Violations

**None found.**

---

## 10. Dead Code / Unused Code

### Definitely Unused

| File | Item | Notes |
|------|------|-------|
| `tests/test_bugtracker.py:1441` | `bug1_id` variable | Assigned but never used |

### Linting Error

```
tests/test_bugtracker.py:1441:9 - F841 Local variable `bug1_id` is assigned to but never used
```

---

## 11. Code Duplication

**No significant duplication found.**

---

## 12. Linting & Formatting Status

```
$ uv run ruff check src/ tests/
Found 1 error (bugtracker test file)

$ uv run ruff check src/
All checks passed!
```

**Status:** ⚠️ 1 linting error in tests

---

## 13. Lines of Code

| Category | Lines |
|----------|-------|
| Source (src/) | 3,768 |
| Tests (tests/) | 5,358 |
| **Total** | **9,126** |
| Test:Source Ratio | 1.42:1 |

---

## 14. Technical Debt Inventory

| ID | Item | Category | Severity | Effort | Priority | Location | Acceptance Criteria |
|----|------|----------|----------|--------|----------|----------|---------------------|
| D1 | bugtracker.py is 1005 lines - God class | Architecture | High | High | P2 | `bugtracker.py` | Split into package |
| D2 | `get_tools()` is 210 lines in bugtracker | Architecture | Medium | Medium | P2 | `bugtracker.py:389` | Extract to constant |
| D3 | `_update_bug()` has CC=18 | Complexity | Medium | Medium | P2 | `bugtracker.py:809` | Reduce to <10 |
| D4 | 4 assert statements used as control flow | Security | Low | Low | P3 | `bugtracker.py:746,792,836,948` | Replace with explicit checks |
| D5 | Rate limiter cleanup not automatic | Performance | Medium | Low | P2 | `ratelimiter.py:46` | Add periodic cleanup |
| D6 | Plugin cleanup not integrated | Performance | Medium | Low | P2 | `server.py` | Call close() on plugins |
| D7 | Unused variable in test | Linting | Low | Low | P1 | `test_bugtracker.py:1441` | Remove or use variable |
| D8 | OCP violation in BugTrackerPlugin.execute | Architecture | Low | Medium | P3 | `bugtracker.py:601` | Add handler registry |
| D9 | N+1 pattern in _search_bugs_global | Performance | Medium | Medium | P3 | `bugtracker.py:979` | Optimize query pattern |
| D10 | project_path lacks traversal protection | Security | Medium | Low | P2 | `bugtracker.py:649` | Add sanitize_path |

---

## 15. Summary & Recommendations

### Overall Health Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| Test Coverage | ⭐⭐⭐⭐⭐ | 97% line, 93% branch |
| Code Complexity | ⭐⭐⭐⭐ | 94.7% A-rated, 1 C-rated function |
| Type Safety | ⭐⭐⭐⭐⭐ | 0 pyright errors |
| Security | ⭐⭐⭐⭐ | Good framework, minor gaps |
| Performance | ⭐⭐⭐⭐ | Minor memory concerns |
| Architecture | ⭐⭐⭐ | One God class needs refactoring |

### Priority Order for Refactoring

1. **P1 (Critical):** D7 - Fix linting error (blocks CI)
2. **P2 (High):** D1, D2, D3, D5, D6, D10 - Architecture and performance
3. **P3 (Medium):** D4, D8, D9 - Code quality improvements

### Risk Areas

1. **BugTrackerPlugin is a God Class** - 1005 lines in a single file with 210-line methods and CC=18 function
2. **Rate limiter memory leak** - cleanup() exists but is never called automatically
3. **Plugin resources not cleaned** - WebSearchPlugin.close() never called
