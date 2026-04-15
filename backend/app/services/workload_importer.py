"""Workload importer service — parse CSV and JSON files into WorkloadCreate objects."""

import csv
import io
import json
import logging

from app.schemas.workload import WorkloadCreate

logger = logging.getLogger(__name__)

# Column name aliases: maps common variants to canonical field names
_COLUMN_ALIASES: dict[str, str] = {
    # name
    "workload_name": "name",
    "vm_name": "name",
    "server_name": "name",
    "hostname": "name",
    # type
    "workload_type": "type",
    "resource_type": "type",
    # source_platform
    "platform": "source_platform",
    "source": "source_platform",
    "hypervisor": "source_platform",
    "environment": "source_platform",
    # cpu
    "cpu": "cpu_cores",
    "cpus": "cpu_cores",
    "vcpu": "cpu_cores",
    "vcpus": "cpu_cores",
    "num_cpu": "cpu_cores",
    # memory
    "memory": "memory_gb",
    "ram": "memory_gb",
    "ram_gb": "memory_gb",
    "memory_gb_total": "memory_gb",
    # storage
    "storage": "storage_gb",
    "disk": "storage_gb",
    "disk_gb": "storage_gb",
    "hdd_gb": "storage_gb",
    "total_storage_gb": "storage_gb",
    # os
    "os": "os_type",
    "operating_system": "os_type",
    "os_name": "os_type",
    "os_ver": "os_version",
    "os_release": "os_version",
    # criticality
    "priority": "criticality",
    "tier": "criticality",
    "importance": "criticality",
    # migration_strategy
    "strategy": "migration_strategy",
    "migration": "migration_strategy",
    "migration_approach": "migration_strategy",
    # compliance
    "compliance": "compliance_requirements",
    "frameworks": "compliance_requirements",
    # notes
    "description": "notes",
    "comments": "notes",
    "remarks": "notes",
}

# Valid enum values — values not in these sets get mapped to a default
_VALID_TYPES = {"vm", "database", "web-app", "container", "other"}
_VALID_PLATFORMS = {"vmware", "hyperv", "physical", "aws", "gcp", "other"}
_VALID_CRITICALITY = {"mission-critical", "business-critical", "standard", "dev-test"}
_VALID_STRATEGIES = {"rehost", "refactor", "rearchitect", "rebuild", "replace", "unknown"}


def _normalise_column(raw: str) -> str:
    """Convert a raw column header to a canonical field name."""
    cleaned = raw.strip().lower().replace(" ", "_").replace("-", "_")
    return _COLUMN_ALIASES.get(cleaned, cleaned)


def _coerce_int(value: str) -> int | None:
    try:
        return int(float(value.strip()))
    except (ValueError, AttributeError):
        return None


def _coerce_float(value: str) -> float | None:
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None


def _parse_list_field(value: str) -> list[str]:
    """Parse a semi-colon or comma-separated string into a list."""
    if not value or not value.strip():
        return []
    # Try semicolon first, then comma
    sep = ";" if ";" in value else ","
    return [item.strip() for item in value.split(sep) if item.strip()]


def _build_workload(row: dict[str, str], project_id: str) -> WorkloadCreate:
    """Convert a normalised row dict into a WorkloadCreate."""
    name = row.get("name", "").strip()
    if not name:
        raise ValueError("Missing required field: name")

    raw_type = row.get("type", "").strip().lower().replace(" ", "-")
    wl_type = raw_type if raw_type in _VALID_TYPES else "other"

    raw_platform = row.get("source_platform", "").strip().lower().replace(" ", "_")
    platform = raw_platform if raw_platform in _VALID_PLATFORMS else "other"

    raw_criticality = row.get("criticality", "").strip().lower().replace(" ", "-")
    criticality = raw_criticality if raw_criticality in _VALID_CRITICALITY else "standard"

    raw_strategy = row.get("migration_strategy", "").strip().lower()
    strategy = raw_strategy if raw_strategy in _VALID_STRATEGIES else "unknown"

    compliance_raw = row.get("compliance_requirements", "")
    if isinstance(compliance_raw, list):
        compliance = compliance_raw
    else:
        compliance = _parse_list_field(compliance_raw)

    deps_raw = row.get("dependencies", "")
    if isinstance(deps_raw, list):
        deps = deps_raw
    else:
        deps = _parse_list_field(deps_raw)

    return WorkloadCreate(
        project_id=project_id,
        name=name,
        type=wl_type,
        source_platform=platform,
        cpu_cores=_coerce_int(row.get("cpu_cores", "")),
        memory_gb=_coerce_float(row.get("memory_gb", "")),
        storage_gb=_coerce_float(row.get("storage_gb", "")),
        os_type=row.get("os_type") or None,
        os_version=row.get("os_version") or None,
        criticality=criticality,
        compliance_requirements=compliance,
        dependencies=deps,
        migration_strategy=strategy,
        notes=row.get("notes") or None,
    )


def detect_format(filename: str, content: bytes) -> str:
    """Detect whether content is CSV or JSON based on filename and sniffing."""
    lower = filename.lower()
    if lower.endswith(".json"):
        return "json"
    if lower.endswith(".csv") or lower.endswith(".tsv"):
        return "csv"
    # Sniff content
    snippet = content[:512].lstrip()
    if snippet.startswith(b"[") or snippet.startswith(b"{"):
        return "json"
    return "csv"


def parse_file(
    content: bytes, filename: str, project_id: str
) -> tuple[list[WorkloadCreate], list[str]]:
    """Parse CSV or JSON bytes, collecting per-row errors without aborting.

    Returns ``(parsed_workloads, errors)``.  Raises ``ValueError`` for fatal
    format errors (invalid JSON syntax, CSV with no header row).
    """
    fmt = detect_format(filename, content)
    parsed: list[WorkloadCreate] = []
    errors: list[str] = []

    if fmt == "json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc

        if isinstance(data, dict):
            data = data.get("workloads", [data])
        if not isinstance(data, list):
            raise ValueError("JSON must be an array of workload objects")

        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f"Item {idx}: expected object, got {type(item).__name__}")
                continue
            normalised: dict = {}
            for key, value in item.items():
                canonical = _normalise_column(str(key))
                if isinstance(value, list):
                    normalised[canonical] = value  # type: ignore[assignment]
                else:
                    normalised[canonical] = str(value) if value is not None else ""
            try:
                parsed.append(_build_workload(normalised, project_id))
            except ValueError as exc:
                errors.append(f"Item {idx}: {exc}")
    else:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            raise ValueError("CSV file has no headers")

        for row_num, raw_row in enumerate(reader, start=2):
            normalised = {}
            for col, value in raw_row.items():
                if col is None:
                    continue
                canonical = _normalise_column(col)
                normalised[canonical] = value or ""
            try:
                parsed.append(_build_workload(normalised, project_id))
            except ValueError as exc:
                errors.append(f"Row {row_num}: {exc}")

    return parsed, errors


def parse_csv(content: bytes, project_id: str) -> list[WorkloadCreate]:
    """Parse CSV bytes into a list of WorkloadCreate objects.

    Handles BOM-prefixed files and maps common column name variants.
    Raises ValueError on completely unparseable content.
    """
    try:
        text = content.decode("utf-8-sig")  # strips BOM if present
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV file has no headers")

    # Build normalised column map: canonical_name -> original_header
    col_map = {_normalise_column(col): col for col in reader.fieldnames}
    logger.debug("CSV column map: %s", col_map)

    results: list[WorkloadCreate] = []
    for row_num, raw_row in enumerate(reader, start=2):  # start=2 (row 1 is header)
        # Remap columns to canonical names
        normalised: dict[str, str] = {}
        for original_col, value in raw_row.items():
            if original_col is None:
                continue
            canonical = _normalise_column(original_col)
            normalised[canonical] = value or ""

        try:
            workload = _build_workload(normalised, project_id)
            results.append(workload)
        except ValueError as exc:
            logger.warning("Invalid CSV row %d: %s", row_num, exc)
            raise ValueError(f"Row {row_num}: {exc}") from exc

    return results


def parse_json(content: bytes, project_id: str) -> list[WorkloadCreate]:
    """Parse JSON bytes into a list of WorkloadCreate objects.

    Accepts either a JSON array of objects, or a single object, or a dict
    with a 'workloads' key containing an array.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if isinstance(data, dict):
        # Accept {workloads: [...]} wrapper
        data = data.get("workloads", [data])

    if not isinstance(data, list):
        raise ValueError("JSON must be an array of workload objects")

    results: list[WorkloadCreate] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {idx}: expected object, got {type(item).__name__}")

        # Normalise keys
        normalised: dict[str, str] = {}
        for key, value in item.items():
            canonical = _normalise_column(str(key))
            if isinstance(value, list):
                normalised[canonical] = value  # type: ignore[assignment]
            else:
                normalised[canonical] = str(value) if value is not None else ""

        try:
            workload = _build_workload(normalised, project_id)
            results.append(workload)
        except ValueError as exc:
            logger.warning("Skipping JSON item %d: %s", idx, exc)
            raise ValueError(f"Item {idx}: {exc}") from exc

    return results
