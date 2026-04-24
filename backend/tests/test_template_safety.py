"""Tests for the TemplateSafetyService — scanning and review workflow."""

import json

import pytest

from app.services.template_safety_service import template_safety_service


class TestScanTemplate:
    """Tests for the scan_template method (no DB required)."""

    def test_safe_template(self):
        template = json.dumps({
            "name": "Hub-Spoke Network",
            "resources": [
                {"type": "Microsoft.Network/virtualNetworks", "name": "hub-vnet"}
            ],
        })
        result = template_safety_service.scan_template(template)
        assert result["safe"] is True
        assert result["findings"] == []

    def test_empty_template(self):
        result = template_safety_service.scan_template(None)
        assert result["safe"] is True

    def test_empty_string_template(self):
        result = template_safety_service.scan_template("")
        assert result["safe"] is True

    def test_detects_script_tag(self):
        template = json.dumps({"description": '<script>alert("xss")</script>'})
        result = template_safety_service.scan_template(template)
        assert result["safe"] is False
        msgs = [f["message"] for f in result["findings"]]
        assert any("script" in m.lower() for m in msgs)

    def test_detects_javascript_uri(self):
        template = json.dumps({"link": "javascript: void(0)"})
        result = template_safety_service.scan_template(template)
        assert result["safe"] is False

    def test_detects_inline_event_handler(self):
        template = json.dumps({"attr": 'onclick=alert(1)'})
        result = template_safety_service.scan_template(template)
        assert result["safe"] is False

    def test_detects_eval_call(self):
        template = json.dumps({"code": "eval('malicious')"})
        result = template_safety_service.scan_template(template)
        assert result["safe"] is False

    def test_detects_function_constructor(self):
        template = json.dumps({"code": 'new Function("return this")'})
        result = template_safety_service.scan_template(template)
        assert result["safe"] is False

    def test_detects_wildcard_permission(self):
        template = json.dumps({"permissions": ["*"]})
        result = template_safety_service.scan_template(template)
        assert result["safe"] is False

    def test_detects_owner_role(self):
        template = json.dumps({"role": "Owner"})
        result = template_safety_service.scan_template(template)
        assert result["safe"] is False

    def test_multiple_findings(self):
        template = json.dumps({
            "x": "<script>bad</script>",
            "y": "eval(z)",
        })
        result = template_safety_service.scan_template(template)
        assert result["safe"] is False
        assert len(result["findings"]) >= 2

    def test_finding_has_match_count(self):
        template = json.dumps({
            "a": "<script>1</script>",
            "b": "<script>2</script>",
        })
        result = template_safety_service.scan_template(template)
        assert result["safe"] is False
        script_finding = next(
            f for f in result["findings"] if "script" in f["message"].lower()
        )
        assert script_finding["match_count"] >= 2

    def test_accepts_dict_input(self):
        """scan_template should handle a dict by serialising it."""
        result = template_safety_service.scan_template(
            {"name": "Safe Template", "resources": []}
        )
        assert result["safe"] is True
