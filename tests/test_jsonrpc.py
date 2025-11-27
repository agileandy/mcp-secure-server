"""Tests for JSON-RPC 2.0 message parsing and formatting."""

import json

import pytest

from src.protocol.jsonrpc import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    JsonRpcError,
    JsonRpcNotification,
    JsonRpcRequest,
    format_error,
    format_notification,
    format_response,
    parse_message,
)


class TestJsonRpcRequest:
    """Tests for parsing JSON-RPC requests."""

    def test_parses_valid_request(self):
        """Should parse a valid request."""
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {"cursor": "abc"},
        }
        msg = parse_message(json.dumps(data))

        assert isinstance(msg, JsonRpcRequest)
        assert msg.id == 1
        assert msg.method == "tools/list"
        assert msg.params == {"cursor": "abc"}

    def test_parses_request_with_string_id(self):
        """Should accept string IDs."""
        data = {"jsonrpc": "2.0", "id": "req-123", "method": "test"}
        msg = parse_message(json.dumps(data))

        assert isinstance(msg, JsonRpcRequest)
        assert msg.id == "req-123"

    def test_parses_request_without_params(self):
        """Should parse request without params."""
        data = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        msg = parse_message(json.dumps(data))

        assert isinstance(msg, JsonRpcRequest)
        assert msg.params is None

    def test_rejects_missing_jsonrpc_version(self):
        """Should reject missing jsonrpc field."""
        data = {"id": 1, "method": "test"}
        with pytest.raises(JsonRpcError) as exc_info:
            parse_message(json.dumps(data))
        assert exc_info.value.code == INVALID_REQUEST

    def test_rejects_wrong_jsonrpc_version(self):
        """Should reject wrong jsonrpc version."""
        data = {"jsonrpc": "1.0", "id": 1, "method": "test"}
        with pytest.raises(JsonRpcError) as exc_info:
            parse_message(json.dumps(data))
        assert exc_info.value.code == INVALID_REQUEST

    def test_rejects_missing_method(self):
        """Should reject request without method."""
        data = {"jsonrpc": "2.0", "id": 1}
        with pytest.raises(JsonRpcError) as exc_info:
            parse_message(json.dumps(data))
        assert exc_info.value.code == INVALID_REQUEST


class TestJsonRpcNotification:
    """Tests for parsing JSON-RPC notifications."""

    def test_parses_notification(self):
        """Should parse notification (no id)."""
        data = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        msg = parse_message(json.dumps(data))

        assert isinstance(msg, JsonRpcNotification)
        assert msg.method == "notifications/initialized"

    def test_parses_notification_with_params(self):
        """Should parse notification with params."""
        data = {
            "jsonrpc": "2.0",
            "method": "notifications/progress",
            "params": {"progress": 50},
        }
        msg = parse_message(json.dumps(data))

        assert isinstance(msg, JsonRpcNotification)
        assert msg.params == {"progress": 50}


class TestParseErrors:
    """Tests for parse error handling."""

    def test_handles_invalid_json(self):
        """Should return parse error for invalid JSON."""
        with pytest.raises(JsonRpcError) as exc_info:
            parse_message("not valid json{")
        assert exc_info.value.code == PARSE_ERROR

    def test_handles_non_object_json(self):
        """Should reject non-object JSON."""
        with pytest.raises(JsonRpcError) as exc_info:
            parse_message('"just a string"')
        assert exc_info.value.code == INVALID_REQUEST

    def test_handles_array_json(self):
        """Should reject array (batch not supported)."""
        with pytest.raises(JsonRpcError) as exc_info:
            parse_message('[{"jsonrpc": "2.0", "id": 1, "method": "test"}]')
        assert exc_info.value.code == INVALID_REQUEST


class TestFormatResponse:
    """Tests for formatting JSON-RPC responses."""

    def test_formats_success_response(self):
        """Should format successful response."""
        response = format_response(1, {"tools": []})
        parsed = json.loads(response)

        assert parsed["jsonrpc"] == "2.0"
        assert parsed["id"] == 1
        assert parsed["result"] == {"tools": []}
        assert "error" not in parsed

    def test_formats_response_with_string_id(self):
        """Should preserve string IDs."""
        response = format_response("req-123", {"status": "ok"})
        parsed = json.loads(response)

        assert parsed["id"] == "req-123"

    def test_formats_null_result(self):
        """Should allow null result."""
        response = format_response(1, None)
        parsed = json.loads(response)

        assert parsed["result"] is None


class TestFormatError:
    """Tests for formatting JSON-RPC errors."""

    def test_formats_error_with_id(self):
        """Should format error with request ID."""
        error = format_error(1, METHOD_NOT_FOUND, "Method not found")
        parsed = json.loads(error)

        assert parsed["jsonrpc"] == "2.0"
        assert parsed["id"] == 1
        assert parsed["error"]["code"] == METHOD_NOT_FOUND
        assert parsed["error"]["message"] == "Method not found"
        assert "result" not in parsed

    def test_formats_error_without_id(self):
        """Should format error without ID (for parse errors)."""
        error = format_error(None, PARSE_ERROR, "Parse error")
        parsed = json.loads(error)

        assert parsed["id"] is None
        assert parsed["error"]["code"] == PARSE_ERROR

    def test_formats_error_with_data(self):
        """Should include error data if provided."""
        error = format_error(1, INVALID_PARAMS, "Invalid params", {"missing": "field"})
        parsed = json.loads(error)

        assert parsed["error"]["data"] == {"missing": "field"}


class TestFormatNotification:
    """Tests for formatting JSON-RPC notifications."""

    def test_formats_notification(self):
        """Should format notification."""
        notification = format_notification("notifications/tools/list_changed")
        parsed = json.loads(notification)

        assert parsed["jsonrpc"] == "2.0"
        assert parsed["method"] == "notifications/tools/list_changed"
        assert "id" not in parsed

    def test_formats_notification_with_params(self):
        """Should format notification with params."""
        notification = format_notification("notifications/progress", {"value": 75})
        parsed = json.loads(notification)

        assert parsed["params"] == {"value": 75}


class TestJsonRpcErrorClass:
    """Tests for JsonRpcError exception class."""

    def test_error_has_code_and_message(self):
        """Should store code and message."""
        error = JsonRpcError(INTERNAL_ERROR, "Something went wrong")

        assert error.code == INTERNAL_ERROR
        assert error.message == "Something went wrong"
        assert str(error) == "Something went wrong"

    def test_error_has_optional_data(self):
        """Should store optional data."""
        error = JsonRpcError(INVALID_PARAMS, "Bad params", {"field": "name"})

        assert error.data == {"field": "name"}


class TestMessageSizeLimit:
    """Tests for message size limits [D8]."""

    def test_rejects_oversized_message(self):
        """Should reject messages larger than 1MB."""
        # Create a message just over 1MB
        large_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "test",
            "params": {"data": "x" * (1024 * 1024 + 100)},
        }
        large_message = json.dumps(large_data)

        with pytest.raises(JsonRpcError) as exc_info:
            parse_message(large_message)

        assert exc_info.value.code == PARSE_ERROR
        assert "too large" in exc_info.value.message.lower()

    def test_accepts_message_under_limit(self):
        """Should accept messages under 1MB."""
        # Create a message just under 1MB
        data = {"jsonrpc": "2.0", "id": 1, "method": "test", "params": {"data": "x" * 100000}}
        message = json.dumps(data)

        # Should not raise
        result = parse_message(message)
        assert isinstance(result, JsonRpcRequest)
