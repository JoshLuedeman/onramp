"""Service layer for architecture version operations."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.architecture_version import ArchitectureVersion
from app.schemas.version import ComponentChange, VersionDiffResponse


async def create_version(
    db: AsyncSession,
    architecture_id: str,
    architecture_json: str,
    created_by: str | None = None,
    change_summary: str | None = None,
) -> ArchitectureVersion:
    """Create a new version for an architecture.

    The ``version_number`` is auto-incremented based on the current maximum
    version for the given architecture.

    Args:
        db: Async database session.
        architecture_id: FK to ``architectures.id``.
        architecture_json: Serialised JSON string of the full architecture.
        created_by: Optional user id who triggered the version.
        change_summary: Human-readable description of what changed.

    Returns:
        The newly created ``ArchitectureVersion`` instance.
    """
    # Determine next version number
    result = await db.execute(
        select(func.coalesce(func.max(ArchitectureVersion.version_number), 0)).where(
            ArchitectureVersion.architecture_id == architecture_id
        )
    )
    max_version: int = result.scalar_one()

    version = ArchitectureVersion(
        architecture_id=architecture_id,
        version_number=max_version + 1,
        architecture_json=architecture_json,
        change_summary=change_summary,
        created_by=created_by,
    )
    db.add(version)
    await db.flush()
    return version


async def list_versions(
    db: AsyncSession,
    architecture_id: str,
) -> list[ArchitectureVersion]:
    """Return all versions for an architecture, newest first.

    Args:
        db: Async database session.
        architecture_id: FK to ``architectures.id``.

    Returns:
        List of ``ArchitectureVersion`` rows ordered by ``version_number`` descending.
    """
    result = await db.execute(
        select(ArchitectureVersion)
        .where(ArchitectureVersion.architecture_id == architecture_id)
        .order_by(ArchitectureVersion.version_number.desc())
    )
    return list(result.scalars().all())


async def get_version(
    db: AsyncSession,
    architecture_id: str,
    version_number: int,
) -> ArchitectureVersion | None:
    """Retrieve a specific version by architecture id and version number.

    Args:
        db: Async database session.
        architecture_id: FK to ``architectures.id``.
        version_number: The version to fetch.

    Returns:
        The matching ``ArchitectureVersion`` or ``None``.
    """
    result = await db.execute(
        select(ArchitectureVersion).where(
            ArchitectureVersion.architecture_id == architecture_id,
            ArchitectureVersion.version_number == version_number,
        )
    )
    return result.scalars().first()


def _extract_components(data: dict[str, Any]) -> dict[str, Any]:
    """Flatten an architecture dict into a name→value mapping of components.

    Handles the top-level keys that represent components in the architecture
    JSON: management_groups, subscriptions, network_topology, policies, and
    compliance_frameworks.
    """
    components: dict[str, Any] = {}
    for key in (
        "management_groups",
        "subscriptions",
        "network_topology",
        "policies",
        "compliance_frameworks",
    ):
        if key in data:
            components[key] = data[key]
    # Also capture any additional top-level keys that aren't metadata
    metadata_keys = {"version", "status", "ai_reasoning", "id", "project_id"}
    for key, value in data.items():
        if key not in components and key not in metadata_keys:
            components[key] = value
    return components


def diff_versions(
    architecture_json_a: str,
    architecture_json_b: str,
) -> VersionDiffResponse:
    """Compare two architecture JSON strings and produce a diff.

    Args:
        architecture_json_a: JSON string of the *from* version.
        architecture_json_b: JSON string of the *to* version.

    Returns:
        ``VersionDiffResponse`` with added, removed, and modified components
        plus a human-readable summary.
    """
    data_a: dict[str, Any] = json.loads(architecture_json_a) if architecture_json_a else {}
    data_b: dict[str, Any] = json.loads(architecture_json_b) if architecture_json_b else {}

    comps_a = _extract_components(data_a)
    comps_b = _extract_components(data_b)

    keys_a = set(comps_a.keys())
    keys_b = set(comps_b.keys())

    added: list[ComponentChange] = []
    removed: list[ComponentChange] = []
    modified: list[ComponentChange] = []

    for key in sorted(keys_b - keys_a):
        added.append(ComponentChange(name=key, detail=f"Added {key}"))

    for key in sorted(keys_a - keys_b):
        removed.append(ComponentChange(name=key, detail=f"Removed {key}"))

    for key in sorted(keys_a & keys_b):
        if comps_a[key] != comps_b[key]:
            detail = _describe_modification(key, comps_a[key], comps_b[key])
            modified.append(ComponentChange(name=key, detail=detail))

    # Build human-readable summary
    parts: list[str] = []
    if added:
        parts.append(f"{len(added)} component(s) added")
    if removed:
        parts.append(f"{len(removed)} component(s) removed")
    if modified:
        parts.append(f"{len(modified)} component(s) modified")
    summary = "; ".join(parts) if parts else "No changes detected"

    return VersionDiffResponse(
        from_version=0,  # Caller sets actual version numbers
        to_version=0,
        added_components=added,
        removed_components=removed,
        modified_components=modified,
        summary=summary,
    )


def _describe_modification(key: str, old: Any, new: Any) -> str:
    """Generate a concise description of how a component changed."""
    if isinstance(old, list) and isinstance(new, list):
        diff = len(new) - len(old)
        if diff > 0:
            return f"{key}: {diff} item(s) added (total {len(new)})"
        if diff < 0:
            return f"{key}: {abs(diff)} item(s) removed (total {len(new)})"
        return f"{key}: items modified (count unchanged at {len(new)})"
    if isinstance(old, dict) and isinstance(new, dict):
        added_keys = set(new.keys()) - set(old.keys())
        removed_keys = set(old.keys()) - set(new.keys())
        parts: list[str] = []
        if added_keys:
            parts.append(f"{len(added_keys)} key(s) added")
        if removed_keys:
            parts.append(f"{len(removed_keys)} key(s) removed")
        changed = sum(1 for k in old.keys() & new.keys() if old[k] != new[k])
        if changed:
            parts.append(f"{changed} key(s) changed")
        return f"{key}: {'; '.join(parts)}" if parts else f"{key}: content changed"
    return f"{key}: value changed"


async def restore_version(
    db: AsyncSession,
    architecture_id: str,
    version_number: int,
    created_by: str | None = None,
    change_summary: str | None = None,
) -> ArchitectureVersion | None:
    """Restore a historical version by creating a new version with its data.

    Args:
        db: Async database session.
        architecture_id: FK to ``architectures.id``.
        version_number: The historical version to restore.
        created_by: Optional user id performing the restore.
        change_summary: Optional note; defaults to a generated message.

    Returns:
        The newly created ``ArchitectureVersion`` or ``None`` if the source
        version was not found.
    """
    source = await get_version(db, architecture_id, version_number)
    if source is None:
        return None

    summary = change_summary or f"Restored from version {version_number}"

    return await create_version(
        db=db,
        architecture_id=architecture_id,
        architecture_json=source.architecture_json,
        created_by=created_by,
        change_summary=summary,
    )
