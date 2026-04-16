"""Prompt registry — versioned prompt management for AI features.

Provides a singleton registry that stores, retrieves, and versions prompt
templates.  On first access it loads the existing hard-coded prompts from
``app.services.prompts`` as version 1.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class PromptEntry:
    """In-memory representation of a single prompt version."""

    name: str
    version: int
    template: str
    metadata: dict | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PromptRegistry:
    """Singleton registry for versioned AI prompts.

    In dev mode (no database) everything lives in memory.  When a DB is
    available the registry can be backed by the ``prompt_versions`` table.
    """

    _instance: PromptRegistry | None = None
    _lock = threading.Lock()

    def __new__(cls) -> PromptRegistry:  # noqa: D102
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._prompts: dict[str, dict[int, PromptEntry]] = {}
                inst._initialized = False
                cls._instance = inst
            return cls._instance

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def _ensure_initialized(self) -> None:
        """Lazy-load built-in prompts from *prompts.py* as v1."""
        if self._initialized:
            return
        self._initialized = True
        try:
            from app.services.prompts import (
                ARCHITECTURE_REFINEMENT_PROMPT,
                ARCHITECTURE_SYSTEM_PROMPT,
                BICEP_GENERATION_PROMPT,
                COMPLIANCE_EVALUATION_PROMPT,
                COST_ESTIMATION_PROMPT,
            )

            _builtin = {
                "architecture_system": ARCHITECTURE_SYSTEM_PROMPT,
                "compliance_evaluation": COMPLIANCE_EVALUATION_PROMPT,
                "bicep_generation": BICEP_GENERATION_PROMPT,
                "cost_estimation": COST_ESTIMATION_PROMPT,
                "architecture_refinement": ARCHITECTURE_REFINEMENT_PROMPT,
            }
            for name, template in _builtin.items():
                self.register_prompt(
                    name,
                    version=1,
                    template=template,
                    metadata={"source": "builtin"},
                )
            logger.info("Loaded %d built-in prompts as v1", len(_builtin))
        except Exception:
            logger.warning("Could not load built-in prompts", exc_info=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_prompt(
        self,
        name: str,
        version: int,
        template: str,
        metadata: dict | None = None,
    ) -> PromptEntry:
        """Register a prompt template under *name* at *version*."""
        self._ensure_initialized() if name not in self._prompts else None
        entry = PromptEntry(
            name=name,
            version=version,
            template=template,
            metadata=metadata,
        )
        self._prompts.setdefault(name, {})[version] = entry

        # Deactivate older versions, activate this one
        for v, e in self._prompts[name].items():
            e.is_active = v == version

        logger.debug("Registered prompt %s v%d", name, version)
        return entry

    def get_prompt(
        self, name: str, version: int | None = None
    ) -> PromptEntry | None:
        """Return a specific version, or the latest if *version* is ``None``."""
        self._ensure_initialized()
        versions = self._prompts.get(name)
        if not versions:
            return None
        if version is not None:
            return versions.get(version)
        return versions[max(versions)]

    def get_latest_version(self, name: str) -> int | None:
        """Return the highest version number for *name*, or ``None``."""
        self._ensure_initialized()
        versions = self._prompts.get(name)
        if not versions:
            return None
        return max(versions)

    def list_prompts(self) -> list[PromptEntry]:
        """Return every registered prompt version (all names, all versions)."""
        self._ensure_initialized()
        return [
            entry
            for versions in self._prompts.values()
            for entry in versions.values()
        ]

    # ------------------------------------------------------------------
    # Testing helpers
    # ------------------------------------------------------------------

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — **tests only**."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._prompts.clear()
                cls._instance._initialized = False
            cls._instance = None


# Module-level convenience accessor
prompt_registry = PromptRegistry()
