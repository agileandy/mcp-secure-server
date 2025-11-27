# Refactor Action Plan

**Session Directory:** `.refactor/20251127-155100/`  
**Baseline Commit:** `d3342dc021a4902d0b47ddd4b5fec131b89a031d`  
**Created:** 2025-11-27T15:51:00

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

- **Total Actions:** 12
- **Completed:** 11
- **Remaining:** 1 (A12 - CANCELLED - P4 nice-to-have)
- **Current Phase:** COMPLETE

---

## Action Table

| ID | Debt ID | Action | Category | Files | Est. Lines | Status | Commit Hash |
|----|---------|--------|----------|-------|------------|--------|-------------|
| A1 | D1 | Integrate SecurityEngine into MCPServer | P1-Security | server.py | +30 | DONE | 1761ab7 |
| A2 | D2 | Add bounds to WebSearchPlugin schema | P1-Security | websearch.py | +5 | DONE | 50f3842 |
| A3 | D3 | Sanitize exception messages in websearch | P1-Security | websearch.py | +10 | DONE | 7376070 |
| A4 | D3 | Sanitize exception messages in dispatcher | P1-Security | dispatcher.py | +5 | DONE | 351df91 |
| A5 | D4 | Add httpx connection pooling | P2-Performance | websearch.py | +20 | DONE | c12f198 |
| A6 | D5 | Add TTL cache for DNS | P2-Performance | firewall.py, pyproject.toml | +15 | DONE | 8deba82 |
| A7 | D6 | Add rate limiter bucket cleanup | P2-Performance | ratelimiter.py | +15 | DONE | 394ce41 |
| A8 | D7 | Add pyright to dev dependencies | P3-TypeSafety | pyproject.toml | +2 | DONE | d293354 |
| A9 | D7 | Fix pyright errors | P3-TypeSafety | firewall.py, validator.py | +5 | DONE | 18f1433 |
| A10 | D9 | Fix transport.py exception handling | P3-ExceptionHandling | transport.py | +10 | DONE | e8b0dfb |
| A11 | D8 | Add message size limit to jsonrpc | P3-Security | jsonrpc.py | +10 | DONE | 2de19b7 |
| A12 | D11 | Improve audit.py branch coverage | P4-Testing | test_audit.py | +30 | CANCELLED | - |

---

## Parallel Groups

### Parallel Group PG1 (P1 Security Fixes)
These actions have no interdependencies and CAN be executed by parallel sub-agents:
- A2: Add bounds to WebSearchPlugin schema
- A3: Sanitize exception messages in websearch  
- A4: Sanitize exception messages in dispatcher

**Note:** A1 (SecurityEngine integration) should be done AFTER A2-A4 since it depends on stable plugin behavior.

### Sequential Group SG1 (Security Integration)
Must be executed in order:
1. A2, A3, A4 (parallel)
2. A1: Integrate SecurityEngine

### Parallel Group PG2 (P2 Performance)
These actions can be executed in parallel:
- A5: httpx connection pooling
- A6: DNS TTL cache  
- A7: Rate limiter cleanup

### Parallel Group PG3 (P3 Improvements)
These actions can be executed in parallel:
- A8: Add pyright (must be before A9)
- A10: transport.py fix
- A11: message size limit

### Sequential Group SG2 (Type Safety)
Must be executed in order:
1. A8: Add pyright
2. A9: Fix pyright errors

---

## Detailed Action Specifications

### A1: Integrate SecurityEngine into MCPServer
**Addresses:** D1 - SecurityEngine not integrated into MCPServer  
**Category:** P1-Security

**Context:**
The `SecurityEngine` class exists in `src/security/engine.py` with full rate limiting, input validation, and audit logging capabilities. However, `MCPServer` in `src/server.py` never instantiates or uses it. Tools are executed at line 145 without any security checks.

**Pre-conditions:**
- A2, A3, A4 completed (plugin behavior stable)
- All existing tests pass

**Steps:**
1. RED: Write test in `tests/test_server.py`:
   - Test that tool calls go through rate limiting
   - Test that invalid input is rejected
   - Test that audit logging is called
2. GREEN: Modify `MCPServer.__init__()` to instantiate `SecurityEngine`
3. GREEN: Modify `_handle_request()` to:
   - Call `check_rate_limit()` before tool execution
   - Call `validate_input()` with tool schema before execution
   - Call `log_tool_execution()` and `log_tool_result()`
4. GREEN: Add context manager support to close SecurityEngine
5. REFACTOR: Ensure error handling wraps SecurityViolation appropriately

**Files Changed:**
- `src/server.py` (+30 lines, -0 lines)
- `tests/test_server.py` (+50 lines)

**Tests:**
- New: 3-5 unit tests for security integration
- Existing: All existing tests must pass unchanged

**Acceptance Criteria:**
- [ ] SecurityEngine instantiated in MCPServer
- [ ] Rate limiting enforced on tool calls
- [ ] Input validation called before tool execution
- [ ] Audit logging records tool executions
- [ ] All existing tests pass
- [ ] New tests for security integration pass

**Commit Message:** `feat(server): integrate SecurityEngine for rate limiting and validation [D1]`

---

### A2: Add bounds to WebSearchPlugin schema
**Addresses:** D2 - WebSearchPlugin has unbounded query/max_results  
**Category:** P1-Security

**Context:**
The `WebSearchPlugin` at line 85-86 accepts `query` and `max_results` without bounds. This could cause memory exhaustion or HTTP request issues with extremely long queries or large result counts.

**Pre-conditions:**
- None (independent action)

**Steps:**
1. RED: Write test that validates schema rejects:
   - Query > 500 characters
   - max_results > 20
   - max_results < 1
2. GREEN: Update `get_tools()` schema:
   ```python
   "query": {"type": "string", "maxLength": 500}
   "max_results": {"type": "integer", "minimum": 1, "maximum": 20}
   ```
3. REFACTOR: Update `execute()` to use schema defaults

**Files Changed:**
- `src/plugins/websearch.py` (+5 lines)
- `tests/test_websearch.py` (+15 lines)

**Tests:**
- New: 3 tests for schema bounds
- Existing: All websearch tests must pass

**Acceptance Criteria:**
- [ ] Schema has `maxLength: 500` on query
- [ ] Schema has `minimum: 1, maximum: 20` on max_results
- [ ] Tests verify bounds enforcement
- [ ] All existing tests pass

**Commit Message:** `fix(websearch): add bounds to query and max_results schema [D2]`

---

### A3: Sanitize exception messages in websearch
**Addresses:** D3 - Exception messages leak to clients  
**Category:** P1-Security

**Context:**
At `websearch.py:94-98`, raw exception messages are returned to clients. This could leak:
- Internal IP addresses/hostnames
- File paths
- Connection error details

**Pre-conditions:**
- None (independent action)

**Steps:**
1. RED: Write test that verifies error messages don't contain:
   - IP addresses
   - File paths
   - Stack traces
2. GREEN: Update exception handler:
   ```python
   except httpx.TimeoutException:
       return ToolResult(
           content=[{"type": "text", "text": "Search timed out. Please try again."}],
           is_error=True,
       )
   except httpx.HTTPStatusError as e:
       return ToolResult(
           content=[{"type": "text", "text": f"Search failed (HTTP {e.response.status_code})"}],
           is_error=True,
       )
   except Exception:
       return ToolResult(
           content=[{"type": "text", "text": "Search failed. Please try again later."}],
           is_error=True,
       )
   ```
3. REFACTOR: Consider adding logging for debugging (future action)

**Files Changed:**
- `src/plugins/websearch.py` (+10 lines, -4 lines)
- `tests/test_websearch.py` (+10 lines)

**Tests:**
- New: 2-3 tests for sanitized error messages
- Existing: All websearch tests must pass

**Acceptance Criteria:**
- [ ] Timeout errors return generic message
- [ ] HTTP errors return status code only
- [ ] Unknown errors return generic message
- [ ] No internal details leaked
- [ ] All tests pass

**Commit Message:** `fix(websearch): sanitize exception messages to prevent info leakage [D3]`

---

### A4: Sanitize exception messages in dispatcher
**Addresses:** D3 - Exception messages leak to clients  
**Category:** P1-Security

**Context:**
At `dispatcher.py:78-79`, exception messages are included in `ToolExecutionError`. This could leak internal details.

**Pre-conditions:**
- None (independent action)

**Steps:**
1. RED: Write test that verifies `ToolExecutionError` doesn't expose internal details
2. GREEN: Update exception handler:
   ```python
   except Exception as e:
       # Log full error for debugging (when logging is added)
       raise ToolExecutionError(f"Tool '{tool_name}' execution failed") from e
   ```
3. REFACTOR: Ensure `from e` preserves chain for debugging

**Files Changed:**
- `src/plugins/dispatcher.py` (+5 lines, -2 lines)
- `tests/test_plugins.py` (+5 lines)

**Tests:**
- New: 1-2 tests for sanitized error
- Existing: All dispatcher tests must pass

**Acceptance Criteria:**
- [ ] ToolExecutionError message is generic
- [ ] Exception chain preserved (from e)
- [ ] All tests pass

**Commit Message:** `fix(dispatcher): sanitize exception messages in tool execution [D3]`

---

### A5: Add httpx connection pooling
**Addresses:** D4 - httpx creates new client per request  
**Category:** P2-Performance

**Context:**
At `websearch.py:115`, `httpx.get()` creates a new client per request. This causes:
- TCP handshake overhead per request
- No HTTP/2 connection reuse
- No keep-alive benefits

**Pre-conditions:**
- A3 completed (exception handling stable)

**Steps:**
1. RED: Write test that verifies:
   - Multiple searches reuse the same client
   - Client is properly closed on plugin cleanup
2. GREEN: Add shared client in `__init__`:
   ```python
   def __init__(self) -> None:
       self._client = httpx.Client(
           timeout=10.0,
           limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
           headers={"User-Agent": USER_AGENT},
           follow_redirects=True,
       )
   ```
3. GREEN: Add cleanup method:
   ```python
   def close(self) -> None:
       self._client.close()
   ```
4. GREEN: Update `_search` to use `self._client.get()`
5. REFACTOR: Consider making `PluginBase` require `close()` (future)

**Files Changed:**
- `src/plugins/websearch.py` (+20 lines, -5 lines)
- `tests/test_websearch.py` (+15 lines)

**Tests:**
- New: 2-3 tests for connection pooling
- Existing: All websearch tests must pass

**Acceptance Criteria:**
- [ ] Shared httpx.Client created in __init__
- [ ] close() method cleans up client
- [ ] Connection limits configured
- [ ] All tests pass

**Commit Message:** `perf(websearch): add httpx connection pooling [D4]`

---

### A6: Add TTL cache for DNS
**Addresses:** D5 - DNS cache unbounded, no TTL  
**Category:** P2-Performance

**Context:**
At `firewall.py:70`, `_dns_cache` is an unbounded dict with no TTL. DNS entries never expire, causing:
- Stale DNS resolution
- Memory growth with unique hostnames

**Pre-conditions:**
- None (independent action)

**Steps:**
1. Add `cachetools` to dependencies
2. RED: Write test that verifies:
   - DNS cache entries expire after TTL
   - Cache has maximum size
3. GREEN: Replace dict with TTLCache:
   ```python
   from cachetools import TTLCache
   
   self._dns_cache: TTLCache[str, str] = TTLCache(maxsize=1000, ttl=300)
   ```
4. REFACTOR: Update cache access patterns if needed

**Files Changed:**
- `pyproject.toml` (+1 line)
- `src/security/firewall.py` (+10 lines, -2 lines)
- `tests/test_firewall.py` (+15 lines)

**Tests:**
- New: 2-3 tests for TTL cache behavior
- Existing: All firewall tests must pass

**Acceptance Criteria:**
- [ ] cachetools added to dependencies
- [ ] DNS cache uses TTLCache
- [ ] maxsize=1000, ttl=300 configured
- [ ] All tests pass

**Commit Message:** `perf(firewall): add TTL and size limit to DNS cache [D5]`

---

### A7: Add rate limiter bucket cleanup
**Addresses:** D6 - Rate limiter keys never pruned  
**Category:** P2-Performance

**Context:**
At `ratelimiter.py:46`, `_buckets` dict keys are never removed. List values are pruned on access, but stale tool entries accumulate indefinitely.

**Pre-conditions:**
- None (independent action)

**Steps:**
1. RED: Write test that verifies:
   - Stale bucket entries are cleaned up
   - Cleanup runs periodically or on access
2. GREEN: Add cleanup method:
   ```python
   def _cleanup_stale_buckets(self) -> None:
       now = time.time()
       stale = [k for k, v in self._buckets.items() 
                if not v or max(v) < now - self._window_seconds]
       for k in stale:
           del self._buckets[k]
   ```
3. GREEN: Call cleanup in `check_rate_limit()` (every N calls or time-based)
4. REFACTOR: Consider probabilistic cleanup to avoid overhead

**Files Changed:**
- `src/security/ratelimiter.py` (+15 lines)
- `tests/test_ratelimiter.py` (+15 lines)

**Tests:**
- New: 2-3 tests for bucket cleanup
- Existing: All ratelimiter tests must pass

**Acceptance Criteria:**
- [ ] Stale bucket entries removed
- [ ] Cleanup doesn't impact performance significantly
- [ ] All tests pass

**Commit Message:** `perf(ratelimiter): add stale bucket cleanup [D6]`

---

### A8: Add pyright to dev dependencies
**Addresses:** D7 - pyright not in dev dependencies  
**Category:** P3-TypeSafety

**Context:**
Type checking with pyright is not enforced. Adding it to dev dependencies enables CI integration.

**Pre-conditions:**
- None (independent action)

**Steps:**
1. Add pyright to pyproject.toml dev dependencies
2. Add pyright config section
3. Run pyright to verify current errors

**Files Changed:**
- `pyproject.toml` (+10 lines)

**Tests:**
- None (tooling change)

**Acceptance Criteria:**
- [ ] pyright in dev dependencies
- [ ] pyright config in pyproject.toml
- [ ] `uv run pyright src/` runs successfully

**Commit Message:** `chore(deps): add pyright for type checking [D7]`

---

### A9: Fix pyright errors
**Addresses:** D7 - pyright errors  
**Category:** P3-TypeSafety

**Context:**
3 pyright errors exist:
1. `firewall.py:134` - Type mismatch in DNS cache
2. `firewall.py:135` - Return type mismatch
3. `validator.py:271` - jsonschema.exceptions import

**Pre-conditions:**
- A8 completed (pyright available)

**Steps:**
1. Fix `firewall.py:134-135`:
   - Cast IP address to str explicitly
2. Fix `validator.py:271`:
   - Import SchemaError directly from jsonschema.exceptions
3. Run pyright to verify no errors

**Files Changed:**
- `src/security/firewall.py` (+2 lines, -2 lines)
- `src/security/validator.py` (+1 line, -1 line)

**Tests:**
- Existing: All tests must pass

**Acceptance Criteria:**
- [ ] pyright reports 0 errors
- [ ] All tests pass

**Commit Message:** `fix(types): resolve pyright type errors [D7]`

---

### A10: Fix transport.py exception handling
**Addresses:** D9 - transport.py swallows exceptions  
**Category:** P3-ExceptionHandling

**Context:**
At `transport.py:47-48`, a bare `except Exception` returns None, silently swallowing all errors. This makes debugging difficult.

**Pre-conditions:**
- None (independent action)

**Steps:**
1. RED: Write test that verifies specific exceptions are caught
2. GREEN: Replace generic handler:
   ```python
   try:
       line = self._stdin.readline()
   except (OSError, IOError) as e:
       # Log error when logging is added
       return None
   ```
3. REFACTOR: Consider whether other exceptions should propagate

**Files Changed:**
- `src/protocol/transport.py` (+5 lines, -2 lines)
- `tests/test_integration.py` (+10 lines)

**Tests:**
- New: 1-2 tests for exception handling
- Existing: All transport tests must pass

**Acceptance Criteria:**
- [ ] Only OSError/IOError caught
- [ ] Other exceptions propagate
- [ ] All tests pass

**Commit Message:** `fix(transport): catch specific exceptions instead of generic Exception [D9]`

---

### A11: Add message size limit to jsonrpc
**Addresses:** D8 - No message size limit before JSON parsing  
**Category:** P3-Security

**Context:**
`parse_message` in `jsonrpc.py` parses JSON without checking message size first. A malicious client could send a very large message to exhaust memory.

**Pre-conditions:**
- None (independent action)

**Steps:**
1. RED: Write test that verifies messages > 1MB are rejected
2. GREEN: Add size check in `parse_message`:
   ```python
   MAX_MESSAGE_SIZE = 1_048_576  # 1 MB
   
   def parse_message(raw: str) -> JsonRpcRequest | JsonRpcNotification:
       if len(raw) > MAX_MESSAGE_SIZE:
           raise JsonRpcError(INVALID_REQUEST, "Message too large")
       ...
   ```
3. REFACTOR: Consider making limit configurable

**Files Changed:**
- `src/protocol/jsonrpc.py` (+10 lines)
- `tests/test_jsonrpc.py` (+10 lines)

**Tests:**
- New: 2 tests for size limit
- Existing: All jsonrpc tests must pass

**Acceptance Criteria:**
- [ ] MAX_MESSAGE_SIZE constant defined
- [ ] Messages > limit rejected with JsonRpcError
- [ ] All tests pass

**Commit Message:** `fix(jsonrpc): add message size limit to prevent memory exhaustion [D8]`

---

### A12: Improve audit.py branch coverage
**Addresses:** D11 - audit.py branch coverage 75%  
**Category:** P4-Testing

**Context:**
`audit.py` has 75% branch coverage, the lowest in the codebase. Missing tests likely cover file operation edge cases.

**Pre-conditions:**
- None (independent action)

**Steps:**
1. Identify uncovered branches using coverage report
2. Write tests for:
   - File open failures
   - Write failures
   - Context manager edge cases
3. Verify branch coverage > 90%

**Files Changed:**
- `tests/test_audit.py` (+30 lines)

**Tests:**
- New: 5-8 tests for edge cases

**Acceptance Criteria:**
- [ ] Branch coverage > 90%
- [ ] All error paths tested
- [ ] All tests pass

**Commit Message:** `test(audit): improve branch coverage to >90% [D11]`

---

## Execution Checklist

### Phase P1 (Critical Security)
- [ ] A2: Add bounds to WebSearchPlugin schema
- [ ] A3: Sanitize exception messages in websearch
- [ ] A4: Sanitize exception messages in dispatcher
- [ ] A1: Integrate SecurityEngine into MCPServer

### Phase P2 (Performance)
- [ ] A5: Add httpx connection pooling
- [ ] A6: Add TTL cache for DNS
- [ ] A7: Add rate limiter bucket cleanup

### Phase P3 (Improvements)
- [ ] A8: Add pyright to dev dependencies
- [ ] A9: Fix pyright errors
- [ ] A10: Fix transport.py exception handling
- [ ] A11: Add message size limit to jsonrpc

### Phase P4 (Nice-to-have)
- [ ] A12: Improve audit.py branch coverage

---

## Post-Refactor Verification

After all actions complete:
1. Run full test suite: `uv run pytest -v`
2. Run coverage: `uv run pytest --cov=src --cov-fail-under=95`
3. Run linter: `uv run ruff check src/ tests/`
4. Run type checker: `uv run pyright src/`
5. Create completion report
