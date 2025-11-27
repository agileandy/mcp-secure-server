"""Bug tracker plugin for MCP server.

Provides lightweight bug tracking functionality with per-project isolation
and cross-project search capabilities.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Callable

from src.plugins.base import PluginBase, ToolDefinition, ToolResult

# =============================================================================
# Project Index (for cross-project search)
# =============================================================================


def get_project_index_path() -> Path:
    """Get path to the central project index file.

    Returns:
        Path to ~/.bugtracker/projects.json
    """
    home = Path(os.environ.get("HOME", os.path.expanduser("~")))
    return home / ".bugtracker" / "projects.json"


def get_indexed_projects() -> list[str]:
    """Get list of all indexed project paths.

    Returns:
        List of project paths that have bug trackers initialized.
    """
    index_path = get_project_index_path()
    if not index_path.exists():
        return []

    with open(index_path) as f:
        index = json.load(f)

    return index.get("projects", [])


def _register_project_in_index(project_path: str) -> None:
    """Register a project in the central index.

    Args:
        project_path: Absolute path to the project directory.
    """
    index_path = get_project_index_path()

    # Ensure directory exists
    index_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing index or create new
    if index_path.exists():
        with open(index_path) as f:
            index = json.load(f)
    else:
        index = {"projects": []}

    # Add project if not already in index
    if project_path not in index["projects"]:
        index["projects"].append(project_path)

    # Save index
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class RelatedBug:
    """Represents a relationship to another bug."""

    bug_id: str
    relationship: Literal["duplicate_of", "duplicated_by", "related_to", "blocks", "blocked_by"]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {"bug_id": self.bug_id, "relationship": self.relationship}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RelatedBug:
        """Deserialize from dictionary."""
        return cls(bug_id=data["bug_id"], relationship=data["relationship"])


@dataclass
class HistoryEntry:
    """Represents a change or note in bug history.

    Changes dict maps field names to (old_value, new_value) tuples.
    Can have a note without any field changes (progress updates).
    """

    timestamp: str  # ISO format
    changes: dict[str, tuple[str | None, str]]  # field -> (old, new)
    note: str | None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Converts tuples to lists for JSON compatibility.
        """
        return {
            "timestamp": self.timestamp,
            "changes": {k: list(v) for k, v in self.changes.items()},
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoryEntry:
        """Deserialize from dictionary.

        Converts lists back to tuples.
        """
        changes = {k: tuple(v) for k, v in data.get("changes", {}).items()}
        return cls(
            timestamp=data["timestamp"],
            changes=changes,
            note=data.get("note"),
        )


@dataclass
class Bug:
    """Represents a bug with full history tracking."""

    id: str
    title: str
    description: str | None
    status: Literal["open", "in_progress", "closed"]
    priority: Literal["low", "medium", "high", "critical"]
    tags: list[str]
    related_bugs: list[RelatedBug]
    created_at: str  # ISO format
    history: list[HistoryEntry]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "tags": self.tags,
            "related_bugs": [r.to_dict() for r in self.related_bugs],
            "created_at": self.created_at,
            "history": [h.to_dict() for h in self.history],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Bug:
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description"),
            status=data["status"],
            priority=data["priority"],
            tags=data.get("tags", []),
            related_bugs=[RelatedBug.from_dict(r) for r in data.get("related_bugs", [])],
            created_at=data["created_at"],
            history=[HistoryEntry.from_dict(h) for h in data.get("history", [])],
        )


# =============================================================================
# Storage Layer
# =============================================================================


class BugStore:
    """SQLite-based storage for bugs.

    Each project has its own database file in .bugtracker/bugs.db.
    Uses WAL mode for better concurrency.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize the store.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._conn.execute("PRAGMA journal_mode=WAL;")
        return self._conn

    def initialize(self) -> None:
        """Create the database schema if it doesn't exist."""
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bugs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                tags TEXT NOT NULL,
                related_bugs TEXT NOT NULL,
                created_at TEXT NOT NULL,
                history TEXT NOT NULL
            )
        """)
        # Create indexes for common queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bugs_status ON bugs(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bugs_priority ON bugs(priority)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bugs_created_at ON bugs(created_at)")
        conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def add_bug(self, bug: Bug) -> None:
        """Add a new bug to the store.

        Args:
            bug: The bug to add.
        """
        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO bugs (id, title, description, status, priority, tags,
                            related_bugs, created_at, history)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bug.id,
                bug.title,
                bug.description,
                bug.status,
                bug.priority,
                json.dumps(bug.tags),
                json.dumps([r.to_dict() for r in bug.related_bugs]),
                bug.created_at,
                json.dumps([h.to_dict() for h in bug.history]),
            ),
        )
        conn.commit()

    def get_bug(self, bug_id: str) -> Bug | None:
        """Retrieve a bug by ID.

        Args:
            bug_id: The bug ID to look up.

        Returns:
            The bug if found, None otherwise.
        """
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM bugs WHERE id = ?", (bug_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_bug(row)

    def update_bug(self, bug: Bug) -> None:
        """Update an existing bug.

        Args:
            bug: The bug with updated values.
        """
        conn = self._get_connection()
        conn.execute(
            """
            UPDATE bugs SET
                title = ?,
                description = ?,
                status = ?,
                priority = ?,
                tags = ?,
                related_bugs = ?,
                history = ?
            WHERE id = ?
            """,
            (
                bug.title,
                bug.description,
                bug.status,
                bug.priority,
                json.dumps(bug.tags),
                json.dumps([r.to_dict() for r in bug.related_bugs]),
                json.dumps([h.to_dict() for h in bug.history]),
                bug.id,
            ),
        )
        conn.commit()

    def list_bugs(
        self,
        status: str | None = None,
        priority: str | None = None,
        tags: list[str] | None = None,
    ) -> list[Bug]:
        """List bugs with optional filtering.

        Args:
            status: Filter by status (open, in_progress, closed).
            priority: Filter by priority (low, medium, high, critical).
            tags: Filter by tags (bug must have all specified tags).

        Returns:
            List of bugs matching the filters.
        """
        conn = self._get_connection()
        query = "SELECT * FROM bugs WHERE 1=1"
        params: list[Any] = []

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        if priority is not None:
            query += " AND priority = ?"
            params.append(priority)

        query += " ORDER BY created_at DESC"
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        bugs = [self._row_to_bug(row) for row in rows]

        # Filter by tags in Python (SQLite JSON support is limited)
        if tags:
            bugs = [b for b in bugs if all(tag in b.tags for tag in tags)]

        return bugs

    def _row_to_bug(self, row: sqlite3.Row) -> Bug:
        """Convert a database row to a Bug object."""
        return Bug(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            priority=row["priority"],
            tags=json.loads(row["tags"]),
            related_bugs=[RelatedBug.from_dict(r) for r in json.loads(row["related_bugs"])],
            created_at=row["created_at"],
            history=[HistoryEntry.from_dict(h) for h in json.loads(row["history"])],
        )


# =============================================================================
# Tool Schema Definitions (extracted for readability)
# =============================================================================

# Common schema fragments
_PROJECT_PATH_SCHEMA: dict[str, Any] = {
    "type": "string",
    "description": "Path to project directory (defaults to cwd).",
}

_STATUS_SCHEMA: dict[str, Any] = {
    "type": "string",
    "enum": ["open", "in_progress", "closed"],
    "description": "Filter by status.",
}

_PRIORITY_SCHEMA: dict[str, Any] = {
    "type": "string",
    "enum": ["low", "medium", "high", "critical"],
    "description": "Filter by priority.",
}

_TAGS_FILTER_SCHEMA: dict[str, Any] = {
    "type": "array",
    "items": {"type": "string"},
    "description": "Filter by tags (must have ALL specified tags).",
}

# Tool-specific schemas
_INIT_BUGTRACKER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "project_path": _PROJECT_PATH_SCHEMA,
    },
    "required": [],
}

_ADD_BUG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Brief title for the bug.",
        },
        "description": {
            "type": "string",
            "description": "Detailed description of the bug.",
        },
        "priority": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
            "description": "Bug priority (default: medium).",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tags for categorizing the bug.",
        },
        "project_path": _PROJECT_PATH_SCHEMA,
    },
    "required": ["title"],
}

_GET_BUG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "bug_id": {
            "type": "string",
            "description": "The bug ID to retrieve.",
        },
        "project_path": _PROJECT_PATH_SCHEMA,
    },
    "required": ["bug_id"],
}

_UPDATE_BUG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "bug_id": {
            "type": "string",
            "description": "The bug ID to update.",
        },
        "status": {
            "type": "string",
            "enum": ["open", "in_progress", "closed"],
            "description": "New status for the bug.",
        },
        "priority": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
            "description": "New priority for the bug.",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "New tags (replaces existing tags).",
        },
        "related_bugs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "bug_id": {"type": "string"},
                    "relationship": {
                        "type": "string",
                        "enum": [
                            "duplicate_of",
                            "duplicated_by",
                            "related_to",
                            "blocks",
                            "blocked_by",
                        ],
                    },
                },
                "required": ["bug_id", "relationship"],
            },
            "description": "Related bugs (replaces existing).",
        },
        "note": {
            "type": "string",
            "description": "Note for the history entry (progress update, reason for change).",
        },
        "project_path": _PROJECT_PATH_SCHEMA,
    },
    "required": ["bug_id"],
}

_CLOSE_BUG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "bug_id": {
            "type": "string",
            "description": "The bug ID to close.",
        },
        "resolution": {
            "type": "string",
            "description": "Resolution note explaining how the bug was fixed.",
        },
        "project_path": _PROJECT_PATH_SCHEMA,
    },
    "required": ["bug_id"],
}

_LIST_BUGS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": _STATUS_SCHEMA,
        "priority": _PRIORITY_SCHEMA,
        "tags": _TAGS_FILTER_SCHEMA,
        "project_path": _PROJECT_PATH_SCHEMA,
    },
    "required": [],
}

_SEARCH_BUGS_GLOBAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": _STATUS_SCHEMA,
        "priority": _PRIORITY_SCHEMA,
        "tags": _TAGS_FILTER_SCHEMA,
    },
    "required": [],
}

# Tool definitions list (used by get_tools())
_TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="init_bugtracker",
        description="Initialize bug tracker for a project. Creates .bugtracker/ directory.",
        input_schema=_INIT_BUGTRACKER_SCHEMA,
    ),
    ToolDefinition(
        name="add_bug",
        description="Add a new bug to the tracker.",
        input_schema=_ADD_BUG_SCHEMA,
    ),
    ToolDefinition(
        name="get_bug",
        description="Get a bug by ID.",
        input_schema=_GET_BUG_SCHEMA,
    ),
    ToolDefinition(
        name="update_bug",
        description=(
            "Update an existing bug. Can update status, priority, tags, related_bugs. "
            "Supports note-only updates for progress tracking."
        ),
        input_schema=_UPDATE_BUG_SCHEMA,
    ),
    ToolDefinition(
        name="close_bug",
        description="Close a bug (convenience wrapper for update_bug with status=closed).",
        input_schema=_CLOSE_BUG_SCHEMA,
    ),
    ToolDefinition(
        name="list_bugs",
        description="List bugs with optional filtering by status, priority, and tags.",
        input_schema=_LIST_BUGS_SCHEMA,
    ),
    ToolDefinition(
        name="search_bugs_global",
        description="Search bugs across all indexed projects.",
        input_schema=_SEARCH_BUGS_GLOBAL_SCHEMA,
    ),
]


class BugTrackerPlugin(PluginBase):
    """Bug tracker plugin.

    Provides tools for tracking bugs across projects with:
    - Per-project SQLite storage (.bugtracker/bugs.db)
    - Cross-project search via central index
    - Full history tracking for all changes

    Attributes:
        allowed_root: Optional root directory for path validation.
                      If None, uses current working directory.
                      Set to "/" or similar to allow any path (for testing).
    """

    # Path validation root - can be overridden for testing
    allowed_root: Path | None = None

    @property
    def name(self) -> str:
        """Return plugin identifier."""
        return "bugtracker"

    @property
    def version(self) -> str:
        """Return plugin version."""
        return "1.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        """Return available tools.

        Returns:
            List of tool definitions for bug tracking.
        """
        return _TOOL_DEFINITIONS

    def _validate_project_path(
        self, arguments: dict[str, Any]
    ) -> tuple[Path | None, ToolResult | None]:
        """Validate and resolve project path, preventing path traversal attacks.

        Args:
            arguments: Tool arguments containing optional project_path.

        Returns:
            Tuple of (resolved_path, None) on success, or (None, error_result) on failure.
        """
        import os

        project_path_str = arguments.get("project_path", os.getcwd())
        project_path = Path(project_path_str)

        # Resolve to absolute path
        try:
            resolved_path = project_path.resolve()
        except (OSError, ValueError) as e:
            return None, ToolResult(
                content=[{"type": "text", "text": f"Invalid path: {e}"}],
                is_error=True,
            )

        # Get allowed root (class attribute or current working directory)
        allowed_root = (
            self.allowed_root.resolve()
            if self.allowed_root is not None
            else Path(os.getcwd()).resolve()
        )

        # Check if resolved path is within allowed root
        try:
            resolved_path.relative_to(allowed_root)
        except ValueError:
            return None, ToolResult(
                content=[
                    {
                        "type": "text",
                        "text": (
                            f"Path traversal denied: {project_path_str} "
                            "is outside allowed directory"
                        ),
                    }
                ],
                is_error=True,
            )

        return resolved_path, None

    def _get_handler_registry(self) -> dict[str, Callable[[dict[str, Any]], ToolResult]]:
        """Return mapping of tool names to handler methods.

        Returns:
            Dict mapping tool names to their handler functions.
        """
        return {
            "init_bugtracker": self._init_bugtracker,
            "add_bug": self._add_bug,
            "get_bug": self._get_bug,
            "update_bug": self._update_bug,
            "close_bug": self._close_bug,
            "list_bugs": self._list_bugs,
            "search_bugs_global": self._search_bugs_global,
        }

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            ToolResult with result or error.
        """
        handlers = self._get_handler_registry()
        handler = handlers.get(tool_name)

        if handler is None:
            return ToolResult(
                content=[{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                is_error=True,
            )

        return handler(arguments)

    def _init_bugtracker(self, arguments: dict[str, Any]) -> ToolResult:
        """Initialize bug tracker for a project.

        Args:
            arguments: Tool arguments containing optional project_path.

        Returns:
            ToolResult indicating success or failure.
        """
        # Validate path (security check for path traversal)
        project_path, error = self._validate_project_path(arguments)
        if error:
            return error

        if project_path is None:
            return ToolResult(
                content=[{"type": "text", "text": "Internal error: path validation failed"}],
                is_error=True,
            )

        # Validate path exists
        if not project_path.exists():
            return ToolResult(
                content=[{"type": "text", "text": f"Project path does not exist: {project_path}"}],
                is_error=True,
            )

        if not project_path.is_dir():
            return ToolResult(
                content=[
                    {"type": "text", "text": f"Project path is not a directory: {project_path}"}
                ],
                is_error=True,
            )

        # Check if already initialized
        bugtracker_dir = project_path / ".bugtracker"
        if bugtracker_dir.exists():
            return ToolResult(
                content=[
                    {"type": "text", "text": f"Bug tracker already initialized at {project_path}"}
                ],
                is_error=True,
            )

        # Create .bugtracker directory
        bugtracker_dir.mkdir(parents=True)

        # Initialize database
        db_path = bugtracker_dir / "bugs.db"
        store = BugStore(db_path)
        store.initialize()
        store.close()

        # Register project in central index for cross-project search
        _register_project_in_index(str(project_path.resolve()))

        return ToolResult(
            content=[{"type": "text", "text": f"Bug tracker initialized at {project_path}"}],
            is_error=False,
        )

    def _get_store(self, arguments: dict[str, Any]) -> tuple[BugStore | None, ToolResult | None]:
        """Get a BugStore for the project, or return an error result.

        Args:
            arguments: Tool arguments containing optional project_path.

        Returns:
            Tuple of (store, None) on success, or (None, error_result) on failure.
        """
        # Validate path (security check for path traversal)
        project_path, error = self._validate_project_path(arguments)
        if error:
            return None, error

        if project_path is None:
            return None, ToolResult(
                content=[{"type": "text", "text": "Internal error: path validation failed"}],
                is_error=True,
            )

        bugtracker_dir = project_path / ".bugtracker"

        if not bugtracker_dir.exists():
            return None, ToolResult(
                content=[
                    {"type": "text", "text": f"Bug tracker not initialized at {project_path}"}
                ],
                is_error=True,
            )

        db_path = bugtracker_dir / "bugs.db"
        store = BugStore(db_path)
        return store, None

    def _add_bug(self, arguments: dict[str, Any]) -> ToolResult:
        """Add a new bug.

        Args:
            arguments: Tool arguments.

        Returns:
            ToolResult with bug ID or error.
        """
        import uuid
        from datetime import datetime

        # Validate title
        title = arguments.get("title", "").strip()
        if not title:
            return ToolResult(
                content=[{"type": "text", "text": "Title is required"}],
                is_error=True,
            )

        # Get store
        store, error = self._get_store(arguments)
        if error:
            return error

        if store is None:
            return ToolResult(
                content=[{"type": "text", "text": "Internal error: store initialization failed"}],
                is_error=True,
            )

        # Create bug
        bug_id = f"bug-{uuid.uuid4().hex[:8]}"
        bug = Bug(
            id=bug_id,
            title=title,
            description=arguments.get("description"),
            status="open",
            priority=arguments.get("priority", "medium"),
            tags=arguments.get("tags", []),
            related_bugs=[],
            created_at=datetime.now(UTC).isoformat(),
            history=[],
        )

        store.add_bug(bug)
        store.close()

        return ToolResult(
            content=[{"type": "text", "text": f"Created bug: {bug_id}"}],
            is_error=False,
        )

    def _get_bug(self, arguments: dict[str, Any]) -> ToolResult:
        """Get a bug by ID.

        Args:
            arguments: Tool arguments.

        Returns:
            ToolResult with bug data as JSON or error.
        """
        # Validate bug_id
        bug_id = arguments.get("bug_id", "").strip()
        if not bug_id:
            return ToolResult(
                content=[{"type": "text", "text": "bug_id is required"}],
                is_error=True,
            )

        # Get store
        store, error = self._get_store(arguments)
        if error:
            return error

        if store is None:
            return ToolResult(
                content=[{"type": "text", "text": "Internal error: store initialization failed"}],
                is_error=True,
            )

        # Get bug
        bug = store.get_bug(bug_id)
        store.close()

        if bug is None:
            return ToolResult(
                content=[{"type": "text", "text": f"Bug not found: {bug_id}"}],
                is_error=True,
            )

        return ToolResult(
            content=[{"type": "text", "text": json.dumps(bug.to_dict(), indent=2)}],
            is_error=False,
        )

    def _apply_field_updates(
        self,
        bug: Bug,
        arguments: dict[str, Any],
        changes: dict[str, tuple[str | None, str]],
    ) -> None:
        """Apply field updates to a bug and track changes.

        Handles status, priority, tags, and related_bugs fields.

        Args:
            bug: The bug to update (modified in place).
            arguments: Tool arguments containing field updates.
            changes: Dict to track changes (modified in place).
        """
        # Simple fields: status, priority
        for field in ("status", "priority"):
            if field in arguments:
                new_value = arguments[field]
                old_value = getattr(bug, field)
                if new_value != old_value:
                    changes[field] = (old_value, new_value)
                    setattr(bug, field, new_value)

        # Tags: list field with sorted comparison
        if "tags" in arguments:
            self._apply_tags_update(bug, arguments["tags"], changes)

        # Related bugs: complex field with JSON comparison
        if "related_bugs" in arguments:
            self._apply_related_bugs_update(bug, arguments["related_bugs"], changes)

    def _apply_tags_update(
        self,
        bug: Bug,
        new_tags: list[str],
        changes: dict[str, tuple[str | None, str]],
    ) -> None:
        """Update bug tags and track changes."""
        old_tags_str = ",".join(sorted(bug.tags)) if bug.tags else ""
        new_tags_str = ",".join(sorted(new_tags)) if new_tags else ""
        if old_tags_str != new_tags_str:
            changes["tags"] = (old_tags_str, new_tags_str)
        bug.tags = new_tags

    def _apply_related_bugs_update(
        self,
        bug: Bug,
        new_related_dicts: list[dict[str, Any]],
        changes: dict[str, tuple[str | None, str]],
    ) -> None:
        """Update related bugs and track changes."""
        new_related = [RelatedBug.from_dict(r) for r in new_related_dicts]
        old_related_str = json.dumps([r.to_dict() for r in bug.related_bugs], sort_keys=True)
        new_related_str = json.dumps([r.to_dict() for r in new_related], sort_keys=True)
        if old_related_str != new_related_str:
            changes["related_bugs"] = (old_related_str, new_related_str)
        bug.related_bugs = new_related

    def _update_bug(self, arguments: dict[str, Any]) -> ToolResult:
        """Update an existing bug.

        Supports updating status, priority, tags, related_bugs.
        Also supports note-only updates for progress tracking (no field changes).

        Args:
            arguments: Tool arguments.

        Returns:
            ToolResult indicating success or failure.
        """
        from datetime import datetime

        # Validate bug_id
        bug_id = arguments.get("bug_id", "").strip()
        if not bug_id:
            return ToolResult(
                content=[{"type": "text", "text": "bug_id is required"}],
                is_error=True,
            )

        # Get store
        store, error = self._get_store(arguments)
        if error:
            return error

        if store is None:
            return ToolResult(
                content=[{"type": "text", "text": "Internal error: store initialization failed"}],
                is_error=True,
            )

        # Get existing bug
        bug = store.get_bug(bug_id)
        if bug is None:
            store.close()
            return ToolResult(
                content=[{"type": "text", "text": f"Bug not found: {bug_id}"}],
                is_error=True,
            )

        # Track and apply field updates
        changes: dict[str, tuple[str | None, str]] = {}
        self._apply_field_updates(bug, arguments, changes)

        # Create history entry (even if no field changes - supports note-only updates)
        note = arguments.get("note")
        history_entry = HistoryEntry(
            timestamp=datetime.now(UTC).isoformat(),
            changes=changes,
            note=note,
        )
        bug.history.append(history_entry)

        # Save changes
        store.update_bug(bug)
        store.close()

        return ToolResult(
            content=[{"type": "text", "text": f"Updated bug: {bug_id}"}],
            is_error=False,
        )

    def _close_bug(self, arguments: dict[str, Any]) -> ToolResult:
        """Close a bug (convenience wrapper).

        Args:
            arguments: Tool arguments containing bug_id and optional resolution.

        Returns:
            ToolResult indicating success or failure.
        """
        # Validate bug_id
        bug_id = arguments.get("bug_id", "").strip()
        if not bug_id:
            return ToolResult(
                content=[{"type": "text", "text": "bug_id is required"}],
                is_error=True,
            )

        # Delegate to update_bug with status=closed
        update_args = {
            "bug_id": bug_id,
            "status": "closed",
        }

        # Pass through resolution as note
        if "resolution" in arguments:
            update_args["note"] = arguments["resolution"]

        # Pass through project_path if provided
        if "project_path" in arguments:
            update_args["project_path"] = arguments["project_path"]

        return self._update_bug(update_args)

    def _list_bugs(self, arguments: dict[str, Any]) -> ToolResult:
        """List bugs with optional filtering.

        Args:
            arguments: Tool arguments with optional status, priority, tags filters.

        Returns:
            ToolResult with JSON array of bugs.
        """
        # Get store
        store, error = self._get_store(arguments)
        if error:
            return error

        if store is None:
            return ToolResult(
                content=[{"type": "text", "text": "Internal error: store initialization failed"}],
                is_error=True,
            )

        # Get filtered bugs
        bugs = store.list_bugs(
            status=arguments.get("status"),
            priority=arguments.get("priority"),
            tags=arguments.get("tags"),
        )
        store.close()

        # Serialize to JSON
        bugs_data = [bug.to_dict() for bug in bugs]
        return ToolResult(
            content=[{"type": "text", "text": json.dumps(bugs_data, indent=2)}],
            is_error=False,
        )

    def _search_bugs_global(self, arguments: dict[str, Any]) -> ToolResult:
        """Search bugs across all indexed projects.

        Args:
            arguments: Tool arguments with optional status, priority, tags filters.

        Returns:
            ToolResult with JSON array of bugs from all projects.
        """
        all_bugs: list[dict[str, Any]] = []

        # Get all indexed projects
        project_paths = get_indexed_projects()

        for project_path in project_paths:
            # Check if project still has a valid bug tracker
            bugtracker_dir = Path(project_path) / ".bugtracker"
            if not bugtracker_dir.exists():
                continue

            db_path = bugtracker_dir / "bugs.db"
            store = BugStore(db_path)

            # Get filtered bugs from this project
            bugs = store.list_bugs(
                status=arguments.get("status"),
                priority=arguments.get("priority"),
                tags=arguments.get("tags"),
            )
            store.close()

            # Add project_path to each bug
            for bug in bugs:
                bug_data = bug.to_dict()
                bug_data["project_path"] = project_path
                all_bugs.append(bug_data)

        return ToolResult(
            content=[{"type": "text", "text": json.dumps(all_bugs, indent=2)}],
            is_error=False,
        )
