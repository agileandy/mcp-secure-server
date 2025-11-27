"""Tests for bug tracker plugin."""

import json

from src.plugins.base import PluginBase


class TestBugTrackerPluginInterface:
    """Tests for BugTrackerPlugin implementing PluginBase."""

    def test_implements_plugin_interface(self):
        """Should implement PluginBase interface."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        assert isinstance(plugin, PluginBase)

    def test_has_correct_name(self):
        """Should have correct plugin name."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        assert plugin.name == "bugtracker"

    def test_has_version(self):
        """Should have a version string."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        assert plugin.version == "1.0.0"

    def test_provides_tools(self):
        """Should provide bug tracking tools."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        tools = plugin.get_tools()

        assert len(tools) >= 1
        tool_names = [t.name for t in tools]
        assert "init_bugtracker" in tool_names

    def test_handles_unknown_tool(self):
        """Should return error for unknown tool."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        result = plugin.execute("unknown_tool", {})

        assert result.is_error is True
        assert "Unknown tool" in result.content[0]["text"]


class TestBugDataModels:
    """Tests for Bug, HistoryEntry, and RelatedBug data models."""

    def test_related_bug_creation(self):
        """Should create RelatedBug with required fields."""
        from src.plugins.bugtracker import RelatedBug

        related = RelatedBug(bug_id="bug-123", relationship="duplicate_of")
        assert related.bug_id == "bug-123"
        assert related.relationship == "duplicate_of"

    def test_related_bug_to_dict(self):
        """Should serialize RelatedBug to dictionary."""
        from src.plugins.bugtracker import RelatedBug

        related = RelatedBug(bug_id="bug-123", relationship="blocks")
        data = related.to_dict()

        assert data == {"bug_id": "bug-123", "relationship": "blocks"}

    def test_related_bug_from_dict(self):
        """Should deserialize RelatedBug from dictionary."""
        from src.plugins.bugtracker import RelatedBug

        data = {"bug_id": "bug-456", "relationship": "related_to"}
        related = RelatedBug.from_dict(data)

        assert related.bug_id == "bug-456"
        assert related.relationship == "related_to"

    def test_history_entry_with_changes(self):
        """Should create HistoryEntry with field changes."""
        from src.plugins.bugtracker import HistoryEntry

        entry = HistoryEntry(
            timestamp="2025-11-27T10:00:00Z",
            changes={"status": ("open", "in_progress")},
            note="Starting work",
        )
        assert entry.timestamp == "2025-11-27T10:00:00Z"
        assert entry.changes == {"status": ("open", "in_progress")}
        assert entry.note == "Starting work"

    def test_history_entry_note_only(self):
        """Should create HistoryEntry with note but no field changes."""
        from src.plugins.bugtracker import HistoryEntry

        entry = HistoryEntry(
            timestamp="2025-11-27T11:00:00Z",
            changes={},
            note="Tried approach X, didn't work. Trying Y now.",
        )
        assert entry.changes == {}
        assert entry.note == "Tried approach X, didn't work. Trying Y now."

    def test_history_entry_to_dict(self):
        """Should serialize HistoryEntry to dictionary."""
        from src.plugins.bugtracker import HistoryEntry

        entry = HistoryEntry(
            timestamp="2025-11-27T10:00:00Z",
            changes={"priority": ("low", "high")},
            note="Escalating",
        )
        data = entry.to_dict()

        assert data["timestamp"] == "2025-11-27T10:00:00Z"
        assert data["changes"] == {"priority": ["low", "high"]}
        assert data["note"] == "Escalating"

    def test_history_entry_from_dict(self):
        """Should deserialize HistoryEntry from dictionary."""
        from src.plugins.bugtracker import HistoryEntry

        data = {
            "timestamp": "2025-11-27T10:00:00Z",
            "changes": {"status": ["open", "closed"]},
            "note": "Fixed",
        }
        entry = HistoryEntry.from_dict(data)

        assert entry.timestamp == "2025-11-27T10:00:00Z"
        assert entry.changes == {"status": ("open", "closed")}
        assert entry.note == "Fixed"

    def test_bug_creation_minimal(self):
        """Should create Bug with minimal required fields."""
        from src.plugins.bugtracker import Bug

        bug = Bug(
            id="bug-001",
            title="Test bug",
            description=None,
            status="open",
            priority="medium",
            tags=[],
            related_bugs=[],
            created_at="2025-11-27T10:00:00Z",
            history=[],
        )
        assert bug.id == "bug-001"
        assert bug.title == "Test bug"
        assert bug.status == "open"

    def test_bug_creation_full(self):
        """Should create Bug with all fields populated."""
        from src.plugins.bugtracker import Bug, HistoryEntry, RelatedBug

        bug = Bug(
            id="bug-002",
            title="Complex bug",
            description="Detailed description",
            status="in_progress",
            priority="critical",
            tags=["backend", "urgent"],
            related_bugs=[RelatedBug("bug-001", "blocks")],
            created_at="2025-11-27T10:00:00Z",
            history=[
                HistoryEntry(
                    timestamp="2025-11-27T11:00:00Z",
                    changes={"status": ("open", "in_progress")},
                    note="Starting investigation",
                )
            ],
        )
        assert bug.priority == "critical"
        assert len(bug.tags) == 2
        assert len(bug.related_bugs) == 1
        assert len(bug.history) == 1

    def test_bug_to_dict(self):
        """Should serialize Bug to dictionary."""
        from src.plugins.bugtracker import Bug, HistoryEntry, RelatedBug

        bug = Bug(
            id="bug-003",
            title="Serialization test",
            description="Test desc",
            status="open",
            priority="low",
            tags=["test"],
            related_bugs=[RelatedBug("bug-001", "related_to")],
            created_at="2025-11-27T10:00:00Z",
            history=[
                HistoryEntry(
                    timestamp="2025-11-27T10:00:00Z",
                    changes={},
                    note="Created",
                )
            ],
        )
        data = bug.to_dict()

        assert data["id"] == "bug-003"
        assert data["title"] == "Serialization test"
        assert data["tags"] == ["test"]
        assert len(data["related_bugs"]) == 1
        assert data["related_bugs"][0]["relationship"] == "related_to"

    def test_bug_from_dict(self):
        """Should deserialize Bug from dictionary."""
        from src.plugins.bugtracker import Bug

        data = {
            "id": "bug-004",
            "title": "Deserialization test",
            "description": None,
            "status": "closed",
            "priority": "high",
            "tags": ["frontend"],
            "related_bugs": [{"bug_id": "bug-002", "relationship": "duplicate_of"}],
            "created_at": "2025-11-27T10:00:00Z",
            "history": [
                {
                    "timestamp": "2025-11-27T12:00:00Z",
                    "changes": {"status": ["open", "closed"]},
                    "note": "Resolved",
                }
            ],
        }
        bug = Bug.from_dict(data)

        assert bug.id == "bug-004"
        assert bug.status == "closed"
        assert len(bug.related_bugs) == 1
        assert bug.related_bugs[0].relationship == "duplicate_of"
        assert len(bug.history) == 1

    def test_bug_json_roundtrip(self):
        """Should survive JSON serialization roundtrip."""
        from src.plugins.bugtracker import Bug, HistoryEntry, RelatedBug

        original = Bug(
            id="bug-005",
            title="Roundtrip test",
            description="Testing JSON roundtrip",
            status="in_progress",
            priority="medium",
            tags=["test", "json"],
            related_bugs=[RelatedBug("bug-001", "blocks")],
            created_at="2025-11-27T10:00:00Z",
            history=[
                HistoryEntry(
                    timestamp="2025-11-27T11:00:00Z",
                    changes={"status": ("open", "in_progress")},
                    note="Started",
                )
            ],
        )

        json_str = json.dumps(original.to_dict())
        restored = Bug.from_dict(json.loads(json_str))

        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.tags == original.tags
        assert restored.related_bugs[0].bug_id == original.related_bugs[0].bug_id
        assert restored.history[0].note == original.history[0].note


class TestBugStore:
    """Tests for BugStore SQLite storage layer."""

    def test_create_store(self, tmp_path):
        """Should create a new BugStore instance."""
        from src.plugins.bugtracker import BugStore

        db_path = tmp_path / "bugs.db"
        store = BugStore(db_path)
        assert store is not None
        store.close()

    def test_initialize_creates_tables(self, tmp_path):
        """Should create bugs table on initialization."""
        from src.plugins.bugtracker import BugStore

        db_path = tmp_path / "bugs.db"
        store = BugStore(db_path)
        store.initialize()

        # Verify table exists by attempting a query
        bugs = store.list_bugs()
        assert bugs == []
        store.close()

    def test_add_bug(self, tmp_path):
        """Should add a bug to the store."""
        from src.plugins.bugtracker import Bug, BugStore

        db_path = tmp_path / "bugs.db"
        store = BugStore(db_path)
        store.initialize()

        bug = Bug(
            id="bug-001",
            title="Test bug",
            description="A test",
            status="open",
            priority="medium",
            tags=["test"],
            related_bugs=[],
            created_at="2025-11-27T10:00:00Z",
            history=[],
        )
        store.add_bug(bug)

        retrieved = store.get_bug("bug-001")
        assert retrieved is not None
        assert retrieved.title == "Test bug"
        store.close()

    def test_get_bug_not_found(self, tmp_path):
        """Should return None for non-existent bug."""
        from src.plugins.bugtracker import BugStore

        db_path = tmp_path / "bugs.db"
        store = BugStore(db_path)
        store.initialize()

        result = store.get_bug("non-existent")
        assert result is None
        store.close()

    def test_update_bug(self, tmp_path):
        """Should update an existing bug."""
        from src.plugins.bugtracker import Bug, BugStore, HistoryEntry

        db_path = tmp_path / "bugs.db"
        store = BugStore(db_path)
        store.initialize()

        bug = Bug(
            id="bug-001",
            title="Original title",
            description=None,
            status="open",
            priority="low",
            tags=[],
            related_bugs=[],
            created_at="2025-11-27T10:00:00Z",
            history=[],
        )
        store.add_bug(bug)

        # Update the bug
        bug.title = "Updated title"
        bug.status = "in_progress"
        bug.history.append(
            HistoryEntry(
                timestamp="2025-11-27T11:00:00Z",
                changes={
                    "status": ("open", "in_progress"),
                    "title": ("Original title", "Updated title"),
                },
                note="Updated",
            )
        )
        store.update_bug(bug)

        retrieved = store.get_bug("bug-001")
        assert retrieved.title == "Updated title"
        assert retrieved.status == "in_progress"
        assert len(retrieved.history) == 1
        store.close()

    def test_list_bugs_empty(self, tmp_path):
        """Should return empty list when no bugs."""
        from src.plugins.bugtracker import BugStore

        db_path = tmp_path / "bugs.db"
        store = BugStore(db_path)
        store.initialize()

        bugs = store.list_bugs()
        assert bugs == []
        store.close()

    def test_list_bugs_all(self, tmp_path):
        """Should return all bugs when no filter."""
        from src.plugins.bugtracker import Bug, BugStore

        db_path = tmp_path / "bugs.db"
        store = BugStore(db_path)
        store.initialize()

        for i in range(3):
            store.add_bug(
                Bug(
                    id=f"bug-{i:03d}",
                    title=f"Bug {i}",
                    description=None,
                    status="open",
                    priority="medium",
                    tags=[],
                    related_bugs=[],
                    created_at="2025-11-27T10:00:00Z",
                    history=[],
                )
            )

        bugs = store.list_bugs()
        assert len(bugs) == 3
        store.close()

    def test_list_bugs_filter_status(self, tmp_path):
        """Should filter bugs by status."""
        from src.plugins.bugtracker import Bug, BugStore

        db_path = tmp_path / "bugs.db"
        store = BugStore(db_path)
        store.initialize()

        store.add_bug(
            Bug(
                id="bug-001",
                title="Open bug",
                description=None,
                status="open",
                priority="low",
                tags=[],
                related_bugs=[],
                created_at="2025-11-27T10:00:00Z",
                history=[],
            )
        )
        store.add_bug(
            Bug(
                id="bug-002",
                title="Closed bug",
                description=None,
                status="closed",
                priority="low",
                tags=[],
                related_bugs=[],
                created_at="2025-11-27T10:00:00Z",
                history=[],
            )
        )

        open_bugs = store.list_bugs(status="open")
        assert len(open_bugs) == 1
        assert open_bugs[0].id == "bug-001"
        store.close()

    def test_list_bugs_filter_priority(self, tmp_path):
        """Should filter bugs by priority."""
        from src.plugins.bugtracker import Bug, BugStore

        db_path = tmp_path / "bugs.db"
        store = BugStore(db_path)
        store.initialize()

        store.add_bug(
            Bug(
                id="bug-001",
                title="Low bug",
                description=None,
                status="open",
                priority="low",
                tags=[],
                related_bugs=[],
                created_at="2025-11-27T10:00:00Z",
                history=[],
            )
        )
        store.add_bug(
            Bug(
                id="bug-002",
                title="Critical bug",
                description=None,
                status="open",
                priority="critical",
                tags=[],
                related_bugs=[],
                created_at="2025-11-27T10:00:00Z",
                history=[],
            )
        )

        critical_bugs = store.list_bugs(priority="critical")
        assert len(critical_bugs) == 1
        assert critical_bugs[0].id == "bug-002"
        store.close()

    def test_list_bugs_filter_tags(self, tmp_path):
        """Should filter bugs by tags."""
        from src.plugins.bugtracker import Bug, BugStore

        db_path = tmp_path / "bugs.db"
        store = BugStore(db_path)
        store.initialize()

        store.add_bug(
            Bug(
                id="bug-001",
                title="Backend bug",
                description=None,
                status="open",
                priority="low",
                tags=["backend"],
                related_bugs=[],
                created_at="2025-11-27T10:00:00Z",
                history=[],
            )
        )
        store.add_bug(
            Bug(
                id="bug-002",
                title="Frontend bug",
                description=None,
                status="open",
                priority="low",
                tags=["frontend", "ui"],
                related_bugs=[],
                created_at="2025-11-27T10:00:00Z",
                history=[],
            )
        )

        backend_bugs = store.list_bugs(tags=["backend"])
        assert len(backend_bugs) == 1
        assert backend_bugs[0].id == "bug-001"
        store.close()

    def test_bug_with_related_bugs_roundtrip(self, tmp_path):
        """Should store and retrieve bugs with related bugs."""
        from src.plugins.bugtracker import Bug, BugStore, RelatedBug

        db_path = tmp_path / "bugs.db"
        store = BugStore(db_path)
        store.initialize()

        bug = Bug(
            id="bug-001",
            title="Primary bug",
            description=None,
            status="open",
            priority="high",
            tags=[],
            related_bugs=[
                RelatedBug("bug-002", "blocks"),
                RelatedBug("bug-003", "related_to"),
            ],
            created_at="2025-11-27T10:00:00Z",
            history=[],
        )
        store.add_bug(bug)

        retrieved = store.get_bug("bug-001")
        assert len(retrieved.related_bugs) == 2
        assert retrieved.related_bugs[0].bug_id == "bug-002"
        assert retrieved.related_bugs[0].relationship == "blocks"
        store.close()

    def test_uses_wal_mode(self, tmp_path):
        """Should use WAL mode for better concurrency."""
        import sqlite3

        from src.plugins.bugtracker import BugStore

        db_path = tmp_path / "bugs.db"
        store = BugStore(db_path)
        store.initialize()
        store.close()

        # Check WAL mode was set
        conn = sqlite3.connect(db_path)
        result = conn.execute("PRAGMA journal_mode;").fetchone()
        conn.close()
        assert result[0].lower() == "wal"


class TestInitBugtrackerTool:
    """Tests for init_bugtracker tool."""

    def test_init_creates_directory(self, tmp_path):
        """Should create .bugtracker directory."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        result = plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        assert result.is_error is False
        assert (tmp_path / ".bugtracker").exists()
        assert (tmp_path / ".bugtracker").is_dir()

    def test_init_creates_database(self, tmp_path):
        """Should create bugs.db in .bugtracker directory."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        assert (tmp_path / ".bugtracker" / "bugs.db").exists()

    def test_init_rejects_reinit(self, tmp_path):
        """Should reject re-initialization of already initialized project."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()

        # First init should succeed
        result1 = plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})
        assert result1.is_error is False

        # Second init should fail
        result2 = plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})
        assert result2.is_error is True
        assert "already initialized" in result2.content[0]["text"].lower()

    def test_init_returns_success_message(self, tmp_path):
        """Should return success message with path."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        result = plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        assert result.is_error is False
        assert "initialized" in result.content[0]["text"].lower()
        assert str(tmp_path) in result.content[0]["text"]

    def test_init_handles_invalid_path(self, tmp_path):
        """Should handle invalid project path gracefully."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        result = plugin.execute("init_bugtracker", {"project_path": str(tmp_path / "nonexistent")})

        assert result.is_error is True
        assert "not exist" in result.content[0]["text"].lower()

    def test_init_uses_cwd_when_no_path(self, tmp_path, monkeypatch):
        """Should use current working directory when no path provided."""

        from src.plugins.bugtracker import BugTrackerPlugin

        # Change to tmp_path
        monkeypatch.chdir(tmp_path)

        plugin = BugTrackerPlugin()
        result = plugin.execute("init_bugtracker", {})

        assert result.is_error is False
        assert (tmp_path / ".bugtracker").exists()


class TestAddBugTool:
    """Tests for add_bug tool."""

    def test_add_bug_minimal(self, tmp_path):
        """Should add bug with just title."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        result = plugin.execute(
            "add_bug",
            {"title": "Test bug", "project_path": str(tmp_path)},
        )

        assert result.is_error is False
        # Should return the bug ID
        assert "bug-" in result.content[0]["text"].lower()

    def test_add_bug_with_all_fields(self, tmp_path):
        """Should add bug with all optional fields."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        result = plugin.execute(
            "add_bug",
            {
                "title": "Complex bug",
                "description": "Detailed description",
                "priority": "critical",
                "tags": ["backend", "urgent"],
                "project_path": str(tmp_path),
            },
        )

        assert result.is_error is False

    def test_add_bug_generates_uuid(self, tmp_path):
        """Should generate unique bug IDs."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        result1 = plugin.execute("add_bug", {"title": "Bug 1", "project_path": str(tmp_path)})
        result2 = plugin.execute("add_bug", {"title": "Bug 2", "project_path": str(tmp_path)})

        # Extract bug IDs from results
        text1 = result1.content[0]["text"]
        text2 = result2.content[0]["text"]

        # IDs should be different
        assert text1 != text2

    def test_add_bug_defaults_to_open(self, tmp_path):
        """Should default status to 'open'."""
        from src.plugins.bugtracker import BugStore, BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        plugin.execute("add_bug", {"title": "New bug", "project_path": str(tmp_path)})

        # Verify in database
        store = BugStore(tmp_path / ".bugtracker" / "bugs.db")
        bugs = store.list_bugs()
        assert len(bugs) == 1
        assert bugs[0].status == "open"
        store.close()

    def test_add_bug_defaults_to_medium_priority(self, tmp_path):
        """Should default priority to 'medium'."""
        from src.plugins.bugtracker import BugStore, BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        plugin.execute("add_bug", {"title": "New bug", "project_path": str(tmp_path)})

        store = BugStore(tmp_path / ".bugtracker" / "bugs.db")
        bugs = store.list_bugs()
        assert bugs[0].priority == "medium"
        store.close()

    def test_add_bug_requires_init(self, tmp_path):
        """Should fail if bugtracker not initialized."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        result = plugin.execute("add_bug", {"title": "Bug", "project_path": str(tmp_path)})

        assert result.is_error is True
        assert "not initialized" in result.content[0]["text"].lower()

    def test_add_bug_requires_title(self, tmp_path):
        """Should fail if title not provided."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        result = plugin.execute("add_bug", {"project_path": str(tmp_path)})

        assert result.is_error is True
        assert "title" in result.content[0]["text"].lower()

    def test_add_bug_records_created_at(self, tmp_path):
        """Should record creation timestamp."""
        from src.plugins.bugtracker import BugStore, BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        plugin.execute("add_bug", {"title": "New bug", "project_path": str(tmp_path)})

        store = BugStore(tmp_path / ".bugtracker" / "bugs.db")
        bugs = store.list_bugs()
        assert bugs[0].created_at is not None
        assert "2025" in bugs[0].created_at  # Basic sanity check
        store.close()


class TestGetBugTool:
    """Tests for get_bug tool."""

    def test_get_bug_returns_bug(self, tmp_path):
        """Should retrieve bug by ID."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        # Add a bug
        add_result = plugin.execute(
            "add_bug",
            {"title": "Test bug", "description": "Test desc", "project_path": str(tmp_path)},
        )
        bug_id = add_result.content[0]["text"].split(": ")[1]

        # Get the bug
        result = plugin.execute("get_bug", {"bug_id": bug_id, "project_path": str(tmp_path)})

        assert result.is_error is False
        bug_data = json.loads(result.content[0]["text"])
        assert bug_data["id"] == bug_id
        assert bug_data["title"] == "Test bug"

    def test_get_bug_not_found(self, tmp_path):
        """Should return error for non-existent bug."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        result = plugin.execute("get_bug", {"bug_id": "nonexistent", "project_path": str(tmp_path)})

        assert result.is_error is True
        assert "not found" in result.content[0]["text"].lower()

    def test_get_bug_requires_init(self, tmp_path):
        """Should fail if bugtracker not initialized."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        result = plugin.execute("get_bug", {"bug_id": "bug-123", "project_path": str(tmp_path)})

        assert result.is_error is True
        assert "not initialized" in result.content[0]["text"].lower()

    def test_get_bug_requires_bug_id(self, tmp_path):
        """Should fail if bug_id not provided."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        result = plugin.execute("get_bug", {"project_path": str(tmp_path)})

        assert result.is_error is True
        assert "bug_id" in result.content[0]["text"].lower()


class TestUpdateBugTool:
    """Tests for update_bug tool."""

    def test_update_bug_status(self, tmp_path):
        """Should update bug status and record in history."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        # Add a bug
        add_result = plugin.execute("add_bug", {"title": "Test bug", "project_path": str(tmp_path)})
        bug_id = add_result.content[0]["text"].split(": ")[1]

        # Update status
        result = plugin.execute(
            "update_bug",
            {
                "bug_id": bug_id,
                "status": "in_progress",
                "note": "Starting work",
                "project_path": str(tmp_path),
            },
        )

        assert result.is_error is False

        # Verify history
        get_result = plugin.execute("get_bug", {"bug_id": bug_id, "project_path": str(tmp_path)})
        bug_data = json.loads(get_result.content[0]["text"])
        assert bug_data["status"] == "in_progress"
        assert len(bug_data["history"]) == 1
        assert bug_data["history"][0]["changes"]["status"] == ["open", "in_progress"]

    def test_update_bug_note_only(self, tmp_path):
        """Should allow note-only updates without field changes."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        add_result = plugin.execute(
            "add_bug", {"title": "Complex bug", "project_path": str(tmp_path)}
        )
        bug_id = add_result.content[0]["text"].split(": ")[1]

        # First update: change status
        plugin.execute(
            "update_bug",
            {
                "bug_id": bug_id,
                "status": "in_progress",
                "note": "Starting investigation",
                "project_path": str(tmp_path),
            },
        )

        # Second update: note only (tried something, didn't work)
        result = plugin.execute(
            "update_bug",
            {
                "bug_id": bug_id,
                "note": "Tried approach X, didn't work. Trying Y now.",
                "project_path": str(tmp_path),
            },
        )

        assert result.is_error is False

        get_result = plugin.execute("get_bug", {"bug_id": bug_id, "project_path": str(tmp_path)})
        bug_data = json.loads(get_result.content[0]["text"])

        # Should have 2 history entries
        assert len(bug_data["history"]) == 2
        # Second entry should have empty changes but a note
        assert bug_data["history"][1]["changes"] == {}
        assert "Tried approach X" in bug_data["history"][1]["note"]

    def test_update_bug_priority(self, tmp_path):
        """Should update priority."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        add_result = plugin.execute("add_bug", {"title": "Bug", "project_path": str(tmp_path)})
        bug_id = add_result.content[0]["text"].split(": ")[1]

        plugin.execute(
            "update_bug",
            {
                "bug_id": bug_id,
                "priority": "critical",
                "note": "Escalating",
                "project_path": str(tmp_path),
            },
        )

        get_result = plugin.execute("get_bug", {"bug_id": bug_id, "project_path": str(tmp_path)})
        bug_data = json.loads(get_result.content[0]["text"])
        assert bug_data["priority"] == "critical"

    def test_update_bug_tags(self, tmp_path):
        """Should update tags."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        add_result = plugin.execute("add_bug", {"title": "Bug", "project_path": str(tmp_path)})
        bug_id = add_result.content[0]["text"].split(": ")[1]

        plugin.execute(
            "update_bug",
            {
                "bug_id": bug_id,
                "tags": ["backend", "urgent"],
                "project_path": str(tmp_path),
            },
        )

        get_result = plugin.execute("get_bug", {"bug_id": bug_id, "project_path": str(tmp_path)})
        bug_data = json.loads(get_result.content[0]["text"])
        assert bug_data["tags"] == ["backend", "urgent"]

    def test_update_bug_related_bugs(self, tmp_path):
        """Should update related_bugs."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        # Create two bugs
        add1 = plugin.execute("add_bug", {"title": "Bug 1", "project_path": str(tmp_path)})
        bug1_id = add1.content[0]["text"].split(": ")[1]
        add2 = plugin.execute("add_bug", {"title": "Bug 2", "project_path": str(tmp_path)})
        bug2_id = add2.content[0]["text"].split(": ")[1]

        # Mark bug2 as duplicate of bug1
        plugin.execute(
            "update_bug",
            {
                "bug_id": bug2_id,
                "related_bugs": [{"bug_id": bug1_id, "relationship": "duplicate_of"}],
                "note": "This is a duplicate",
                "project_path": str(tmp_path),
            },
        )

        get_result = plugin.execute("get_bug", {"bug_id": bug2_id, "project_path": str(tmp_path)})
        bug_data = json.loads(get_result.content[0]["text"])
        assert len(bug_data["related_bugs"]) == 1
        assert bug_data["related_bugs"][0]["bug_id"] == bug1_id
        assert bug_data["related_bugs"][0]["relationship"] == "duplicate_of"

    def test_update_bug_reopen(self, tmp_path):
        """Should allow reopening a closed bug."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        add_result = plugin.execute("add_bug", {"title": "Bug", "project_path": str(tmp_path)})
        bug_id = add_result.content[0]["text"].split(": ")[1]

        # Close the bug
        plugin.execute(
            "update_bug",
            {"bug_id": bug_id, "status": "closed", "note": "Fixed", "project_path": str(tmp_path)},
        )

        # Reopen the bug
        plugin.execute(
            "update_bug",
            {
                "bug_id": bug_id,
                "status": "open",
                "note": "Reopening - fix didn't work",
                "project_path": str(tmp_path),
            },
        )

        get_result = plugin.execute("get_bug", {"bug_id": bug_id, "project_path": str(tmp_path)})
        bug_data = json.loads(get_result.content[0]["text"])
        assert bug_data["status"] == "open"
        assert len(bug_data["history"]) == 2

    def test_update_bug_not_found(self, tmp_path):
        """Should return error for non-existent bug."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        result = plugin.execute(
            "update_bug",
            {"bug_id": "nonexistent", "status": "closed", "project_path": str(tmp_path)},
        )

        assert result.is_error is True
        assert "not found" in result.content[0]["text"].lower()

    def test_update_bug_requires_bug_id(self, tmp_path):
        """Should fail if bug_id not provided."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        result = plugin.execute("update_bug", {"status": "closed", "project_path": str(tmp_path)})

        assert result.is_error is True
        assert "bug_id" in result.content[0]["text"].lower()


class TestCloseBugTool:
    """Tests for close_bug tool (convenience wrapper)."""

    def test_close_bug_sets_status_to_closed(self, tmp_path):
        """Should set bug status to closed."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        add_result = plugin.execute(
            "add_bug", {"title": "Bug to close", "project_path": str(tmp_path)}
        )
        bug_id = add_result.content[0]["text"].split(": ")[1]

        result = plugin.execute(
            "close_bug",
            {"bug_id": bug_id, "resolution": "Fixed the issue", "project_path": str(tmp_path)},
        )

        assert result.is_error is False

        get_result = plugin.execute("get_bug", {"bug_id": bug_id, "project_path": str(tmp_path)})
        bug_data = json.loads(get_result.content[0]["text"])
        assert bug_data["status"] == "closed"

    def test_close_bug_records_resolution_in_history(self, tmp_path):
        """Should record resolution note in history."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        add_result = plugin.execute("add_bug", {"title": "Bug", "project_path": str(tmp_path)})
        bug_id = add_result.content[0]["text"].split(": ")[1]

        plugin.execute(
            "close_bug",
            {
                "bug_id": bug_id,
                "resolution": "Deployed hotfix v2.1.3",
                "project_path": str(tmp_path),
            },
        )

        get_result = plugin.execute("get_bug", {"bug_id": bug_id, "project_path": str(tmp_path)})
        bug_data = json.loads(get_result.content[0]["text"])

        assert len(bug_data["history"]) == 1
        assert "hotfix v2.1.3" in bug_data["history"][0]["note"]

    def test_close_bug_requires_bug_id(self, tmp_path):
        """Should fail if bug_id not provided."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        result = plugin.execute("close_bug", {"resolution": "Fixed", "project_path": str(tmp_path)})

        assert result.is_error is True
        assert "bug_id" in result.content[0]["text"].lower()

    def test_close_bug_not_found(self, tmp_path):
        """Should return error for non-existent bug."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        result = plugin.execute(
            "close_bug",
            {"bug_id": "nonexistent", "resolution": "Fixed", "project_path": str(tmp_path)},
        )

        assert result.is_error is True
        assert "not found" in result.content[0]["text"].lower()


class TestListBugsTool:
    """Tests for list_bugs tool."""

    def test_list_bugs_returns_all(self, tmp_path):
        """Should return all bugs when no filters provided."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        # Add 3 bugs
        plugin.execute("add_bug", {"title": "Bug 1", "project_path": str(tmp_path)})
        plugin.execute("add_bug", {"title": "Bug 2", "project_path": str(tmp_path)})
        plugin.execute("add_bug", {"title": "Bug 3", "project_path": str(tmp_path)})

        result = plugin.execute("list_bugs", {"project_path": str(tmp_path)})

        assert result.is_error is False
        bugs = json.loads(result.content[0]["text"])
        assert len(bugs) == 3

    def test_list_bugs_filter_by_status(self, tmp_path):
        """Should filter bugs by status."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        # Add bugs with different statuses
        add1 = plugin.execute("add_bug", {"title": "Open bug", "project_path": str(tmp_path)})
        bug1_id = add1.content[0]["text"].split(": ")[1]

        add2 = plugin.execute(
            "add_bug", {"title": "In progress bug", "project_path": str(tmp_path)}
        )
        bug2_id = add2.content[0]["text"].split(": ")[1]
        plugin.execute(
            "update_bug",
            {"bug_id": bug2_id, "status": "in_progress", "project_path": str(tmp_path)},
        )

        add3 = plugin.execute("add_bug", {"title": "Closed bug", "project_path": str(tmp_path)})
        bug3_id = add3.content[0]["text"].split(": ")[1]
        plugin.execute("close_bug", {"bug_id": bug3_id, "project_path": str(tmp_path)})

        # Filter by status=open
        result = plugin.execute("list_bugs", {"status": "open", "project_path": str(tmp_path)})
        bugs = json.loads(result.content[0]["text"])
        assert len(bugs) == 1
        assert bugs[0]["id"] == bug1_id

    def test_list_bugs_filter_by_priority(self, tmp_path):
        """Should filter bugs by priority."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        plugin.execute(
            "add_bug", {"title": "Low", "priority": "low", "project_path": str(tmp_path)}
        )
        plugin.execute(
            "add_bug", {"title": "Critical", "priority": "critical", "project_path": str(tmp_path)}
        )
        plugin.execute("add_bug", {"title": "Medium", "project_path": str(tmp_path)})  # default

        result = plugin.execute(
            "list_bugs", {"priority": "critical", "project_path": str(tmp_path)}
        )
        bugs = json.loads(result.content[0]["text"])
        assert len(bugs) == 1
        assert bugs[0]["title"] == "Critical"

    def test_list_bugs_filter_by_tags(self, tmp_path):
        """Should filter bugs by tags (must have all specified tags)."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        plugin.execute(
            "add_bug",
            {"title": "Backend only", "tags": ["backend"], "project_path": str(tmp_path)},
        )
        plugin.execute(
            "add_bug",
            {"title": "Frontend only", "tags": ["frontend"], "project_path": str(tmp_path)},
        )
        plugin.execute(
            "add_bug",
            {"title": "Both", "tags": ["backend", "frontend"], "project_path": str(tmp_path)},
        )

        # Filter by single tag
        result = plugin.execute("list_bugs", {"tags": ["backend"], "project_path": str(tmp_path)})
        bugs = json.loads(result.content[0]["text"])
        assert len(bugs) == 2

        # Filter by multiple tags (must have ALL)
        result = plugin.execute(
            "list_bugs", {"tags": ["backend", "frontend"], "project_path": str(tmp_path)}
        )
        bugs = json.loads(result.content[0]["text"])
        assert len(bugs) == 1
        assert bugs[0]["title"] == "Both"

    def test_list_bugs_empty_result(self, tmp_path):
        """Should return empty list when no bugs match."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        result = plugin.execute("list_bugs", {"project_path": str(tmp_path)})
        bugs = json.loads(result.content[0]["text"])
        assert bugs == []

    def test_list_bugs_combined_filters(self, tmp_path):
        """Should support combining status and priority filters."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(tmp_path)})

        plugin.execute(
            "add_bug", {"title": "A", "priority": "critical", "project_path": str(tmp_path)}
        )
        add2 = plugin.execute(
            "add_bug", {"title": "B", "priority": "critical", "project_path": str(tmp_path)}
        )
        bug2_id = add2.content[0]["text"].split(": ")[1]
        plugin.execute("close_bug", {"bug_id": bug2_id, "project_path": str(tmp_path)})
        plugin.execute("add_bug", {"title": "C", "priority": "low", "project_path": str(tmp_path)})

        # Critical AND open
        result = plugin.execute(
            "list_bugs",
            {"status": "open", "priority": "critical", "project_path": str(tmp_path)},
        )
        bugs = json.loads(result.content[0]["text"])
        assert len(bugs) == 1
        assert bugs[0]["title"] == "A"


class TestProjectIndex:
    """Tests for project index (cross-project search support)."""

    def test_init_registers_project_in_index(self, tmp_path, monkeypatch):
        """Should register project in central index on init."""
        from src.plugins.bugtracker import BugTrackerPlugin, get_project_index_path

        # Use a temp directory as home for the central index
        monkeypatch.setenv("HOME", str(tmp_path))

        project_path = tmp_path / "my_project"
        project_path.mkdir()

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(project_path)})

        # Verify project is in index
        index_path = get_project_index_path()
        assert index_path.exists()

        import json

        with open(index_path) as f:
            index = json.load(f)

        assert str(project_path) in index["projects"]

    def test_multiple_projects_in_index(self, tmp_path, monkeypatch):
        """Should track multiple projects in index."""
        from src.plugins.bugtracker import BugTrackerPlugin, get_project_index_path

        monkeypatch.setenv("HOME", str(tmp_path))

        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"
        project1.mkdir()
        project2.mkdir()

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(project1)})
        plugin.execute("init_bugtracker", {"project_path": str(project2)})

        import json

        with open(get_project_index_path()) as f:
            index = json.load(f)

        assert str(project1) in index["projects"]
        assert str(project2) in index["projects"]
        assert len(index["projects"]) == 2

    def test_get_indexed_projects(self, tmp_path, monkeypatch):
        """Should return list of indexed projects."""
        from src.plugins.bugtracker import BugTrackerPlugin, get_indexed_projects

        monkeypatch.setenv("HOME", str(tmp_path))

        project = tmp_path / "project"
        project.mkdir()

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(project)})

        projects = get_indexed_projects()
        assert str(project) in projects


class TestSearchBugsGlobal:
    """Tests for search_bugs_global tool."""

    def test_search_across_projects(self, tmp_path, monkeypatch):
        """Should search bugs across all indexed projects."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        monkeypatch.setenv("HOME", str(tmp_path))

        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"
        project1.mkdir()
        project2.mkdir()

        plugin = BugTrackerPlugin()

        # Init both projects
        plugin.execute("init_bugtracker", {"project_path": str(project1)})
        plugin.execute("init_bugtracker", {"project_path": str(project2)})

        # Add bugs to each project
        plugin.execute(
            "add_bug",
            {"title": "Auth bug", "tags": ["auth"], "project_path": str(project1)},
        )
        plugin.execute(
            "add_bug",
            {"title": "UI bug", "tags": ["frontend"], "project_path": str(project1)},
        )
        plugin.execute(
            "add_bug",
            {"title": "API auth issue", "tags": ["auth"], "project_path": str(project2)},
        )

        # Search for auth bugs across all projects
        result = plugin.execute("search_bugs_global", {"tags": ["auth"]})

        assert result.is_error is False
        bugs = json.loads(result.content[0]["text"])
        assert len(bugs) == 2

        # Each result should have project_path
        for bug in bugs:
            assert "project_path" in bug

    def test_search_with_status_filter(self, tmp_path, monkeypatch):
        """Should filter by status across projects."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        monkeypatch.setenv("HOME", str(tmp_path))

        project = tmp_path / "project"
        project.mkdir()

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(project)})

        add1 = plugin.execute("add_bug", {"title": "Open bug", "project_path": str(project)})
        _bug1_id = add1.content[0]["text"].split(": ")[1]  # noqa: F841 - ID extracted to verify add works

        plugin.execute("add_bug", {"title": "Another open", "project_path": str(project)})

        add3 = plugin.execute("add_bug", {"title": "Closed bug", "project_path": str(project)})
        bug3_id = add3.content[0]["text"].split(": ")[1]
        plugin.execute("close_bug", {"bug_id": bug3_id, "project_path": str(project)})

        result = plugin.execute("search_bugs_global", {"status": "open"})
        bugs = json.loads(result.content[0]["text"])
        assert len(bugs) == 2

    def test_search_empty_result(self, tmp_path, monkeypatch):
        """Should return empty list when no bugs match."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        monkeypatch.setenv("HOME", str(tmp_path))

        project = tmp_path / "project"
        project.mkdir()

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(project)})

        result = plugin.execute("search_bugs_global", {"status": "closed"})
        bugs = json.loads(result.content[0]["text"])
        assert bugs == []

    def test_search_no_indexed_projects(self, tmp_path, monkeypatch):
        """Should return empty list when no projects indexed."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        monkeypatch.setenv("HOME", str(tmp_path))

        plugin = BugTrackerPlugin()
        result = plugin.execute("search_bugs_global", {})

        assert result.is_error is False
        bugs = json.loads(result.content[0]["text"])
        assert bugs == []


class TestBugTrackerIntegration:
    """End-to-end integration tests for bug tracker workflow."""

    def test_full_bug_lifecycle(self, tmp_path, monkeypatch):
        """Test complete bug lifecycle: create -> work -> close -> reopen."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        monkeypatch.setenv("HOME", str(tmp_path))
        project = tmp_path / "project"
        project.mkdir()

        plugin = BugTrackerPlugin()

        # 1. Initialize bug tracker
        result = plugin.execute("init_bugtracker", {"project_path": str(project)})
        assert result.is_error is False
        assert (project / ".bugtracker" / "bugs.db").exists()

        # 2. Create a bug
        result = plugin.execute(
            "add_bug",
            {
                "title": "Authentication fails for OAuth users",
                "description": "Users logging in via OAuth get 401 errors",
                "priority": "high",
                "tags": ["auth", "oauth", "backend"],
                "project_path": str(project),
            },
        )
        assert result.is_error is False
        bug_id = result.content[0]["text"].split(": ")[1]

        # 3. Verify bug was created correctly
        result = plugin.execute("get_bug", {"bug_id": bug_id, "project_path": str(project)})
        bug = json.loads(result.content[0]["text"])
        assert bug["title"] == "Authentication fails for OAuth users"
        assert bug["status"] == "open"
        assert bug["priority"] == "high"
        assert "oauth" in bug["tags"]

        # 4. Start working on the bug
        result = plugin.execute(
            "update_bug",
            {
                "bug_id": bug_id,
                "status": "in_progress",
                "note": "Investigating token refresh logic",
                "project_path": str(project),
            },
        )
        assert result.is_error is False

        # 5. Add progress note (no field changes)
        result = plugin.execute(
            "update_bug",
            {
                "bug_id": bug_id,
                "note": "Found issue: token expiry check uses wrong timezone",
                "project_path": str(project),
            },
        )
        assert result.is_error is False

        # 6. Close the bug
        result = plugin.execute(
            "close_bug",
            {
                "bug_id": bug_id,
                "resolution": "Fixed timezone handling in token validation",
                "project_path": str(project),
            },
        )
        assert result.is_error is False

        # 7. Verify full history
        result = plugin.execute("get_bug", {"bug_id": bug_id, "project_path": str(project)})
        bug = json.loads(result.content[0]["text"])
        assert bug["status"] == "closed"
        assert len(bug["history"]) == 3

        # History entries: start work, progress note, close
        assert bug["history"][0]["changes"]["status"] == ["open", "in_progress"]
        assert "Investigating" in bug["history"][0]["note"]
        assert bug["history"][1]["changes"] == {}  # note-only update
        assert "timezone" in bug["history"][1]["note"]
        assert bug["history"][2]["changes"]["status"] == ["in_progress", "closed"]

        # 8. Reopen the bug (regression found)
        result = plugin.execute(
            "update_bug",
            {
                "bug_id": bug_id,
                "status": "open",
                "note": "Regression: issue reappeared after DST change",
                "project_path": str(project),
            },
        )
        assert result.is_error is False

        result = plugin.execute("get_bug", {"bug_id": bug_id, "project_path": str(project)})
        bug = json.loads(result.content[0]["text"])
        assert bug["status"] == "open"
        assert len(bug["history"]) == 4

    def test_multi_project_workflow(self, tmp_path, monkeypatch):
        """Test working with bugs across multiple projects."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        monkeypatch.setenv("HOME", str(tmp_path))

        # Create two projects
        backend = tmp_path / "backend"
        frontend = tmp_path / "frontend"
        backend.mkdir()
        frontend.mkdir()

        plugin = BugTrackerPlugin()

        # Initialize both
        plugin.execute("init_bugtracker", {"project_path": str(backend)})
        plugin.execute("init_bugtracker", {"project_path": str(frontend)})

        # Add bugs to each
        plugin.execute(
            "add_bug",
            {"title": "API rate limiting", "tags": ["api"], "project_path": str(backend)},
        )
        plugin.execute(
            "add_bug",
            {"title": "Button alignment", "tags": ["ui"], "project_path": str(frontend)},
        )
        plugin.execute(
            "add_bug",
            {"title": "Auth token refresh", "tags": ["auth"], "project_path": str(backend)},
        )
        plugin.execute(
            "add_bug",
            {"title": "Login form", "tags": ["auth"], "project_path": str(frontend)},
        )

        # List bugs in backend only
        result = plugin.execute("list_bugs", {"project_path": str(backend)})
        bugs = json.loads(result.content[0]["text"])
        assert len(bugs) == 2

        # List bugs in frontend only
        result = plugin.execute("list_bugs", {"project_path": str(frontend)})
        bugs = json.loads(result.content[0]["text"])
        assert len(bugs) == 2

        # Search auth bugs globally
        result = plugin.execute("search_bugs_global", {"tags": ["auth"]})
        bugs = json.loads(result.content[0]["text"])
        assert len(bugs) == 2
        project_paths = {bug["project_path"] for bug in bugs}
        assert str(backend) in project_paths
        assert str(frontend) in project_paths

    def test_related_bugs_workflow(self, tmp_path):
        """Test creating and linking related bugs."""
        import json

        from src.plugins.bugtracker import BugTrackerPlugin

        project = tmp_path / "project"
        project.mkdir()

        plugin = BugTrackerPlugin()
        plugin.execute("init_bugtracker", {"project_path": str(project)})

        # Create original bug
        result = plugin.execute(
            "add_bug",
            {"title": "Login page crashes", "project_path": str(project)},
        )
        original_id = result.content[0]["text"].split(": ")[1]

        # Create duplicate
        result = plugin.execute(
            "add_bug",
            {"title": "App crashes on login", "project_path": str(project)},
        )
        duplicate_id = result.content[0]["text"].split(": ")[1]

        # Link as duplicate
        plugin.execute(
            "update_bug",
            {
                "bug_id": duplicate_id,
                "related_bugs": [{"bug_id": original_id, "relationship": "duplicate_of"}],
                "note": "Duplicate of original login crash bug",
                "project_path": str(project),
            },
        )

        # Close duplicate
        plugin.execute(
            "close_bug",
            {"bug_id": duplicate_id, "resolution": "Duplicate", "project_path": str(project)},
        )

        # Verify
        result = plugin.execute("get_bug", {"bug_id": duplicate_id, "project_path": str(project)})
        bug = json.loads(result.content[0]["text"])
        assert bug["status"] == "closed"
        assert len(bug["related_bugs"]) == 1
        assert bug["related_bugs"][0]["bug_id"] == original_id
        assert bug["related_bugs"][0]["relationship"] == "duplicate_of"


class TestGetStoreNoneGuard:
    """Tests for handling edge case where _get_store returns (None, None).

    This tests defensive programming against an "impossible" state that could
    occur if _get_store is modified incorrectly. The assert statements that
    previously guarded this are stripped in optimized Python (-O flag).
    """

    def test_add_bug_handles_store_none(self, tmp_path, monkeypatch):
        """Should return error if _get_store returns (None, None)."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()

        # Mock _get_store to return the "impossible" state
        def mock_get_store(arguments):
            return None, None

        monkeypatch.setattr(plugin, "_get_store", mock_get_store)

        result = plugin.execute("add_bug", {"title": "Test", "project_path": str(tmp_path)})

        assert result.is_error is True
        assert "internal error" in result.content[0]["text"].lower()

    def test_get_bug_handles_store_none(self, tmp_path, monkeypatch):
        """Should return error if _get_store returns (None, None)."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()

        def mock_get_store(arguments):
            return None, None

        monkeypatch.setattr(plugin, "_get_store", mock_get_store)

        result = plugin.execute("get_bug", {"bug_id": "bug-123", "project_path": str(tmp_path)})

        assert result.is_error is True
        assert "internal error" in result.content[0]["text"].lower()

    def test_update_bug_handles_store_none(self, tmp_path, monkeypatch):
        """Should return error if _get_store returns (None, None)."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()

        def mock_get_store(arguments):
            return None, None

        monkeypatch.setattr(plugin, "_get_store", mock_get_store)

        result = plugin.execute(
            "update_bug",
            {"bug_id": "bug-123", "status": "in_progress", "project_path": str(tmp_path)},
        )

        assert result.is_error is True
        assert "internal error" in result.content[0]["text"].lower()

    def test_list_bugs_handles_store_none(self, tmp_path, monkeypatch):
        """Should return error if _get_store returns (None, None)."""
        from src.plugins.bugtracker import BugTrackerPlugin

        plugin = BugTrackerPlugin()

        def mock_get_store(arguments):
            return None, None

        monkeypatch.setattr(plugin, "_get_store", mock_get_store)

        result = plugin.execute("list_bugs", {"project_path": str(tmp_path)})

        assert result.is_error is True
        assert "internal error" in result.content[0]["text"].lower()


class TestPathTraversalProtection:
    """Tests for path traversal attack prevention.

    Ensures that malicious project_path values cannot escape the
    allowed directory (current working directory by default).
    """

    def test_init_rejects_path_traversal_attempt(self, tmp_path, monkeypatch):
        """Should reject project_path with path traversal attempt."""
        from src.plugins.bugtracker import BugTrackerPlugin

        # Set cwd to a temp directory
        monkeypatch.chdir(tmp_path)
        (tmp_path / "allowed").mkdir()

        plugin = BugTrackerPlugin()

        # Try to escape with ../
        result = plugin.execute(
            "init_bugtracker",
            {"project_path": "../../../etc"},
        )

        assert result.is_error is True
        assert "path" in result.content[0]["text"].lower()

    def test_init_rejects_absolute_path_outside_cwd(self, tmp_path, monkeypatch):
        """Should reject absolute paths outside current working directory."""
        from src.plugins.bugtracker import BugTrackerPlugin

        # Set cwd to a subdirectory
        workdir = tmp_path / "workdir"
        workdir.mkdir()
        monkeypatch.chdir(workdir)

        plugin = BugTrackerPlugin()

        # Try to access parent directory with absolute path
        result = plugin.execute(
            "init_bugtracker",
            {"project_path": str(tmp_path)},
        )

        assert result.is_error is True
        assert "path" in result.content[0]["text"].lower()

    def test_add_bug_rejects_path_traversal(self, tmp_path, monkeypatch):
        """Should reject path traversal in add_bug."""
        from src.plugins.bugtracker import BugTrackerPlugin

        monkeypatch.chdir(tmp_path)
        plugin = BugTrackerPlugin()

        result = plugin.execute(
            "add_bug",
            {"title": "Test", "project_path": "../../../etc"},
        )

        assert result.is_error is True
        assert "path" in result.content[0]["text"].lower()

    def test_init_allows_subdirectory(self, tmp_path, monkeypatch):
        """Should allow paths within the current working directory."""
        from src.plugins.bugtracker import BugTrackerPlugin

        monkeypatch.chdir(tmp_path)
        subdir = tmp_path / "projects" / "myproject"
        subdir.mkdir(parents=True)

        plugin = BugTrackerPlugin()

        result = plugin.execute(
            "init_bugtracker",
            {"project_path": str(subdir)},
        )

        assert result.is_error is False
        assert (subdir / ".bugtracker").exists()

    def test_init_allows_relative_subdirectory(self, tmp_path, monkeypatch):
        """Should allow relative paths to subdirectories."""
        from src.plugins.bugtracker import BugTrackerPlugin

        monkeypatch.chdir(tmp_path)
        subdir = tmp_path / "projects"
        subdir.mkdir()

        plugin = BugTrackerPlugin()

        result = plugin.execute(
            "init_bugtracker",
            {"project_path": "projects"},
        )

        assert result.is_error is False
        assert (subdir / ".bugtracker").exists()
