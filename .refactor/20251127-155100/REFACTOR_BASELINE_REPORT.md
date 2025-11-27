# MCP Server Refactor Baseline Report

**Session Directory:** `.refactor/20251127-155100/`  
**Baseline Commit:** `d3342dc021a4902d0b47ddd4b5fec131b89a031d`  
**Created:** 2025-11-27T15:51:00  
**Project:** mcp-secure-local v1.0.0

---

## 0. Research Findings (Phase 0)

### Current Best Practices 2024/2025

| Area | Tool/Practice | Status in Codebase |
|------|---------------|-------------------|
| **Linting** | Ruff (replaces flake8, isort, black) | ✅ Configured in pyproject.toml |
| **Type Checking** | Pyright/mypy | ⚠️ Not in dev dependencies |
| **Security Scanning** | Bandit (via ruff S rules) | ✅ Configured |
| **Coverage** | coverage.py with branch coverage | ✅ Configured at 95% threshold |
| **Testing** | pytest with pytest-asyncio | ✅ Configured |

### Recommended Additions

1. **Add pyright** to dev dependencies for CI type checking
2. **Add cachetools** for TTL-based caching (DNS cache, rate limiter cleanup)
3. Consider **hypothesis** for property-based testing of validators

### Language-Specific Patterns to Apply

- Use `TypedDict` for structured JSON instead of `dict[str, Any]`
- Use context managers for all resource cleanup
- Use `from __future__ import annotations` (already in use)
- Prefer `X | None` over `Optional[X]` (already in use)

---

## 1. Test Coverage Analysis

### Overall Summary

| Metric | Value |
|--------|-------|
| **Overall Coverage** | **95.94%** |
| **Total Tests** | 210 |
| **Passed** | 210 |
| **Failed** | 0 |
| **Branch Coverage** | 93.9% |

### Per-Module Coverage

| Module | Statements | Missing | Coverage |
|--------|------------|---------|----------|
| `src/__init__.py` | 1 | 0 | 100% |
| `src/plugins/__init__.py` | 4 | 0 | 100% |
| `src/plugins/base.py` | 32 | 4 | 88% |
| `src/plugins/dispatcher.py` | 37 | 1 | 94% |
| `src/plugins/loader.py` | 53 | 3 | 93% |
| `src/plugins/websearch.py` | 55 | 0 | 100% |
| `src/protocol/__init__.py` | 5 | 0 | 100% |
| `src/protocol/jsonrpc.py` | 59 | 2 | 95% |
| `src/protocol/lifecycle.py` | 49 | 0 | 100% |
| `src/protocol/tools.py` | 29 | 0 | 100% |
| `src/protocol/transport.py` | 25 | 2 | 93% |
| `src/security/__init__.py` | 0 | 0 | 100% |
| `src/security/audit.py` | 70 | 2 | 95% |
| `src/security/engine.py` | 67 | 0 | 99% |
| `src/security/firewall.py` | 103 | 4 | 97% |
| `src/security/policy.py` | 75 | 2 | 96% |
| `src/security/ratelimiter.py` | 31 | 0 | 100% |
| `src/security/validator.py` | 117 | 9 | 94% |
| `src/server.py` | 59 | 2 | 97% |

### Branch Coverage Concerns

| Module | Branch Coverage |
|--------|-----------------|
| `security/audit.py` | 75.0% ⚠️ |
| `plugins/dispatcher.py` | 85.7% |
| `protocol/jsonrpc.py` | 87.5% |
| `security/policy.py` | 87.5% |

### Test Type Inventory

| Type | Count | Files |
|------|-------|-------|
| Unit Tests | 192 | 12 files |
| Integration Tests | 9 | test_integration.py |
| Property-Based Tests | 0 | - |

---

## 2. Code Complexity Metrics

### Complexity Grade Distribution

| Grade | Range | Count | Percentage |
|-------|-------|-------|------------|
| **A** | 1-5 | 79 | 90.8% |
| **B** | 6-10 | 8 | 9.2% |
| **C** | 11-20 | 0 | 0% |
| **D** | 21-30 | 0 | 0% |
| **E** | 31+ | 0 | 0% |

**Average Complexity Score:** 2.8

### Functions Rated B or Higher (ALL)

| Function | File:Line | Complexity | Grade |
|----------|-----------|------------|-------|
| `parse_message` | `src/protocol/jsonrpc.py:54` | 8 | B |
| `_handle_request` | `src/server.py:110` | 7 | B |
| `_load_plugin` | `src/plugins/loader.py:86` | 7 | B |
| `_resolve_hostname` | `src/security/firewall.py:96` | 6 | B |
| `validate_url` | `src/security/firewall.py:234` | 6 | B |
| `_validate_hostname` | `src/security/firewall.py:188` | 6 | B |
| `sanitize_path` | `src/security/validator.py:43` | 6 | B |
| `_process_value` | `src/security/validator.py:207` | 6 | B |

---

## 3. Dependency Analysis

### External Dependencies

| Package | Version | Purpose | Health |
|---------|---------|---------|--------|
| `pyyaml` | >=6.0 | YAML parsing | ✅ Current |
| `jsonschema` | >=4.20 | JSON Schema validation | ✅ Current |
| `httpx` | >=0.27 | HTTP client | ✅ Current |

### Module Coupling Summary

| Module | Efferent (Out) | Afferent (In) | Notes |
|--------|----------------|---------------|-------|
| `server.py` | 6 | 0 | Composition root - expected |
| `security/engine.py` | 5 | 0 | Facade pattern - expected |
| `plugins/base.py` | 0 | 4 | Stable abstraction |
| `security/policy.py` | 0 | 3 | Stable data class |

### Circular Dependencies

**None detected.** Clean layered architecture.

---

## 4. Type Safety Analysis

| Metric | Value |
|--------|-------|
| Type Annotation Coverage | ~98% |
| Pyright Errors | 3 |
| `# type: ignore` Comments | 0 |
| Uses of `Any` | 48 |
| Untyped Functions | 0 |

### Pyright Errors

| File | Line | Error |
|------|------|-------|
| `security/firewall.py` | 134 | Type mismatch in DNS cache |
| `security/firewall.py` | 135 | Return type mismatch |
| `security/validator.py` | 271 | jsonschema.exceptions import |

---

## 5. Exception Handling Analysis

### Anti-Patterns Found

| Pattern | File:Line | Issue |
|---------|-----------|-------|
| Generic `except Exception` swallows error | `src/protocol/transport.py:47-48` | Returns None silently |
| Exception message exposed to client | `src/plugins/websearch.py:94-98` | Leaks internal details |
| Exception message exposed to client | `src/plugins/dispatcher.py:78-79` | Leaks internal details |
| No logging of exceptions | Multiple files | No `logging` module used |

### I/O Operations Without Specific Exception Handling

| File:Line | Operation | Missing |
|-----------|-----------|---------|
| `plugins/websearch.py:115-121` | httpx.get() | TimeoutException, ConnectError not caught |
| `plugins/loader.py:103` | open(manifest) | FileNotFoundError, PermissionError |
| `security/audit.py:121` | open(log_path) | No try/except wrapper |

### Recovery Patterns

| Pattern | Status |
|---------|--------|
| Retry logic | ❌ Not implemented |
| Circuit breaker | ❌ Not implemented |
| Fallback mechanisms | ⚠️ Partial (plugin isolation) |

---

## 6. Security Analysis

### Critical Findings

| ID | Severity | File:Line | Description |
|----|----------|-----------|-------------|
| SEC-001 | **HIGH** | `src/server.py:145` | SecurityEngine not integrated - tools executed without validation |
| SEC-002 | **MEDIUM** | `src/plugins/websearch.py:85-86` | No bounds on query/max_results |
| SEC-003 | **MEDIUM** | `src/plugins/websearch.py:96` | Exception messages leak to client |
| SEC-004 | **MEDIUM** | `src/plugins/dispatcher.py:79` | Exception messages leak to client |
| SEC-005 | **LOW** | `src/protocol/jsonrpc.py` | No message size limit before JSON parsing |

### Security Posture

| Category | Score |
|----------|-------|
| Input Validation Framework | 8/10 |
| Path Traversal Protection | 9/10 |
| Network Security | 9/10 |
| Rate Limiting | 7/10 (not integrated) |
| Error Handling | 5/10 (leaks info) |
| **Overall** | **6/10** |

---

## 7. Performance Analysis

### Concerns Identified

| Priority | Issue | File:Line | Impact |
|----------|-------|-----------|--------|
| P1 | No httpx connection pooling | `websearch.py:115` | Latency per request |
| P2 | DNS cache unbounded, no TTL | `firewall.py:70` | Memory leak, stale DNS |
| P2 | Rate limiter keys never pruned | `ratelimiter.py:46` | Memory leak |

### Resource Management

| Pattern | Status |
|---------|--------|
| Context managers | ✅ SecurityEngine, AuditLogger |
| Connection pooling | ❌ httpx creates new client per request |
| Cache TTL | ❌ DNS cache has no expiration |
| Memory bounds | ⚠️ Some unbounded dicts |

---

## 8. Architectural Issues

### Long Methods (>50 lines)

**None found.** Longest method is `_parse_results` at 51 lines (borderline).

### Medium Methods (30-50 lines)

| Method | File:Line | Lines |
|--------|-----------|-------|
| `_parse_results` | `src/plugins/websearch.py:138` | 51 |
| `_load_plugin` | `src/plugins/loader.py:86` | 43 |
| `sanitize_path` | `src/security/validator.py:43` | 42 |
| `_resolve_hostname` | `src/security/firewall.py:96` | 42 |
| `_handle_request` | `src/server.py:110` | 40 |
| `_search` | `src/plugins/websearch.py:100` | 37 |
| `handle_initialize` | `src/protocol/lifecycle.py:81` | 36 |
| `SecurityPolicy.from_dict` | `src/security/policy.py:84` | 36 |

### God Classes (>500 lines or >10 public methods)

**None found.**

### Classes at Threshold

| Class | File | Public Methods |
|-------|------|----------------|
| `SecurityEngine` | engine.py | 10 (exactly at threshold) |

---

## 9. SOLID Violations

### SRP Violations

| Location | Issue | Severity |
|----------|-------|----------|
| None critical | Minor concerns in `PluginLoader._load_plugin()` | Low |

### OCP Violations

| Location | Issue | Recommendation |
|----------|-------|----------------|
| `server.py:138-149` | if/elif chain for routing | Consider handler registry |
| `validator.py:207` | if/elif for format types | Consider validator registry |

### DIP Violations

| Location | Issue | Severity |
|----------|-------|----------|
| `server.py:57-59` | Direct instantiation | Low - internal details |

---

## 10. Dead Code / Unused Code

### Definitely Unused

| File | Item | Notes |
|------|------|-------|
| None found | - | - |

### Potentially Unused

| File | Item | Notes |
|------|------|-------|
| `security/engine.py` | Entire class | Not used in server.py |

**Critical:** The `SecurityEngine` class exists but is never instantiated by `MCPServer`. This represents orphaned security infrastructure.

---

## 11. Code Duplication

**No significant duplication found.** The codebase has clean separation with minimal copy-paste patterns.

---

## 12. Linting & Formatting Status

```
$ uv run ruff check src/ tests/
All checks passed!
```

**Status:** ✅ Clean

---

## 13. Lines of Code

| Category | Lines |
|----------|-------|
| Source (src/) | 2,676 |
| Tests (tests/) | 3,268 |
| **Total** | **5,944** |
| Test:Source Ratio | 1.22:1 |

---

## 14. Technical Debt Inventory

| ID | Item | Category | Severity | Effort | Priority | Location | Acceptance Criteria |
|----|------|----------|----------|--------|----------|----------|---------------------|
| D1 | SecurityEngine not integrated into MCPServer | Security | High | Medium | P1 | `server.py:145` | Tools validated before execution |
| D2 | WebSearchPlugin has unbounded query/max_results | Security | Medium | Low | P1 | `websearch.py:85-86` | Schema has maxLength and maximum |
| D3 | Exception messages leak to clients | Security | Medium | Low | P1 | `websearch.py:96`, `dispatcher.py:79` | Generic error messages returned |
| D4 | httpx creates new client per request | Performance | Medium | Low | P2 | `websearch.py:115` | Shared client with connection pool |
| D5 | DNS cache unbounded, no TTL | Performance | Medium | Medium | P2 | `firewall.py:70` | TTLCache with 5 min expiry |
| D6 | Rate limiter keys never pruned | Performance | Low | Low | P2 | `ratelimiter.py:46` | Cleanup method called periodically |
| D7 | pyright not in dev dependencies | Type Safety | Low | Low | P3 | `pyproject.toml` | pyright runs in CI |
| D8 | No message size limit | Security | Low | Low | P3 | `jsonrpc.py` | Max message size enforced |
| D9 | transport.py swallows exceptions | Exception Handling | Medium | Low | P3 | `transport.py:47-48` | Log errors, catch specific exceptions |
| D10 | No logging framework | Observability | Medium | Medium | P3 | All files | Python logging configured |
| D11 | audit.py branch coverage 75% | Testing | Low | Low | P4 | `audit.py` | Branch coverage >90% |
| D12 | Handler routing uses if/elif | Maintainability | Low | Low | P4 | `server.py:138` | Optional handler registry |

---

## 15. Summary & Recommendations

### Overall Health Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| Test Coverage | ⭐⭐⭐⭐⭐ | 95.94%, excellent |
| Code Complexity | ⭐⭐⭐⭐⭐ | 90.8% A-rated functions |
| Type Safety | ⭐⭐⭐⭐ | 98% coverage, 3 pyright errors |
| Security | ⭐⭐⭐ | Good framework, not integrated |
| Performance | ⭐⭐⭐ | Minor memory concerns |
| Architecture | ⭐⭐⭐⭐ | Clean separation, one integration gap |

### Priority Order for Refactoring

1. **P1 (Critical):** D1, D2, D3 - Security integration and hardening
2. **P2 (High):** D4, D5, D6 - Performance improvements
3. **P3 (Medium):** D7, D8, D9, D10 - Type safety and observability
4. **P4 (Low):** D11, D12 - Nice-to-have improvements

### Risk Areas

1. **Security Layer Disconnected** - The biggest issue is that `SecurityEngine` exists but isn't used. This means rate limiting, input validation, and audit logging are not being enforced.

2. **Information Leakage** - Exception messages expose internal details to clients.

3. **Memory Growth** - DNS cache and rate limiter can grow unbounded over long server lifetimes.
