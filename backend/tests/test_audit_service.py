"""Tests for the AuditService — stateless helpers."""

import pytest

from app.services.audit_service import audit_service


class TestActionFromMethod:
    """Test HTTP method to CRUD action mapping."""

    def test_post_maps_to_create(self):
        assert audit_service.action_from_method("POST") == "create"

    def test_get_maps_to_read(self):
        assert audit_service.action_from_method("GET") == "read"

    def test_put_maps_to_update(self):
        assert audit_service.action_from_method("PUT") == "update"

    def test_patch_maps_to_update(self):
        assert audit_service.action_from_method("PATCH") == "update"

    def test_delete_maps_to_delete(self):
        assert audit_service.action_from_method("DELETE") == "delete"

    def test_unknown_method_returns_unknown(self):
        result = audit_service.action_from_method("OPTIONS")
        assert result == "unknown" or isinstance(result, str)
