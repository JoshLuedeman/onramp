"""Tests for workload importer service."""

import json

import pytest

from app.services.workload_importer import (
    detect_format,
    parse_csv,
    parse_json,
)

PROJECT_ID = "proj-test-001"


# ---------------------------------------------------------------------------
# detect_format
# ---------------------------------------------------------------------------

def test_detect_format_json_extension():
    assert detect_format("workloads.json", b"[]") == "json"


def test_detect_format_csv_extension():
    assert detect_format("workloads.csv", b"name,type\n") == "csv"


def test_detect_format_sniff_json_array():
    assert detect_format("upload", b'[{"name": "web1"}]') == "json"


def test_detect_format_sniff_json_object():
    assert detect_format("upload", b'{"workloads": []}') == "json"


def test_detect_format_sniff_csv_fallback():
    assert detect_format("data.txt", b"name,type,cpu\n") == "csv"


# ---------------------------------------------------------------------------
# parse_csv — happy path
# ---------------------------------------------------------------------------

def test_parse_csv_basic():
    csv_content = b"name,type,cpu_cores,memory_gb\nweb01,vm,4,16\n"
    result = parse_csv(csv_content, PROJECT_ID)
    assert len(result) == 1
    wl = result[0]
    assert wl.name == "web01"
    assert wl.type == "vm"
    assert wl.cpu_cores == 4
    assert wl.memory_gb == 16.0
    assert wl.project_id == PROJECT_ID


def test_parse_csv_column_aliases():
    """cpus/ram/disk/vm_name aliases map to canonical fields."""
    csv_content = b"vm_name,cpus,ram_gb,disk_gb\ndb01,8,32.5,500\n"
    result = parse_csv(csv_content, PROJECT_ID)
    assert len(result) == 1
    wl = result[0]
    assert wl.name == "db01"
    assert wl.cpu_cores == 8
    assert wl.memory_gb == 32.5
    assert wl.storage_gb == 500.0


def test_parse_csv_type_normalisation():
    csv_content = b"name,type\napp1,web-app\n"
    result = parse_csv(csv_content, PROJECT_ID)
    assert result[0].type == "web-app"


def test_parse_csv_unknown_type_defaults_to_other():
    csv_content = b"name,type\napp1,mainframe\n"
    result = parse_csv(csv_content, PROJECT_ID)
    assert result[0].type == "other"


def test_parse_csv_compliance_semicolon():
    csv_content = b"name,compliance_requirements\napp1,SOC2;ISO27001\n"
    result = parse_csv(csv_content, PROJECT_ID)
    assert result[0].compliance_requirements == ["SOC2", "ISO27001"]


def test_parse_csv_compliance_comma():
    csv_content = b"name,compliance\napp1,SOC2,ISO27001\n"
    # NOTE: CSV comma-separated inside a field requires quoting
    csv_content = b'name,compliance\napp1,"SOC2,ISO27001"\n'
    result = parse_csv(csv_content, PROJECT_ID)
    assert result[0].compliance_requirements == ["SOC2", "ISO27001"]


def test_parse_csv_multiple_rows():
    csv_content = b"name,type\nvm1,vm\nvm2,container\n"
    result = parse_csv(csv_content, PROJECT_ID)
    assert len(result) == 2
    assert result[1].type == "container"


def test_parse_csv_bom_prefix():
    """UTF-8 BOM should be stripped correctly."""
    # Prepend BOM bytes directly so utf-8-sig decoding removes them
    csv_content = b"\xef\xbb\xbfname,type\nweb01,vm\n"
    result = parse_csv(csv_content, PROJECT_ID)
    assert result[0].name == "web01"


def test_parse_csv_empty_optional_fields():
    csv_content = b"name,cpu_cores,memory_gb,storage_gb\nweb01,,,\n"
    result = parse_csv(csv_content, PROJECT_ID)
    wl = result[0]
    assert wl.cpu_cores is None
    assert wl.memory_gb is None
    assert wl.storage_gb is None


def test_parse_csv_criticality_alias():
    csv_content = b"name,priority\napp1,mission-critical\n"
    result = parse_csv(csv_content, PROJECT_ID)
    assert result[0].criticality == "mission-critical"


# ---------------------------------------------------------------------------
# parse_csv — error cases
# ---------------------------------------------------------------------------

def test_parse_csv_missing_name_raises():
    csv_content = b"type,cpu_cores\nvm,4\n"
    with pytest.raises(ValueError, match="name"):
        parse_csv(csv_content, PROJECT_ID)


def test_parse_csv_no_headers_raises():
    with pytest.raises(ValueError, match="no headers"):
        parse_csv(b"", PROJECT_ID)


# ---------------------------------------------------------------------------
# parse_json — happy path
# ---------------------------------------------------------------------------

def test_parse_json_array():
    data = [{"name": "svc1", "type": "vm", "cpu_cores": 2}]
    result = parse_json(json.dumps(data).encode(), PROJECT_ID)
    assert len(result) == 1
    assert result[0].name == "svc1"
    assert result[0].cpu_cores == 2


def test_parse_json_wrapped_in_workloads_key():
    data = {"workloads": [{"name": "svc2", "type": "container"}]}
    result = parse_json(json.dumps(data).encode(), PROJECT_ID)
    assert len(result) == 1
    assert result[0].type == "container"


def test_parse_json_single_object():
    data = {"name": "single-vm", "type": "vm"}
    result = parse_json(json.dumps(data).encode(), PROJECT_ID)
    assert len(result) == 1
    assert result[0].name == "single-vm"


def test_parse_json_compliance_list():
    data = [{"name": "app", "compliance_requirements": ["SOC2", "PCI-DSS"]}]
    result = parse_json(json.dumps(data).encode(), PROJECT_ID)
    assert result[0].compliance_requirements == ["SOC2", "PCI-DSS"]


def test_parse_json_source_platform_normalisation():
    data = [{"name": "vm1", "source_platform": "vmware"}]
    result = parse_json(json.dumps(data).encode(), PROJECT_ID)
    assert result[0].source_platform == "vmware"


def test_parse_json_unknown_platform_defaults():
    data = [{"name": "vm1", "source_platform": "hyper-v-pro"}]
    result = parse_json(json.dumps(data).encode(), PROJECT_ID)
    assert result[0].source_platform == "other"


def test_parse_json_column_aliases():
    """JSON keys should also be normalised via aliases."""
    data = [{"workload_name": "svc3", "cpus": 4, "ram": 8}]
    result = parse_json(json.dumps(data).encode(), PROJECT_ID)
    assert result[0].name == "svc3"
    assert result[0].cpu_cores == 4
    assert result[0].memory_gb == 8.0


# ---------------------------------------------------------------------------
# parse_json — error cases
# ---------------------------------------------------------------------------

def test_parse_json_invalid_json_raises():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_json(b"not-json", PROJECT_ID)


def test_parse_json_non_array_non_dict_raises():
    with pytest.raises(ValueError, match="array"):
        parse_json(b'"just a string"', PROJECT_ID)


def test_parse_json_missing_name_raises():
    data = [{"type": "vm"}]
    with pytest.raises(ValueError, match="name"):
        parse_json(json.dumps(data).encode(), PROJECT_ID)


def test_parse_json_item_not_dict_raises():
    data = [1, 2, 3]
    with pytest.raises(ValueError):
        parse_json(json.dumps(data).encode(), PROJECT_ID)
