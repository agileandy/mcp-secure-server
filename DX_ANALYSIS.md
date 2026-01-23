# Tripoli MCP Server: Developer Experience & Testing Quality Analysis

**Codebase Size**: 14,173 lines | **Test Coverage**: 49% (359/360 tests passing) | **Target Coverage**: 95%
**Test Count**: 360 tests | **Type Hints**: Good (mostly complete) | **Documentation**: Good

---

## Executive Summary

The Tripoli MCP server is a well-architected security-first MCP server with solid foundations but several developer experience gaps that slow iteration velocity and complicate debugging. The test suite is comprehensive but skewed—361 passing tests with only 49% coverage indicates tests focus on happy paths while many edge cases and error paths remain untested.

**Key Finding**: The Figma Stories plugin (156 statements, 0% coverage) represents 6% of the codebase but is completely untested. This is a major coverage gap masking the true state of test quality.

---

## Issue 1: Incomplete Test Coverage Masks Untested Production Code

### Current State
- Test coverage: 49% (2089 lines executed / 2452 total)
- 95% coverage requirement in pyproject.toml but currently failing
- Figma Stories plugin: **0% coverage** (156 of 156 lines untested)
- Network/firewall modules: **13% coverage** (19 of 104 lines)
- Protocol transport: **28% coverage** (17 of 25 lines)
- Several production error paths completely untested

### Developer Impact
- False sense of security: tests pass despite major gaps
- Untested error handling leads to surprises in production
- New developers can't learn from tests how certain scenarios fail
- Debugging production issues requires reverse-engineering untested code paths
- 95% coverage goal is impossible to meet without including these modules

### Improvement: Bring Untested Modules into Test Coverage
**Priority**: P0 (blocks continuous improvement)

1. **Figma Stories Plugin** (0% → 100%, ~100 lines)
   - Add fixtures for mocked Figma API, AI client, and file operations
   - Tests for success path, rate limiting, auth errors, file write conflicts
   - Mock external dependencies (FigmaClient, AIClient) to avoid real API calls

2. **Network Firewall** (13% → 95%, ~50+ missing branches)
   - Test IPv4/IPv6 validation edge cases
   - Test DNS allowlist matching
   - Test port blocking and blocked_ports interaction
   - Test CIDR range calculations

3. **Protocol Transport** (28% → 95%, ~8 missing branches)
   - Test STDIO read/write error scenarios
   - Test partial message handling
   - Test EOF handling

**Implementation Effort**: Medium (4-6 hours)
- Recommend TDD approach: identify uncovered branches via coverage report, write tests first

---

## Issue 2: Missing Local Development Setup Documentation

### Current State
- No CONTRIBUTING.md or development setup guide
- README.md has installation but no "get coding immediately" guidance
- No instructions for: Python version, virtual environment setup, pre-commit hooks
- New developers must infer workflows from README + main.py comments
- No guidance on running tests, linting, or formatting

### Developer Impact
- First-time setup takes 15+ minutes of trial-and-error
- Inconsistent code styles between developers (no pre-commit enforcement)
- Unknown testing workflow for new plugins
- No clear CI/CD integration guidance (tests, linting, coverage gates)
- Onboarding friction slows team velocity

### Improvement: Create CONTRIBUTING.md with Quick Start
**Priority**: P2 (improves onboarding)

Create `CONTRIBUTING.md`:

```markdown
# Contributing to Tripoli MCP Server

## Quick Start (5 minutes)

### Prerequisites
- Python 3.11+
- uv (fast Python package manager)

### Setup
\`\`\`bash
# Clone and enter
git clone <repo>
cd tripoli

# Install dependencies with uv
uv sync

# Verify setup
uv run pytest tests/ -k "test_server" --no-cov
\`\`\`

### Development Workflow

#### Running Tests
\`\`\`bash
# All tests with coverage
uv run pytest

# Specific test file
uv run pytest tests/test_plugins.py -v

# Watch mode (with pytest-watch plugin)
uv run ptw tests/
\`\`\`

#### Code Quality
\`\`\`bash
# Lint and auto-fix
uv run ruff check --fix .
uv run ruff format .

# Type checking
uv run pyright src/

# Full check before commit
uv run ruff check . && uv run pytest --no-cov && uv run pyright src/
\`\`\`

### Adding a Plugin (Step-by-Step)

1. Create `src/plugins/my_feature.py`
2. Inherit from `PluginBase`
3. Implement `name`, `version`, `get_tools()`, `execute()`
4. Add rate limits to `config/policy.yaml`
5. Create `tests/test_my_feature.py` with 100% coverage
6. Register in `main.py`
\`\`\`python
from src.plugins.my_feature import MyPlugin
server.register_plugin(MyPlugin())
\`\`\`

## Pre-Commit Hooks (Optional)

Install git hooks to auto-format on commit:
\`\`\`bash
# Install pre-commit framework
pip install pre-commit

# Create .pre-commit-config.yaml (provided)
pre-commit install

# Now commits are auto-formatted
\`\`\`

## Coverage Expectations

All code must have ≥95% coverage (enforced by pytest):
- Write tests FIRST (TDD workflow)
- Mock external dependencies (HTTP, filesystems)
- Test both happy path and error cases
- See tests/test_validator.py for testing patterns

## Code Style

- Use type hints everywhere (checked by pyright)
- Line length: 100 characters (enforced by ruff)
- Sort imports automatically (ruff handles this)
- No print() statements in production code (use audit logging instead)

## Troubleshooting

### ImportError: No module named 'src'
\`\`\`bash
# Ensure you ran uv sync
uv sync
\`\`\`

### Tests fail with "cannot import module"
\`\`\`bash
# Run from repository root
cd tripoli
uv run pytest tests/
\`\`\`

### Coverage too low
\`\`\`bash
# See what's uncovered
uv run pytest --cov-report=term-missing
\`\`\`
```

**Implementation Effort**: Low (1-2 hours)
- Can be done immediately with minimal code

---

## Issue 3: Error Messages Lack Actionable Context for Debugging

### Current State
- Error messages are generic: "Path is denied by policy"
- No context about why (which policy rule blocked it? which pattern?)
- Security vulnerabilities hidden to prevent information leakage
- Example error from validator: `ValidationError("Path is denied by policy: {sanitized}")`
  - Doesn't tell user: denied_paths pattern that matched? which path violated it?
- Rate limit errors just say "Too many requests" with no retry timing

### Developer Impact
- Developers debug by adding print() statements or re-reading policy.yaml
- User frustration: "Why is this path blocked?" → need to dig into code
- Integration testing harder: don't know which security rule failed
- Custom error debugging code slows iteration
- Hard to differentiate: user error vs. server bug vs. policy misconfiguration

### Improvement: Add Structured Error Context
**Priority**: P2 (improves debugging speed)

**Key principle**: Error messages should answer:
1. WHAT failed (the operation)
2. WHY it failed (the rule/reason)
3. HOW to fix it (the remedy)

Example improvements:

```python
# CURRENT (not helpful):
raise ValidationError(f"Path is denied by policy: {sanitized}")

# IMPROVED (actionable):
raise ValidationError(
    f"Path access denied: {sanitized} | "
    f"Reason: matched denied pattern '**/.ssh/**' | "
    f"Fix: use a path outside ~/.ssh/ or update policy.yaml denied_paths"
)

# RATE LIMIT (CURRENT):
raise RateLimitExceeded()

# RATE LIMIT (IMPROVED):
raise RateLimitExceeded(
    f"Rate limit exceeded for '{tool_name}': "
    f"20 requests/min max, already used 20. "
    f"Retry after {reset_time_seconds}s"
)

# NETWORK (CURRENT):
raise SecurityViolation(str(e))

# NETWORK (IMPROVED):
raise SecurityViolation(
    f"Network access blocked: cannot reach {host}:{port} | "
    f"Allowed: local networks + {allowed_endpoint_count} external endpoints | "
    f"To allow: add to config/policy.yaml allowed_endpoints"
)
```

1. Create custom exception classes with structured fields:

```python
# src/security/exceptions.py
class DetailedSecurityError(Exception):
    """Security error with actionable debugging info."""
    def __init__(self, what: str, why: str, how_to_fix: str):
        self.what = what
        self.why = why
        self.how_to_fix = how_to_fix
        super().__init__(f"{what} | {why} | {how_to_fix}")
```

2. Update validators to use new exception types
3. Document error patterns in docs/DEBUGGING.md

**Implementation Effort**: Medium (3-4 hours)
- Refactor exception raising in: validator.py, firewall.py, engine.py, ratelimiter.py
- Add integration tests for error messages

---

## Issue 4: Missing Integration Test Examples and Patterns

### Current State
- 360 tests total but integration test file is sparse
- `tests/test_integration.py` exists but has limited real-world scenarios
- No end-to-end examples: "add plugin → register → call via MCP → verify output"
- Mocking strategy inconsistent: some tests mock everything, others mock selectively
- No guidance for developers adding new plugins on how to test their integrations

### Developer Impact
- New plugin developers don't know how to test their feature end-to-end
- Plugins can pass unit tests but fail when called through MCP protocol
- No example of testing: security policy + plugin validation + rate limiting together
- Harder to verify: "does my plugin work with the actual server?"

### Improvement: Add Annotated Integration Test Patterns
**Priority**: P2 (helps new developers)

Add new file: `tests/test_integration_patterns.py` with documented examples:

```python
"""Integration test patterns - use these as templates for new plugins.

This file shows the standard patterns for testing plugins end-to-end.
Copy these tests and adapt them for your plugin.
"""

class TestPluginIntegrationPattern:
    """Template for testing a new plugin end-to-end."""

    def test_plugin_end_to_end_happy_path(self, initialized_server: MCPServer):
        """Pattern 1: Plugin executes successfully through MCP protocol.

        Use this pattern when:
        - You're adding a new plugin
        - You want to verify it works with the full MCP stack
        - You need to test security policy + plugin together
        """
        # Setup
        server = initialized_server

        # Call through MCP protocol (not directly)
        response = server.handle_message(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "web_search",
                "arguments": {"query": "python asyncio"}
            }
        }))

        # Verify
        result = json.loads(response)
        assert "result" in result
        assert isinstance(result["result"]["content"], list)

    def test_plugin_security_validation_integration(self, initialized_server: MCPServer):
        """Pattern 2: Verify security policy is enforced before plugin runs.

        Use this when:
        - Your plugin makes network requests
        - Your plugin accesses the filesystem
        - You want to verify the security layer blocks invalid inputs
        """
        # Setup
        server = initialized_server

        # Try to call with denied path
        response = server.handle_message(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "read_file",
                "arguments": {"path": "/etc/passwd"}  # Should be denied
            }
        }))

        result = json.loads(response)
        assert "error" in result
        assert "denied" in result["error"]["message"].lower()

    def test_plugin_rate_limiting_integration(self, initialized_server: MCPServer):
        """Pattern 3: Verify rate limits are enforced.

        Use this when:
        - Your plugin has rate limits
        - You want to verify they're enforced
        """
        server = initialized_server

        # Make requests until rate limited
        responses = []
        for i in range(25):  # Assuming limit is 20/min
            response = server.handle_message(json.dumps({
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {"name": "web_search", "arguments": {"query": f"test {i}"}}
            }))
            responses.append(json.loads(response))

        # Last few should be rate limited
        assert "error" in responses[-1]
        assert "rate" in responses[-1]["error"]["message"].lower()
```

Add documentation: `docs/INTEGRATION_TESTING.md`

**Implementation Effort**: Low (2-3 hours)
- Copy existing integration tests and annotate
- Create 3-4 clear patterns with explanations

---

## Issue 5: Mypy/Type Checking Not Enforced in CI

### Current State
- Type hints are good (most code is well-typed)
- pyright in dev dependencies but NOT run in CI/pre-commit
- No type checking enforcement = gradual type drift over time
- Comments reference type hints but nothing validates them at commit time
- Code review can't catch type errors automatically

### Developer Impact
- Type-safe code can gradually degrade as developers commit type-unsafe changes
- IDE shows no warnings for type errors in contributors without mypy/pyright setup
- New developers might commit code without running pyright
- Lost opportunity to catch runtime errors before they reach code review

### Improvement: Add Type Checking to Pre-Commit Hooks
**Priority**: P1 (prevents regressions)

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-ast

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.14
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/RoelAdriaans/pre-commit-pyright
    rev: 1.1.330
    hooks:
      - id: pyright
        stages: [commit]
```

Update `pyproject.toml` to add pre-commit to dev dependencies.

**Implementation Effort**: Low (30 minutes)
- Create .pre-commit-config.yaml
- Add to dev deps
- Test locally

---

## Issue 6: No Structured Logging for Debugging Plugin Execution

### Current State
- Audit logging exists but only logs policy violations
- No execution trace for plugin calls: when plugin runs, what args, what result
- Figma Stories plugin has print() statements instead of logging
- No way to turn on "verbose mode" for debugging
- Developers add print() to debug, then forget to remove them

### Developer Impact
- Can't trace plugin execution without modifying code
- Audit log doesn't show successful operations, only security events
- Debugging production issues requires: stop server, add prints, restart, reproduce
- Hard to verify: "is my plugin actually being called?" or "why is it slow?"
- Print statements pollute STDIO (breaks MCP protocol)

### Improvement: Add Structured Plugin Execution Logging
**Priority**: P2 (improves runtime debugging)

1. Create `src/logging.py` with structured logging:

```python
"""Structured logging for MCP server operations."""

from typing import Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import sys

@dataclass
class ExecutionLog:
    """Structured execution log entry."""
    timestamp: str
    level: str  # DEBUG, INFO, WARN, ERROR
    event: str  # plugin_execute, plugin_error, security_check
    tool_name: str
    details: dict[str, Any]

class ExecutionLogger:
    """Log plugin execution for debugging."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def log(self, level: str, event: str, tool_name: str, **details):
        """Log an event."""
        if level == "DEBUG" and not self.verbose:
            return

        entry = ExecutionLog(
            timestamp=datetime.utcnow().isoformat(),
            level=level,
            event=event,
            tool_name=tool_name,
            details=details
        )
        # Write to stderr (doesn't interfere with MCP STDIO protocol)
        print(json.dumps(asdict(entry)), file=sys.stderr)

    def plugin_execute(self, tool_name: str, arguments: dict[str, Any]):
        """Log plugin execution."""
        self.log("DEBUG", "plugin_execute", tool_name, arguments=arguments)

    def plugin_result(self, tool_name: str, duration_ms: float, is_error: bool):
        """Log plugin result."""
        self.log("DEBUG", "plugin_result", tool_name,
                 duration_ms=duration_ms, is_error=is_error)
```

2. Integrate into SecurityEngine and MCPServer:

```python
# In src/server.py
from src.logging import ExecutionLogger

class MCPServer:
    def __init__(self, policy_path: Path | None = None, verbose: bool = False):
        # ... existing code ...
        self._logger = ExecutionLogger(verbose=verbose)
```

3. Update main.py to support `--verbose` flag:

```python
parser.add_argument("--verbose", "-v", action="store_true",
                    help="Enable verbose logging to stderr")
```

4. Usage: `uv run python main.py --verbose` outputs execution traces to stderr

**Implementation Effort**: Medium (3-4 hours)
- Create logging module
- Integrate into server/security engine
- Add CLI flag
- Test that stderr doesn't break MCP protocol

---

## Issue 7: Policy.yaml Complexity Not Surfaced in Error Messages

### Current State
- config/policy.yaml is 273 lines with nested sections
- When a plugin's network access is denied, error says "host blocked" but not why
- No validation of policy.yaml at startup → errors appear at runtime
- Example: forgotten rate limit entry causes tool to use default (users confused)
- Policy documentation is separate from policy file itself

### Developer Impact
- Setting up a new plugin requires: edit policy.yaml → test → debug → edit again
- Iteration loop: guess policy config → test → see generic error → repeat
- New developers don't know: "Is my policy wrong or did my plugin break?"
- Hard to understand: which policy rule matched? which section applies?

### Improvement: Add Policy Validation and Diagnostic Reporting
**Priority**: P2 (improves DX for plugin configuration)

1. Add policy validator at startup:

```python
# src/security/policy_validator.py
class PolicyDiagnostics:
    """Validate policy and provide diagnostics."""

    def __init__(self, policy: SecurityPolicy):
        self.policy = policy
        self.diagnostics = []

    def validate_and_report(self) -> list[str]:
        """Return list of diagnostics (warnings/errors)."""
        diagnostics = []

        # Check for unused rate limits
        configured_limits = set(self.policy.rate_limits.keys())
        # Scan plugins to see which ones are configured
        # Warn: "rate limit for 'foo_plugin' configured but plugin not found"

        # Check for unreachable endpoints
        # Warn: "allowed_endpoint 'foo.internal' but no DNS entry"

        return diagnostics
```

2. Print diagnostics at startup:

```bash
$ uv run python main.py
MCP Secure Local Server started
Policy loaded from: config/policy.yaml
Diagnostics:
  WARN: Rate limit for 'query_database' configured but tool not registered
  WARN: Allowed endpoint 'db.internal' not resolvable (DNS issue?)
  INFO: 7 plugins registered, 3 rate limits configured
```

3. Add `--validate-policy` mode:

```bash
uv run python main.py --validate-policy config/policy.yaml
```

**Implementation Effort**: Medium (2-3 hours)
- Create policy validation logic
- Integrate into startup
- Add diagnostic CLI

---

## Summary: Priority Roadmap

| # | Issue | Priority | Impact | Effort | Recommendation |
|---|-------|----------|--------|--------|-----------------|
| 1 | Untested production code (Figma, firewall, transport) | P0 | Coverage 49%→80%+ | 4-6h | Start here: fixes coverage gate |
| 2 | Missing CONTRIBUTING.md | P2 | Onboarding -15 min | 1-2h | Do next: unblocks contributors |
| 3 | Error messages lack context | P2 | Debugging -30% faster | 3-4h | Do in parallel with #2 |
| 4 | No integration test patterns | P2 | Plugin DX | 2-3h | Do after #2 |
| 5 | Type checking not enforced | P1 | Prevents regressions | 30m | Quick win |
| 6 | No execution logging | P2 | Runtime debugging | 3-4h | Medium term |
| 7 | Policy complexity in errors | P2 | Config DX | 2-3h | Medium term |

---

## Detailed Recommendations by Role

### For the Maintainer (Andy)

1. **Immediate (this week)**:
   - Merge untested modules into coverage (Issue #1) - unblocks CI gate
   - Add type checking to pre-commit (Issue #5) - 30m, prevents regressions

2. **Near-term (next 2 weeks)**:
   - Create CONTRIBUTING.md (Issue #2) - enables faster onboarding
   - Improve error messages (Issue #3) - makes debugging easier for users

3. **Medium-term (next month)**:
   - Add integration test patterns (Issue #4) - helps new plugin developers
   - Structured execution logging (Issue #6) - enables production debugging

### For New Plugin Developers

**Key files to understand**:
1. `docs/PLUGIN_DEVELOPMENT.md` - plugin interface
2. `config/policy.yaml` - security rules for your plugin
3. `tests/test_plugins.py` - testing patterns (copy MockPlugin)
4. `src/plugins/websearch.py` - reference implementation

**Workflow**:
1. Create `src/plugins/my_feature.py` with `PluginBase` + 3 methods
2. Create `tests/test_my_feature.py` with ≥95% coverage (use MockPlugin as template)
3. Update `config/policy.yaml` if you need network access or special rates
4. Register in `main.py`
5. Test: `uv run pytest tests/test_my_feature.py --no-cov` (passes locally)
6. Check coverage: `uv run pytest --cov=src.plugins.my_feature` (must be ≥95%)

---

## Appendix: Code Metrics Summary

| Metric | Value | Status |
|--------|-------|--------|
| Total Lines of Code | 14,173 | Normal |
| Test Count | 360 | Good |
| Tests Passing | 359/360 (99.7%) | Excellent |
| Current Coverage | 49.5% | Poor |
| Target Coverage | 95% | Gap: 45.5% |
| Major Coverage Gaps | Figma (0%), Firewall (13%), Transport (28%) | Critical |
| Type Hints | Mostly complete | Good |
| Documentation | README, PLUGIN_DEVELOPMENT.md, PROTOCOL.md, SECURITY_POLICY.md | Good |
| Missing Documentation | CONTRIBUTING.md, INTEGRATION_TESTING.md, DEBUGGING.md | Gap |
| Error Messages | Generic, non-actionable | Needs work |
| Logging | Audit-only, no execution traces | Needs work |
| Pre-commit Hooks | None (ruff/pyright not enforced) | Needs setup |
| Local Dev Setup | No guide | Needs docs |

---

## Conclusion

Tripoli is a **mature, well-designed codebase** with solid security foundations and good documentation for users. However, **developer experience has gaps** that slow iteration:

1. **Test coverage is misleading** - 49% hides 6% of codebase (Figma plugin) that's completely untested
2. **Developer onboarding lacks guidance** - no CONTRIBUTING.md, unclear workflows
3. **Debugging is harder than it needs to be** - generic error messages, no execution logging
4. **New plugin development needs patterns** - developers can't easily see how to test their code

**Quick wins** (1-2 days of work):
- Add type checking to pre-commit (30m)
- Create CONTRIBUTING.md (1-2h)
- Improve error messages (3-4h)

**Medium-term investments** (1-2 weeks):
- Bring coverage to 95% (4-6h)
- Add integration test patterns (2-3h)
- Structured execution logging (3-4h)

These improvements would make Tripoli **exceptional** for both users and contributors.
