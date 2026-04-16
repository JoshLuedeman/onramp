"""Comprehensive tests for the template marketplace feature."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.db.seed_templates import CURATED_TEMPLATES, seed_curated_templates
from app.models.template import Template
from app.schemas.template import (
    TemplateCreate,
    TemplateListResponse,
    TemplateRatingRequest,
    TemplateRatingValue,
    TemplateResponse,
    TemplateUseRequest,
    TemplateVisibility,
)
from app.services.template_service import TemplateService, template_service


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _make_template_row(**overrides):
    """Create a mock Template row with sensible defaults."""
    now = datetime.now(timezone.utc)
    defaults = {
        "id": str(uuid.uuid4()),
        "name": "Test Template",
        "description": "A test template",
        "industry": "Healthcare",
        "tags": ["test", "hipaa"],
        "architecture_json": json.dumps({"archetype": "test"}),
        "author_tenant_id": "dev-tenant",
        "visibility": "public",
        "download_count": 0,
        "rating_up": 0,
        "rating_down": 0,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    row = MagicMock(spec=Template)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


SAMPLE_ARCH_JSON = json.dumps({
    "archetype": "sample",
    "network": {"topology": "hub-spoke"},
})


# ══════════════════════════════════════════════════════════════
# 1. Schema Validation Tests
# ══════════════════════════════════════════════════════════════

class TestTemplateSchemas:
    """Pydantic schema validation tests."""

    def test_template_create_valid(self):
        t = TemplateCreate(
            name="My Template",
            industry="Healthcare",
            architecture_json=SAMPLE_ARCH_JSON,
        )
        assert t.name == "My Template"
        assert t.visibility == TemplateVisibility.PRIVATE

    def test_template_create_all_fields(self):
        t = TemplateCreate(
            name="Full Template",
            description="With all fields",
            industry="Retail",
            tags=["retail", "pci"],
            architecture_json=SAMPLE_ARCH_JSON,
            visibility=TemplateVisibility.PUBLIC,
        )
        assert t.tags == ["retail", "pci"]
        assert t.visibility == TemplateVisibility.PUBLIC

    def test_template_create_missing_name(self):
        with pytest.raises(ValidationError):
            TemplateCreate(
                industry="Healthcare",
                architecture_json=SAMPLE_ARCH_JSON,
            )

    def test_template_create_missing_industry(self):
        with pytest.raises(ValidationError):
            TemplateCreate(
                name="No Industry",
                architecture_json=SAMPLE_ARCH_JSON,
            )

    def test_template_create_missing_arch_json(self):
        with pytest.raises(ValidationError):
            TemplateCreate(
                name="No Arch",
                industry="Healthcare",
            )

    def test_template_create_default_tags(self):
        t = TemplateCreate(
            name="Test",
            industry="Startup",
            architecture_json="{}",
        )
        assert t.tags == []

    def test_template_create_default_visibility(self):
        t = TemplateCreate(
            name="Test",
            industry="Startup",
            architecture_json="{}",
        )
        assert t.visibility == TemplateVisibility.PRIVATE

    def test_template_response_from_attributes(self):
        row = _make_template_row()
        resp = TemplateResponse.model_validate(row)
        assert resp.id == row.id
        assert resp.name == row.name

    def test_template_response_defaults(self):
        resp = TemplateResponse(
            id="x", name="N", industry="I",
            visibility="public",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert resp.download_count == 0
        assert resp.rating_up == 0
        assert resp.tags == []

    def test_template_list_response(self):
        resp = TemplateListResponse(
            templates=[], total=0, page=1, page_size=20
        )
        assert resp.total == 0
        assert resp.page == 1

    def test_template_use_request(self):
        req = TemplateUseRequest(project_id="proj-1")
        assert req.project_id == "proj-1"

    def test_template_use_request_missing_project(self):
        with pytest.raises(ValidationError):
            TemplateUseRequest()

    def test_template_rating_up(self):
        req = TemplateRatingRequest(rating=TemplateRatingValue.UP)
        assert req.rating == TemplateRatingValue.UP

    def test_template_rating_down(self):
        req = TemplateRatingRequest(rating=TemplateRatingValue.DOWN)
        assert req.rating == TemplateRatingValue.DOWN

    def test_template_rating_invalid(self):
        with pytest.raises(ValidationError):
            TemplateRatingRequest(rating="sideways")

    def test_visibility_enum_values(self):
        assert TemplateVisibility.PRIVATE == "private"
        assert TemplateVisibility.PUBLIC == "public"
        assert TemplateVisibility.CURATED == "curated"

    def test_rating_enum_values(self):
        assert TemplateRatingValue.UP == "up"
        assert TemplateRatingValue.DOWN == "down"


# ══════════════════════════════════════════════════════════════
# 2. Template Service Tests
# ══════════════════════════════════════════════════════════════

class TestTemplateServiceCreate:
    """Service create_template tests."""

    @pytest.mark.asyncio
    async def test_create_template(self):
        row = _make_template_row(name="Created")
        db = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()

        with patch(
            "app.models.template.Template",
            return_value=row,
        ):
            result = await template_service.create_template(
                db=db,
                data={
                    "name": "Created",
                    "industry": "Healthcare",
                    "architecture_json": SAMPLE_ARCH_JSON,
                },
            )

        assert result["name"] == "Created"
        db.add.assert_called_once()
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_template_with_tenant(self):
        row = _make_template_row(
            author_tenant_id="t-123"
        )
        db = AsyncMock()
        db.add = MagicMock()

        with patch(
            "app.models.template.Template",
            return_value=row,
        ):
            result = await template_service.create_template(
                db=db,
                data={
                    "name": "Tenant Tpl",
                    "industry": "Retail",
                    "architecture_json": "{}",
                },
                author_tenant_id="t-123",
            )

        assert result["author_tenant_id"] == "t-123"

    @pytest.mark.asyncio
    async def test_create_template_defaults(self):
        row = _make_template_row(
            tags=[], visibility="private"
        )
        db = AsyncMock()
        db.add = MagicMock()

        with patch(
            "app.models.template.Template",
            return_value=row,
        ):
            result = await template_service.create_template(
                db=db,
                data={
                    "name": "Defaults",
                    "industry": "Startup",
                    "architecture_json": "{}",
                },
            )

        assert result["visibility"] == "private"
        assert result["tags"] == []


class TestTemplateServiceList:
    """Service list_templates tests."""

    @pytest.mark.asyncio
    async def test_list_no_filters(self):
        rows = [
            _make_template_row(name="T1"),
            _make_template_row(name="T2"),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows

        db = AsyncMock()
        db.scalar = AsyncMock(return_value=2)
        db.execute = AsyncMock(return_value=mock_result)

        result = await template_service.list_templates(db=db)

        assert result["total"] == 2
        assert len(result["templates"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 20

    @pytest.mark.asyncio
    async def test_list_with_industry_filter(self):
        rows = [_make_template_row(industry="Healthcare")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows

        db = AsyncMock()
        db.scalar = AsyncMock(return_value=1)
        db.execute = AsyncMock(return_value=mock_result)

        result = await template_service.list_templates(
            db=db, industry="Healthcare"
        )

        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_with_visibility_filter(self):
        rows = [_make_template_row(visibility="curated")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows

        db = AsyncMock()
        db.scalar = AsyncMock(return_value=1)
        db.execute = AsyncMock(return_value=mock_result)

        result = await template_service.list_templates(
            db=db, visibility="curated"
        )

        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_with_tags_filter(self):
        rows = [
            _make_template_row(
                id="t1", tags=["hipaa", "healthcare"]
            ),
            _make_template_row(
                id="t2", tags=["pci", "financial"]
            ),
        ]
        # First execute returns all rows for tag filtering
        mock_all = MagicMock()
        mock_all.scalars.return_value.all.return_value = rows

        # Second execute returns filtered rows
        filtered = MagicMock()
        filtered.scalars.return_value.all.return_value = [rows[0]]

        db = AsyncMock()
        db.scalar = AsyncMock(return_value=2)
        db.execute = AsyncMock(
            side_effect=[mock_all, filtered]
        )

        result = await template_service.list_templates(
            db=db, tags=["hipaa"]
        )

        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_pagination_page2(self):
        rows = [_make_template_row(name="Page2Item")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows

        db = AsyncMock()
        db.scalar = AsyncMock(return_value=25)
        db.execute = AsyncMock(return_value=mock_result)

        result = await template_service.list_templates(
            db=db, page=2, page_size=10
        )

        assert result["page"] == 2
        assert result["page_size"] == 10

    @pytest.mark.asyncio
    async def test_list_empty(self):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        db = AsyncMock()
        db.scalar = AsyncMock(return_value=0)
        db.execute = AsyncMock(return_value=mock_result)

        result = await template_service.list_templates(db=db)

        assert result["total"] == 0
        assert result["templates"] == []


class TestTemplateServiceGet:
    """Service get_template tests."""

    @pytest.mark.asyncio
    async def test_get_existing(self):
        row = _make_template_row(name="Found")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = row

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        result = await template_service.get_template(
            db=db, template_id=row.id
        )

        assert result is not None
        assert result["name"] == "Found"

    @pytest.mark.asyncio
    async def test_get_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        result = await template_service.get_template(
            db=db, template_id="nonexistent"
        )

        assert result is None


class TestTemplateServiceUse:
    """Service use_template tests."""

    @pytest.mark.asyncio
    async def test_use_increments_download(self):
        row = _make_template_row(download_count=5)
        mock_tpl = MagicMock()
        mock_tpl.scalar_one_or_none.return_value = row

        mock_arch = MagicMock()
        mock_arch.scalar_one_or_none.return_value = None

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[mock_tpl, mock_arch]
        )
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        result = await template_service.use_template(
            db=db, template_id=row.id, project_id="proj-1"
        )

        assert result is not None
        assert row.download_count == 6

    @pytest.mark.asyncio
    async def test_use_template_not_found(self):
        mock_tpl = MagicMock()
        mock_tpl.scalar_one_or_none.return_value = None

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_tpl)

        result = await template_service.use_template(
            db=db, template_id="missing", project_id="p1"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_use_updates_existing_architecture(self):
        row = _make_template_row(download_count=0)
        mock_tpl = MagicMock()
        mock_tpl.scalar_one_or_none.return_value = row

        existing_arch = MagicMock()
        existing_arch.architecture_data = {}
        mock_arch = MagicMock()
        mock_arch.scalar_one_or_none.return_value = existing_arch

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[mock_tpl, mock_arch]
        )
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        await template_service.use_template(
            db=db, template_id=row.id, project_id="p1"
        )

        assert row.download_count == 1

    @pytest.mark.asyncio
    async def test_use_handles_invalid_json(self):
        row = _make_template_row(
            architecture_json="not valid json"
        )
        mock_tpl = MagicMock()
        mock_tpl.scalar_one_or_none.return_value = row

        mock_arch = MagicMock()
        mock_arch.scalar_one_or_none.return_value = None

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[mock_tpl, mock_arch]
        )
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        result = await template_service.use_template(
            db=db, template_id=row.id, project_id="p1"
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_use_handles_none_arch_json(self):
        row = _make_template_row(architecture_json=None)
        mock_tpl = MagicMock()
        mock_tpl.scalar_one_or_none.return_value = row

        mock_arch = MagicMock()
        mock_arch.scalar_one_or_none.return_value = None

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[mock_tpl, mock_arch]
        )
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        result = await template_service.use_template(
            db=db, template_id=row.id, project_id="p1"
        )

        assert result is not None


class TestTemplateServiceRate:
    """Service rate_template tests."""

    @pytest.mark.asyncio
    async def test_rate_up(self):
        row = _make_template_row(rating_up=3, rating_down=1)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = row

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        result = await template_service.rate_template(
            db=db, template_id=row.id, rating="up"
        )

        assert result is not None
        assert row.rating_up == 4

    @pytest.mark.asyncio
    async def test_rate_down(self):
        row = _make_template_row(rating_up=3, rating_down=1)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = row

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        result = await template_service.rate_template(
            db=db, template_id=row.id, rating="down"
        )

        assert result is not None
        assert row.rating_down == 2

    @pytest.mark.asyncio
    async def test_rate_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        result = await template_service.rate_template(
            db=db, template_id="missing", rating="up"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_rate_invalid_value(self):
        row = _make_template_row(rating_up=0, rating_down=0)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = row

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        result = await template_service.rate_template(
            db=db, template_id=row.id, rating="invalid"
        )

        assert result is not None
        assert row.rating_up == 0
        assert row.rating_down == 0

    @pytest.mark.asyncio
    async def test_rate_up_from_zero(self):
        row = _make_template_row(rating_up=0, rating_down=0)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = row

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        result = await template_service.rate_template(
            db=db, template_id=row.id, rating="up"
        )

        assert row.rating_up == 1


class TestTemplateServiceCurated:
    """Service get_curated_templates tests."""

    def test_get_curated_returns_list(self):
        result = template_service.get_curated_templates()
        assert isinstance(result, list)
        assert len(result) == 5

    def test_curated_has_healthcare(self):
        result = template_service.get_curated_templates()
        names = [t["name"] for t in result]
        assert any("Healthcare" in n for n in names)

    def test_curated_has_financial(self):
        result = template_service.get_curated_templates()
        names = [t["name"] for t in result]
        assert any("Financial" in n for n in names)

    def test_curated_has_government(self):
        result = template_service.get_curated_templates()
        names = [t["name"] for t in result]
        assert any("Government" in n for n in names)

    def test_curated_has_retail(self):
        result = template_service.get_curated_templates()
        names = [t["name"] for t in result]
        assert any("Retail" in n for n in names)

    def test_curated_has_startup(self):
        result = template_service.get_curated_templates()
        names = [t["name"] for t in result]
        assert any("Startup" in n for n in names)

    def test_curated_all_have_required_fields(self):
        result = template_service.get_curated_templates()
        for t in result:
            assert "id" in t
            assert "name" in t
            assert "industry" in t
            assert "architecture_json" in t
            assert "visibility" in t
            assert t["visibility"] == "curated"

    def test_curated_arch_json_is_valid(self):
        result = template_service.get_curated_templates()
        for t in result:
            data = json.loads(t["architecture_json"])
            assert isinstance(data, dict)
            assert "archetype" in data

    def test_curated_templates_are_independent_copies(self):
        r1 = template_service.get_curated_templates()
        r2 = template_service.get_curated_templates()
        assert r1 is not r2


class TestTemplateServiceRowToDict:
    """Test the _row_to_dict helper."""

    def test_row_to_dict_all_fields(self):
        row = _make_template_row()
        d = TemplateService._row_to_dict(row)
        assert d["id"] == row.id
        assert d["name"] == row.name
        assert d["description"] == row.description
        assert d["industry"] == row.industry
        assert d["tags"] == row.tags
        assert d["download_count"] == 0
        assert d["rating_up"] == 0
        assert d["rating_down"] == 0

    def test_row_to_dict_none_tags(self):
        row = _make_template_row(tags=None)
        d = TemplateService._row_to_dict(row)
        assert d["tags"] == []

    def test_row_to_dict_none_counts(self):
        row = _make_template_row(
            download_count=None, rating_up=None, rating_down=None
        )
        d = TemplateService._row_to_dict(row)
        assert d["download_count"] == 0
        assert d["rating_up"] == 0
        assert d["rating_down"] == 0

    def test_row_to_dict_none_timestamps(self):
        row = _make_template_row(
            created_at=None, updated_at=None
        )
        d = TemplateService._row_to_dict(row)
        assert d["created_at"] is None
        assert d["updated_at"] is None


# ══════════════════════════════════════════════════════════════
# 3. Seed Tests
# ══════════════════════════════════════════════════════════════

class TestSeedCuratedTemplates:
    """Tests for the curated template seeding."""

    def test_curated_data_count(self):
        assert len(CURATED_TEMPLATES) == 5

    def test_curated_ids_unique(self):
        ids = [t["id"] for t in CURATED_TEMPLATES]
        assert len(ids) == len(set(ids))

    def test_curated_industries_diverse(self):
        industries = {t["industry"] for t in CURATED_TEMPLATES}
        assert len(industries) == 5

    def test_curated_all_have_tags(self):
        for t in CURATED_TEMPLATES:
            assert len(t["tags"]) > 0

    def test_curated_all_have_description(self):
        for t in CURATED_TEMPLATES:
            assert t["description"]
            assert len(t["description"]) > 20

    @pytest.mark.asyncio
    async def test_seed_skips_when_populated(self):
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=5)

        await seed_curated_templates(session)

        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_inserts_when_empty(self):
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=0)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await seed_curated_templates(session)

        assert session.add.call_count == 5
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_seed_idempotent_none_count(self):
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await seed_curated_templates(session)

        assert session.add.call_count == 5


# ══════════════════════════════════════════════════════════════
# 4. Model Tests
# ══════════════════════════════════════════════════════════════

class TestTemplateModel:
    """Template SQLAlchemy model tests."""

    def test_tablename(self):
        assert Template.__tablename__ == "templates"

    def test_model_columns(self):
        cols = {c.name for c in Template.__table__.columns}
        expected = {
            "id", "name", "description", "industry", "tags",
            "architecture_json", "author_tenant_id", "visibility",
            "download_count", "rating_up", "rating_down",
            "created_at", "updated_at",
        }
        assert expected.issubset(cols)

    def test_id_is_primary_key(self):
        pk_cols = [
            c.name for c in Template.__table__.primary_key.columns
        ]
        assert "id" in pk_cols

    def test_author_tenant_id_fk(self):
        col = Template.__table__.c.author_tenant_id
        fk_targets = [
            fk.target_fullname for fk in col.foreign_keys
        ]
        assert "tenants.id" in fk_targets

    def test_visibility_default(self):
        col = Template.__table__.c.visibility
        assert col.default is not None
        assert col.default.arg == "private"

    def test_download_count_default(self):
        col = Template.__table__.c.download_count
        assert col.default is not None
        assert col.default.arg == 0

    def test_rating_up_default(self):
        col = Template.__table__.c.rating_up
        assert col.default is not None
        assert col.default.arg == 0

    def test_rating_down_default(self):
        col = Template.__table__.c.rating_down
        assert col.default is not None
        assert col.default.arg == 0


# ══════════════════════════════════════════════════════════════
# 5. Route-level Tests (via FastAPI TestClient)
# ══════════════════════════════════════════════════════════════

class TestTemplateRoutes:
    """Test route handler logic via mocked service."""

    @pytest.mark.asyncio
    async def test_create_route_calls_service(self):
        from app.api.routes.templates import create_template

        payload = TemplateCreate(
            name="Route Test",
            industry="Healthcare",
            architecture_json=SAMPLE_ARCH_JSON,
        )
        user = {"tenant_id": "dev-tenant"}
        db = AsyncMock()

        now = datetime.now(timezone.utc)
        with patch.object(
            template_service,
            "create_template",
            new_callable=AsyncMock,
            return_value={
                "id": "new-id",
                "name": "Route Test",
                "description": None,
                "industry": "Healthcare",
                "tags": [],
                "architecture_json": SAMPLE_ARCH_JSON,
                "author_tenant_id": "dev-tenant",
                "visibility": "private",
                "download_count": 0,
                "rating_up": 0,
                "rating_down": 0,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            },
        ) as mock_create:
            result = await create_template(payload, user, db)
            mock_create.assert_awaited_once()
            assert result.name == "Route Test"

    @pytest.mark.asyncio
    async def test_create_route_no_db(self):
        from fastapi import HTTPException

        from app.api.routes.templates import create_template

        payload = TemplateCreate(
            name="No DB",
            industry="Healthcare",
            architecture_json="{}",
        )
        with pytest.raises(HTTPException) as exc_info:
            await create_template(payload, {}, None)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_get_route_not_found(self):
        from fastapi import HTTPException

        from app.api.routes.templates import get_template

        db = AsyncMock()
        with patch.object(
            template_service,
            "get_template",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_template("missing-id", {}, db)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_route_no_db(self):
        from fastapi import HTTPException

        from app.api.routes.templates import get_template

        with pytest.raises(HTTPException) as exc_info:
            await get_template("x", {}, None)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_use_route_not_found(self):
        from fastapi import HTTPException

        from app.api.routes.templates import use_template

        payload = TemplateUseRequest(project_id="p1")
        db = AsyncMock()
        with patch.object(
            template_service,
            "use_template",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await use_template("missing", payload, {}, db)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_use_route_no_db(self):
        from fastapi import HTTPException

        from app.api.routes.templates import use_template

        payload = TemplateUseRequest(project_id="p1")
        with pytest.raises(HTTPException) as exc_info:
            await use_template("x", payload, {}, None)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_rate_route_not_found(self):
        from fastapi import HTTPException

        from app.api.routes.templates import rate_template

        payload = TemplateRatingRequest(
            rating=TemplateRatingValue.UP
        )
        db = AsyncMock()
        with patch.object(
            template_service,
            "rate_template",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await rate_template("missing", payload, {}, db)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_rate_route_no_db(self):
        from fastapi import HTTPException

        from app.api.routes.templates import rate_template

        payload = TemplateRatingRequest(
            rating=TemplateRatingValue.UP
        )
        with pytest.raises(HTTPException) as exc_info:
            await rate_template("x", payload, {}, None)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_list_route_no_db_returns_curated(self):
        from app.api.routes.templates import list_templates

        result = await list_templates(
            industry=None, tags=None, visibility=None,
            page=1, page_size=20, user={}, db=None,
        )
        assert result.total == 5
        assert len(result.templates) == 5

    @pytest.mark.asyncio
    async def test_list_route_with_db(self):
        from app.api.routes.templates import list_templates

        now = datetime.now(timezone.utc)
        with patch.object(
            template_service,
            "list_templates",
            new_callable=AsyncMock,
            return_value={
                "templates": [{
                    "id": "t1",
                    "name": "DB Template",
                    "description": None,
                    "industry": "Retail",
                    "tags": [],
                    "architecture_json": "{}",
                    "author_tenant_id": None,
                    "visibility": "public",
                    "download_count": 0,
                    "rating_up": 0,
                    "rating_down": 0,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }],
                "total": 1,
                "page": 1,
                "page_size": 20,
            },
        ):
            db = AsyncMock()
            result = await list_templates(
                industry=None, tags=None, visibility=None,
                page=1, page_size=20, user={}, db=db,
            )
            assert result.total == 1

    @pytest.mark.asyncio
    async def test_list_route_with_tags_csv(self):
        from app.api.routes.templates import list_templates

        now = datetime.now(timezone.utc)
        with patch.object(
            template_service,
            "list_templates",
            new_callable=AsyncMock,
            return_value={
                "templates": [],
                "total": 0,
                "page": 1,
                "page_size": 20,
            },
        ) as mock_list:
            db = AsyncMock()
            await list_templates(
                industry=None, tags="hipaa,pci",
                visibility=None, page=1, page_size=20,
                user={}, db=db,
            )
            call_kwargs = mock_list.call_args.kwargs
            assert call_kwargs["tags"] == ["hipaa", "pci"]


# ══════════════════════════════════════════════════════════════
# 6. Integration / Singleton Tests
# ══════════════════════════════════════════════════════════════

class TestTemplateServiceSingleton:
    """Verify singleton pattern."""

    def test_singleton_instance(self):
        from app.services.template_service import template_service as ts
        assert ts is template_service

    def test_service_is_template_service_type(self):
        assert isinstance(template_service, TemplateService)
